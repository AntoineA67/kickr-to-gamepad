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


# Field present condition functions based on the Flags field.
def speed_present(flags):
    # InstantaneousSpeed is present if bit 0 is 0.
    return ((flags >> 0) & 1) == 0


def avg_speed_present(flags):
    return ((flags >> 1) & 1) == 1


def cadence_present(flags):
    return ((flags >> 2) & 1) == 1


def avg_cadence_present(flags):
    return ((flags >> 3) & 1) == 1


def distance_present(flags):
    return ((flags >> 4) & 1) == 1


def resistance_present(flags):
    return ((flags >> 5) & 1) == 1


def power_present(flags):
    return ((flags >> 6) & 1) == 1


def avg_power_present(flags):
    return ((flags >> 7) & 1) == 1


def expanded_energy_present(flags):
    return ((flags >> 8) & 1) == 1


def heart_rate_present(flags):
    return ((flags >> 9) & 1) == 1


def metabolic_equivalent_present(flags):
    return ((flags >> 10) & 1) == 1


def elapsed_time_present(flags):
    return ((flags >> 11) & 1) == 1


def remaining_time_present(flags):
    return ((flags >> 12) & 1) == 1


# Field definitions for the Indoor Bike Data characteristic.
# Each field definition includes its name, size (bytes), type, resolution,
# optional unit, a function to test its presence given the Flags value,
# and an optional "short" alias.
FIELD_DEFS = [
    {
        "name": "Flags",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "present": lambda flags: True,
    },
    {
        "name": "InstantaneousSpeed",
        "size": 2,
        "type": "Uint16",
        "resolution": 0.01,
        "unit": "kph",
        "present": speed_present,
        "short": "speed",
    },
    {
        "name": "AverageSpeed",
        "size": 2,
        "type": "Uint16",
        "resolution": 0.01,
        "unit": "kph",
        "present": avg_speed_present,
    },
    {
        "name": "InstantaneousCadence",
        "size": 2,
        "type": "Uint16",
        "resolution": 0.5,
        "unit": "rpm",
        "present": cadence_present,
        "short": "cadence",
    },
    {
        "name": "AverageCadence",
        "size": 2,
        "type": "Uint16",
        "resolution": 0.5,
        "unit": "rpm",
        "present": avg_cadence_present,
    },
    {
        "name": "TotalDistance",
        "size": 3,
        "type": "Uint24",
        "resolution": 1,
        "unit": "m",
        "present": distance_present,
        "short": "distance",
    },
    {
        "name": "ResistanceLevel",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "unitless",
        "present": resistance_present,
    },
    {
        "name": "InstantaneousPower",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "W",
        "present": power_present,
        "short": "power",
    },
    {
        "name": "AveragePower",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "W",
        "present": avg_power_present,
    },
    {
        "name": "TotalEnergy",
        "size": 2,
        "type": "Int16",
        "resolution": 1,
        "unit": "kcal",
        "present": expanded_energy_present,
    },
    {
        "name": "EnergyPerHour",
        "size": 2,
        "type": "Int16",
        "resolution": 1,
        "unit": "kcal",
        "present": expanded_energy_present,
    },
    {
        "name": "EnergyPerMinute",
        "size": 1,
        "type": "Uint8",
        "resolution": 1,
        "unit": "kcal",
        "present": expanded_energy_present,
    },
    {
        "name": "HeartRate",
        "size": 1,
        "type": "Uint8",
        "resolution": 1,
        "unit": "bpm",
        "present": heart_rate_present,
        "short": "heartRate",
    },
    {
        "name": "MetabolicEquivalent",
        "size": 1,
        "type": "Uint8",
        "resolution": 1,
        "unit": "me",
        "present": metabolic_equivalent_present,
    },
    {
        "name": "ElapsedTime",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "s",
        "present": elapsed_time_present,
    },
    {
        "name": "RemainingTime",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "s",
        "present": remaining_time_present,
    },
]

def decode_indoor_bike_data(data: bytes):
    """
    Decode the FTMS Indoor Bike Data characteristic.
    Returns a dictionary mapping field names (or their short names) to decoded values.
    """
    result = {}
    offset = 0

    # First field: Flags (2 bytes, Uint16).
    if len(data) < 2:
        return None
    flags = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    result["Flags"] = flags

    # Process each remaining field.
    for field in FIELD_DEFS[1:]:
        if offset + field["size"] > len(data):
            break  # Not enough data remains.
        if field["present"](flags):
            # Decode based on type.
            if field["type"] == "Uint16":
                val = struct.unpack_from("<H", data, offset)[0]
            elif field["type"] == "Int16":
                val = struct.unpack_from("<h", data, offset)[0]
            elif field["type"] == "Uint8":
                val = struct.unpack_from("<B", data, offset)[0]
            elif field["type"] == "Uint24":
                b0, b1, b2 = data[offset], data[offset + 1], data[offset + 2]
                val = b0 + (b1 << 8) + (b2 << 16)
            else:
                val = None
            value = val * field["resolution"]
            key = field.get("short", field["name"])
            result[key] = value
        offset += field["size"]
    return result

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
        logging.info(f"{device.name}: Reconnecting in 3 seconds...")
        await asyncio.sleep(3)

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
