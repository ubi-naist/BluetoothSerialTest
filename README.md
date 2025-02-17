# Bluetooth Serial Test

Scripts for testing serial communication through Bluetooth Classic's RFCOMM interface.

These scripts were intended to work with Raspberry OS on a Raspberry Pi Zero 2 W, but they should work in other similar Debian Linux environments.

# Requirements

* Bluetooth Classic RFCOMM service or equivalent
* Python 3.11 or code glue to load a similar library to `tomllib`

## Preparation

1. Copy or add `bluetooth.service` modifications into your Bluetooth service file. This will:
  * Change your bluetooth daemon to enable deprecated services.
  * Add Serial Port (SP) service through `sdptool`.

    File: `systemd/system/bluetooth.target.wants/bluetooth.service`

2. Create a new systemd service file to automatically listen through a rfcomm interface.

    File: `systemd/system/rfcomm.service`

3. Recreate this virtual environment.

```bash
$ python3 -m venv $(pwd)          # Create a python virtual environment in the current directory
$ source bin/activate             # Activate the virtual environment
$ pip install -r requirements.txt # Install pip packages
```

## Usage

```bash
$ python3 blueserialtest.py --help
usage: blueserialtest [-r response] [-e encoding] [-b behavior_name] [--dont_show] [-d device] [-br baudrate]

Listens on rfcomm serial device and sends a pre programmed response. Responses can be customized as a predifined behavior on a
behaviors.toml file

options:
  -h, --help            show this help message and exit
  -r, --response RESPONSE
                        Default response for every message received (default: OK)
  -e, --encoding ENCODING
                        Enconding used for plain-text communication/behaviors. (default: utf-8)
  -b, --behavior BEHAVIOR
                        Custom behavior to load. This should be a root table name collection from behaviors.toml. (default: default)
  -ds, --dont-show      Don't echo serial communication on stdout. (default: False)
  -d, --device DEVICE   Serial device to connect to (default: /dev/rfcomm0)
  -br, --baudrate BAUDRATE
                        PySerial's serial device baudrate. (default: 115200)
```

