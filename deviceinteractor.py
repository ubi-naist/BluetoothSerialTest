from typing import Final, final
from time import sleep
import serial

DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 1         # seconds
DEFAULT_RESPONSE = "OK"
DEFAULT_ENCODING = "utf-8"

class DeviceInteractor:
    """
    A class to handle communications with a serial device.

    This class is expected to be extended to cover custom interactions.

    Attributes
    ----------
    device : str
        Path to system device to be open by the pySerial library
    baudrate : int
        Baudrate used by pySerial library
    timeout : int
        Timeout for receiving data in seconds. If there is not data received after the
        timeout, a loop will immediately listen again on the serial port for new input.
    response : str
        Default response to any data received.
    encoding : str
        Enconding that should be used for <response>'s.

    Methods
    -------
    @final listen():
        Handles the while loop listening for data and sending it to the state_machine().
    state_machine():
        The behavior this class should have given a certain input. For custom behaviors
        this method should be overridden.

    Exceptions
    ----------
        IOError : when a communication error with the serial device has ocurred
    """

    def __init__(self, device: str, options: dict[str, str|int]) -> None:
        self.device: Final[str] = str(device)
        self.baudrate: Final[int] = int(options.get("Baudrate", DEFAULT_BAUDRATE))
        self.timeout: Final[int] = int(options.get("Timeout", DEFAULT_TIMEOUT))
        self.encoding: Final[str] = str(options.get("Encoding", DEFAULT_ENCODING))
        self.response: Final[bytes] = str(
            options.get("Response", DEFAULT_RESPONSE)).encode(self.encoding)

        self.serial: serial.Serial | None = None
        self.previous_event: list[tuple[str, str]] = list()

    @final
    def __del__(self) -> None:
        if self.serial:
            self.serial.close()
            self.serial = None

    @final
    def init_device(self) -> serial.Serial:
        ser = serial.Serial(self.device, self.baudrate, timeout=self.timeout)
        if not ser.is_open:
            raise IOError(f"Serial device ${self.device} not found")
        return ser

    @final
    def listen(self) -> None:
        if not self.serial:
            self.serial = self.init_device()

        while True:
            try:
                data = self.serial.readline().decode(self.encoding).strip()
                if not data:
                    continue
                delay, response = self.state_machine(data)
                if delay > 0:
                    sleep(delay)
                _ = self.serial.write(response)
            except serial.SerialException as e:
                raise IOError(f"Connection terminated: ${e}")

    def state_machine(self, msg_received: str) -> tuple[int, bytes]:
        delay = 0
        try:
            tmp = int(msg_received)
            if tmp > 0:
                delay = tmp
        except ValueError:
            pass
        return (delay, self.response)