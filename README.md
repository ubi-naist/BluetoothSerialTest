# Bluetooth Serial Test

Scripts for testing serial communication through Bluetooth Classic's RFCOMM interface.

These scripts were intended to work with Raspberry OS on a Raspberry Pi Zero 2 W, but they should work in other similar Debian Linux environments.

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
python3 blueserialtest.py --help
```

