# pyright: reportUnusedCallResult=false, reportAny=false

import argparse
import subprocess
from deviceinteractor import DeviceInteractor

parser = argparse.ArgumentParser(prog='blueserialtest'
    , usage='%(prog)s [-r]'
    , description='Listens on rfcomm serial device and sends a default response'
    )
parser.add_argument("-r", "--response"
    , help="Default response for every message received"
    , type=str
    , default="OK"
    )
parser.add_argument("-d", "--device"
    , help="Serial device to connect to"
    , type=str
    , default="/dev/rfcomm0"
    )
parser.add_argument("-b", "--behavior"
    , help="Custom behavior to load. This should be a root table name collection from behaviors.toml."
    , type=str
    , default="default"
    )

args = parser.parse_args()
RESPONSE = f"{args.response}\r\n"
DEVICE = args.device
BEHAVIOR = args.behavior

try:
    # Check for running rfcomm
    result = subprocess.check_output(["ps", "-eo", "pid args"]
        , encoding="utf-8"
        )
    rfcommProc = None
    for line in result.split("\n"):
        proc = line.strip().split(" ")
        if proc[1] == "/usr/bin/rfcomm":
            rfcommProc = proc
            break
    if not rfcommProc:
        print("rfcomm is not running")
        raise SystemExit

    # Check for rfcomm running parameters
    if rfcommProc[2] not in ["watch", "listen"]:
        print("It seems rfcomm is not listening for connections: "+" ".join(rfcommProc))
        raise SystemExit

except AttributeError:
    print("Failed to search for rfcomm process")
    raise SystemExit
except IndexError:
    print("Failed to find rfcomm process")
    raise SystemExit

try:
    result = subprocess.check_output(["ls", "-C", DEVICE], encoding="utf-8")
    if result.strip() == DEVICE:
        print(f"External device connected and waiting on {DEVICE}\n")
except subprocess.CalledProcessError:
    print(f"External device is not connected: {DEVICE} not found")
    raise SystemExit

opts = {
    "Baudrate": 115200,
    "Timeout": 1,
    "Response": RESPONSE,
}
if BEHAVIOR != "default":
    opts["Behavior"] = BEHAVIOR

try:
    interactor = DeviceInteractor(DEVICE, options=opts)
    interactor.listen()
except IOError as e:
    print(e)
    raise SystemExit