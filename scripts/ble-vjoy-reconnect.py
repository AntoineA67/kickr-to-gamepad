import sys
# Force COM to initialize as MTA on Windows (must precede any STA-using imports)
sys.coinit_flags = 0
# from bleak.backends.winrt.util import uninitialize_sta
# uninitialize_sta()

import asyncio
import struct
import logging
from bleak import BleakScanner, BleakClient
from pyvjoystick import vigem as vg

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# BLE Service/Characteristic UUIDs
FITNESS_MACHINE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
INDOOR_BIKE_DATA_UUID = "00002ad2-0000-1000-8000-00805f9b34fb"

# Virtual gamepad setup
gamepad = vg.VX360Gamepad()
MAX_SPEED_KPH = 80.0

# Global speed storage
global_speeds = {i: 0.0 for i in range(4)}

# Name-to-axis index mapping
DEVICE_AXIS_MAPPING = {
    "Wahoo KICKR 99CB": 0,
    "Wahoo KICKR B483": 1,
    "Wahoo KICKR 9989": 2,
    "Wahoo KICKR 9985": 3,
}

# Decode definitions omitted for brevity (use your existing FIELD_DEFS and decode_indoor_bike_data)
# -- INSERT your FIELD_DEFS list and decode_indoor_bike_data(data) here --

# Mapping functions

def map_speed_to_stick(speed: float) -> int:
    return int((min(speed, MAX_SPEED_KPH) / MAX_SPEED_KPH) * 32767)


def update_gamepad():
    lx = map_speed_to_stick(global_speeds[0])
    ly = map_speed_to_stick(global_speeds[1])
    rx = map_speed_to_stick(global_speeds[2])
    ry = map_speed_to_stick(global_speeds[3])
    gamepad.left_joystick(x_value=lx, y_value=ly)
    gamepad.right_joystick(x_value=rx, y_value=ry)
    gamepad.update()
    logging.debug(f"Gamepad updated: LX={lx}, LY={ly}, RX={rx}, RY={ry}")


def device_notification_handler(sender, data, axis_index):
    decoded = decode_indoor_bike_data(data)
    if decoded is None:
        logging.warning(f"[{sender}] Short payload, can't decode.")
        return
    if "speed" in decoded:
        speed = decoded["speed"]
        global_speeds[axis_index] = speed
        logging.info(f"[{sender}] Speed={speed:.2f} kph (axis {axis_index})")
        update_gamepad()

async def handle_device_loop(device, axis_index):
    """
    Keep trying to connect, subscribe, and handle notifications.
    Reconnect automatically on any failure or disconnect.
    """
    while True:
        try:
            logging.info(f"{device.name}: Connecting...")
            async with BleakClient(device,
                                   services={FITNESS_MACHINE_UUID},
                                   timeout=30.0) as client:
                if client.is_connected:
                    logging.info(f"{device.name}: Connected")
                    await client.start_notify(
                        INDOOR_BIKE_DATA_UUID,
                        lambda s, d: device_notification_handler(s, d, axis_index)
                    )
                    # Keep alive until disconnected
                    while client.is_connected:
                        await asyncio.sleep(1)
                    logging.warning(f"{device.name}: Disconnected")
        except Exception as e:
            logging.error(f"{device.name}: Error - {e}")
        logging.info(f"{device.name}: Reconnecting in 5 seconds...")
        await asyncio.sleep(5)

async def main():
    # Discover KICKR devices advertising the FTMS service
    logging.info("Scanning for KICKR devices...")
    devices = await BleakScanner.discover(
        timeout=20.0,
        service_uuids=[FITNESS_MACHINE_UUID]
    )
    kickrs = [d for d in devices if d.name and "KICKR" in d.name][:4]
    if not kickrs:
        logging.error("No KICKR devices found. Exiting.")
        return
    logging.info(f"Found {len(kickrs)} KICKR(s), starting handlers...")
    # Launch a reconnecting handler for each
    for d in kickrs:
        axis = DEVICE_AXIS_MAPPING.get(d.name)
        if axis is None:
            logging.warning(f"Unknown device name '{d.name}', skipping.")
            continue
        asyncio.create_task(handle_device_loop(d, axis))
    # Never exit
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down by user request.")
