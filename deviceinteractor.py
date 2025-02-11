from typing import Final, final
from time import sleep
import tomllib
import serial

DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 1         # seconds
DEFAULT_READSIZE = 64       # bytes
DEFAULT_RESPONSE = "OK"
DEFAULT_ENCODING = "utf-8"
BEHAVIORS_FILENAME = "./behaviors.toml"

class DeviceInteractor:
    f"""
    A class to handle communications with a serial device.

    This class is expected to be extended to cover custom interactions.

    Attributes
    ----------
    device : str
        Path to system device to be open by the pySerial library
    baudrate : int (default: {DEFAULT_BAUDRATE})
        Baudrate used by pySerial library
    timeout : int (default: {DEFAULT_TIMEOUT})
        Timeout for receiving data in seconds. If there is not data received after the
        timeout, a loop will immediately listen again on the serial port for new input.
    read_size : int (default: {DEFAULT_READSIZE})
        Bytes that will be read
    df_response : str (default: {DEFAULT_RESPONSE})
        Default df_response to any data received.
    encoding : str (default: {DEFAULT_ENCODING})
        Enconding that should be used for response's.
        If the selected behavior ends in "_hex" this parameter will be ignored and the
        serial port input and the responses written into it will be encoded as plain
        binary strings internally handled by bytes.hex() and bytes.fromhex() methods.

    Methods
    -------
    @final listen():
        Handles the while loop listening for data and sending it to the state_machine().
    state_machine():
        The behavior this class should have given a certain input. For custom behaviors
        you should set <options["Behavior"]> parameter pointing to a valid root table
        entry in {BEHAVIORS_FILENAME} file.

    Exceptions
    ----------
        IOError : when a communication error with the serial device has ocurred.
        KeyError : when a behavior is not found in {BEHAVIORS_FILENAME} file.
    """

    def __init__(self, device: str, options: dict[str, str|int]) -> None:
        self.device: Final[str] = str(device)
        self.baudrate: Final[int] = int(options.get("Baudrate", DEFAULT_BAUDRATE))
        self.timeout: Final[int] = int(options.get("Timeout", DEFAULT_TIMEOUT))
        self.read_size: Final[int] = int(options.get("ReadSize", DEFAULT_READSIZE))
        self.encoding: Final[str] = str(options.get("Encoding", DEFAULT_ENCODING))
        self.df_response: Final[bytes] = str(
            options.get("Response", DEFAULT_RESPONSE)).encode(self.encoding)
        self.behavior_name: Final[str] = str(options.get("Behavior", None))

        self.serial: serial.Serial | None = None
        self.previous_event: list[tuple[str, str]] = list()
        self.binary_streams: Final[bool] = self.behavior_name[-4:] == "_hex"

    @final
    def __del__(self) -> None:
        if self.serial:
            self.serial.close()
            self.serial = None

    @final
    def init_device(self) -> serial.Serial:
        ser = serial.Serial(self.device, self.baudrate, timeout=self.timeout)
        if not ser.is_open:
            raise IOError(f"Serial device {self.device} not found")
        return ser

    @final
    def listen(self) -> None:
        if not self.serial:
            self.serial = self.init_device()

        behavior = self.load_behavior()

        while True:
            try:
                data = ""
                if self.binary_streams:
                    tmp = self.serial.read(self.read_size).hex()
                    data = f"h{tmp}" if tmp else ""
                else:
                    data = self.serial.readline().decode(self.encoding).strip()
                if not data:
                    continue
                delay, response = self.state_machine(data, responses=behavior)
                if delay > 0:
                    sleep(delay)
                _ = self.serial.write(response)
            except serial.SerialException as e:
                raise IOError(f"Connection terminated: {e}")

    @final
    def load_behavior(self) -> dict[str, dict[str, str | int]] | None:
        if not self.behavior_name:
            return None
        try:
            fd = open(BEHAVIORS_FILENAME, "rb")
            behaviors = tomllib.load(fd)
            fd.close()
        except FileNotFoundError:
            raise IOError(f"Behavior toml file ({BEHAVIORS_FILENAME}) not found")

        bh: dict[str, dict[str, str | int]] | None = behaviors.get(self.behavior_name, None)
        if not bh:
            raise KeyError(f"'{self.behavior_name}' behavior not found in {BEHAVIORS_FILENAME}")

        return bh

    def state_machine(self,
            msg_received: str,
            responses: dict[str, dict[str, str | int]] | None = None
            ) -> tuple[int, bytes]:
        delay = 0
        response = b""

        if not responses:
            # Default behavior, return self.df_response and
            # wait <msg_received> seconds in case the message received was an integer
            try:
                response = self.df_response
                tmp = int(msg_received)
                if tmp > 0:
                    delay = tmp
            except ValueError:
                pass
        else:
            data = responses[msg_received]
            delay = int(data.get("delay", 0))
            tmp = str(data.get("message", ""))
            response = bytes.fromhex(tmp[1:]) if tmp else b""
        return (delay, response)
