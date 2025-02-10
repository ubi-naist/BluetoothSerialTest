# basedpyright: reportUnusedCallResult=false, reportAny=false

import argparse
import subprocess
import serial

parser = argparse.ArgumentParser(prog='blueserialtest'
    , usage='%(prog)s [-r]'
    , description='Listens on rfcomm serial device and sends a default response'
    )
parser.add_argument("-r", "--response"
    , help="Default response for every message received"
    , type=str
    , default="OK"
    )

args = parser.parse_args()
RESPONSE = "{}\n".format(args.response).encode("utf-8")

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
    result = subprocess.check_output(["ls", "-C", "/dev/rfcomm0"], encoding="utf-8")
    if result.strip() == "/dev/rfcomm0":
        print("External device connected and waiting on /dev/rfcomm0\n")
except subprocess.CalledProcessError:
    print("External device is not connected: /dev/rfcomm0 not found")
    raise SystemExit

with serial.Serial("/dev/rfcomm0", 115200, timeout=1) as ser:
    print(f"Serial port openned at {ser}")
    while True:
        try:
            data = ser.readline()
            if not data:
                continue
            print(data)
            ser.write(RESPONSE)
        except serial.SerialException as e:
            print(f"Connection terminated: {e}")
            raise SystemExit