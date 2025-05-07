# Kickr-to-Gamepad

This project connects one or more Wahoo KICKR trainers to a virtual Xbox 360 controller (via ViGEmBus) so that trainer speed data maps directly to gamepad axes.  

Two modes are available:
  - **BLE mode** (`ble-vjoy.py`): connects via Bluetooth LE (FTMS).  
  - **TCP mode** (`tcp-vjoy.py`): connects via the built-in TCP/Dircon interface on Wahoo head units.

This README covers the TCP version (`tcp-vjoy.py`).

---

## Prerequisites

- **Windows PC** with Python 3.10 or newer
- **ViGEmBus driver** installed (required by `pyvjoystick`)
  - Download/installer: https://github.com/ViGEm/ViGEmBus/releases
- Network connectivity to your KICKR devices (`169.254.3.1`–`169.254.3.4` by default)

## Setup

1. Clone or download this repository to your Windows machine.
2. Install Python dependencies:
   ```powershell
   cd kickr-to-gamepad
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

## Running TCP Mode

The `tcp-vjoy.py` script will:
  1. Open parallel TCP connections to your KICKR trainers at IPs `169.254.3.1`–`169.254.3.4`
  2. Enable FTMS indoor-bike data notifications over Dircon
  3. Decode the instantaneous speed from each trainer
  4. Map each trainer speed to one axis on a virtual Xbox360 controller:
     - Trainer 1 → Left stick X
     - Trainer 2 → Left stick Y
     - Trainer 3 → Right stick X
     - Trainer 4 → Right stick Y

To run:
```powershell
python scripts/tcp-vjoy.py
```

You should see console logs for each device connection and controller updates.

## Customization

- **IP addresses**: edit the `DEVICE_IPS` list at the top of `scripts/tcp-vjoy.py` if your trainers use different addresses.
- **Axis mapping**: modify the `update_gamepad()` function to change which speed maps to which joystick or trigger.

## BLE Mode (Optional)

If you prefer BLE, see [scripts/ble-vjoy.py](scripts/ble-vjoy.py) and follow its builtin instructions.  Make sure your PC has a compatible BLE adapter.

---

Happy riding, happy gaming!  🎮🚴
