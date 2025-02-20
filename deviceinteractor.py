from typing import Final, final, cast
from time import sleep, time
import random
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
        Default df_response to any data received when no custom behavior is specified.
    encoding : str (default: {DEFAULT_ENCODING})
        Enconding that should be used for response's.
        If the selected behavior ends in "_hex" this parameter will be ignored and the
        serial port input and the responses written into it will be encoded as plain
        binary strings internally handled by bytes.hex() and bytes.fromhex() methods.
    behavior_name : str (default: "")
        Custom behavior as defined on a {BEHAVIORS_FILENAME} table.
    show : bool (default: True)
        If True, it will echo all Tx and Rx data on stdout.

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
        self.df_response: Final[str] = str(options.get("Response", DEFAULT_RESPONSE))
        self.behavior_name: Final[str] = str(options.get("Behavior", ""))
        self.show: Final[bool] = bool(options.get("Show", True))

        self.serial: serial.Serial | None = None
        self.previous_event: list[str] = list()
        self.binary_streams: Final[bool] = self.behavior_name[-4:] == "_hex"
        self.streaming: bool = False
        self.streaming_period: int = 0 # in milliseconds
        self.streams: list[str] = list()
        self.last_stream_timestamp: int = 0 # unix time with milliseconds

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
        self.last_stream_timestamp = round(time() * 1000)
        next_stream_timestamp = self.last_stream_timestamp + self.streaming_period

        while True:
            try:
                payload = ""
                if self.binary_streams:
                    tmp = self.serial.read(self.read_size).hex()
                    payload = f"h{tmp}" if tmp else ""
                else:
                    payload = self.serial.readline().decode(self.encoding).strip()

                # streaming functionality
                if not payload and self.streaming and round(time() * 1000) > next_stream_timestamp:
                    payload = random.choice(self.streams)
                    self.last_stream_timestamp = round(time() * 1000)
                    next_stream_timestamp = self.last_stream_timestamp + self.streaming_period

                if not payload:
                    continue

                if self.show:
                    print(f"RX: {payload}")
                delay, response = self.state_machine(payload, responses=behavior)

                if not response:
                    continue

                self.previous_event.append(payload)

                if delay > 0:
                    sleep(delay)

                if self.show:
                    print(f"TX: {response}")
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

        bh: dict[str, dict[str, str | int]] | None = behaviors.get(self.behavior_name)
        if not bh:
            raise KeyError(f"'{self.behavior_name}' behavior not found in {BEHAVIORS_FILENAME}")

        return bh

    @final
    def default_behavior(self, payload: str) -> tuple[int, str]:
        # Return self.df_response and wait <payload> seconds in case the message received was an integer
        delay = 0
        response = self.df_response
        try:
            tmp = int(payload)
            if tmp > 0:
                delay = tmp
        except ValueError:
            pass
        return (delay, response)


    def process_output(self, string: str) -> bytes:
        if self.binary_streams:
            return bytes.fromhex(string[1:])
        else:
            return "{0}\r\n".format(string).encode(self.encoding) if string else b''

    def state_machine(self,
            payload: str,
            responses: dict[str, dict[str, str | int]] | None = None
            ) -> tuple[int, bytes]:
        delay = 0
        response = b""
        payload = payload.lower()

        if not responses:
            delay, str_response = self.default_behavior(payload)
            response = self.process_output(str_response)
        else:
            str_response = ""
            data = responses.get(payload)
            if not data:
                # case without a match, return default response "_" case
                data = responses.get("_", {})
            delay = int(data.get("delay", 0))
            tmp = data.get("message")
            if tmp:
                # has a message response
                streamer = data.get("stream")
                if streamer is not None:
                    # stream start/stop response
                    self.streaming_period = abs(int(data.get("period", 0))) * 1000
                    self.streams = cast(list[str], data.get("streams", []))
                    self.streaming = bool(streamer) and bool(self.streaming_period) and bool(self.streams)
                    print(f"Streaming: {self.streaming}, Period: {self.streaming_period}, Streams: {self.streams}")
                # normal response
                str_response = str(tmp)
            else:
                # check if it's a conditional case
                conditional = data.get("if")
                then_case = data.get("then")
                else_case = data.get("else")
                if conditional and then_case and else_case:
                    if len(self.previous_event) > 0 and self.previous_event[-1] == str(conditional):
                        case = then_case
                    else:
                        case = else_case
                    data = responses[str(case)]
                else:
                    # case without a match, return default response "_" case
                    data = responses.get("_", {})
                delay = int(data.get("delay", 0))
                str_response = str(data.get("message", ""))
            response = self.process_output(str_response)

        return (delay, response)
