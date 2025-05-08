import asyncio
import struct
import logging
from bleak import BleakScanner, BleakClient
from pyvjoystick import vigem as vg

# Set logging level (optional)
logging.basicConfig(level=logging.DEBUG)

# UUIDs for the Fitness Machine service and Indoor Bike Data characteristic.
FITNESS_MACHINE = "00001826-0000-1000-8000-00805f9b34fb"
INDOOR_BIKE_DATA = "00002ad2-0000-1000-8000-00805f9b34fb"

# Virtual gamepad configuration.
# We'll use the following mapping:
#   Device 0: left joystick X (range: 0 to 32767)
#   Device 1: left joystick Y (range: 0 to 32767)
#   Device 2: left trigger (0 to 255)
#   Device 3: right trigger (0 to 255)
MAX_SPEED_KPH = 80.0  # maximum speed expected (in kph) for scaling

# Create a virtual Xbox360 gamepad via ViGEmBus.
gamepad = vg.VX360Gamepad()
print("Virtual Xbox360 gamepad created and connected via ViGEmBus.")

# Global dictionary to hold the latest speed (kph) for each device (by index 0-3).
global_speeds = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}

# Mapping of BLE device names to axis indices (0: left x, 1: left y, 2: right x, 3: right y)
DEVICE_AXIS_MAPPING = {
    "Wahoo KICKR 99CB": 0,
    "Wahoo KICKR B483": 1,
    "Wahoo KICKR 9989": 2,
    "Wahoo KICKR 9985": 3,
}

# --- FTMS Indoor Bike Data Decoding ---


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


# --- Mapping Functions ---
def map_speed_to_stick(speed):
    """
    Map speed (kph) to a joystick value (0 to 32767).
    """
    return int((min(speed, MAX_SPEED_KPH) / MAX_SPEED_KPH) * 32767)


def map_speed_to_trigger(speed):
    """
    Map speed (kph) to a trigger value (0 to 255).
    """
    return int((min(speed, MAX_SPEED_KPH) / MAX_SPEED_KPH) * 255)


def update_gamepad():
    lx = map_speed_to_stick(global_speeds.get(0, 0))
    ly = map_speed_to_stick(global_speeds.get(1, 0))
    rx = map_speed_to_stick(global_speeds.get(2, 0))
    ry = map_speed_to_stick(global_speeds.get(3, 0))
    try:
        gamepad.left_joystick(x_value=lx, y_value=ly)
        gamepad.right_joystick(x_value=rx, y_value=ry)
        gamepad.update()
        print(f"Gamepad updated: LX={lx}, LY={ly}, RX={rx}, RY={ry}")
    except Exception as e:
        print("Error updating gamepad:", e)


# --- Per-Device Notification Handler ---
def device_notification_handler(sender, data, dev_index):
    decoded = decode_indoor_bike_data(data)
    if decoded is None:
        print(
            f"Device {dev_index}: Failed to decode Indoor Bike Data (data too short)."
        )
        return

    print(f"Device {dev_index} Decoded Data:")
    for k, v in decoded.items():
        print(f"  {k}: {v}")

    # Update the global speed if instantaneous speed ("speed") is available.
    if "speed" in decoded:
        speed_kph = decoded["speed"]
        global_speeds[dev_index] = speed_kph
        print(f"Device {dev_index}: Instantaneous Speed = {speed_kph:.2f} kph")
        update_gamepad()
    else:
        print(f"Device {dev_index}: Instantaneous speed not present.")


# --- Asynchronous Connection Routine for Each Device ---
async def handle_device(device, dev_index):
    print(f"Connecting to Device {dev_index}: {device.name} ({device.address})...")
    # Determine axis index from device name mapping
    axis = DEVICE_AXIS_MAPPING.get(device.name)
    if axis is None:
        print(f"Device {dev_index}: No axis mapping for {device.name}. Skipping.")
        return
    async with BleakClient(device.address) as client:
        if not client.is_connected:
            print(f"Device {dev_index}: Failed to connect.")
            return
        print(f"Device {dev_index}: Connected.")
        # Subscribe to Indoor Bike Data notifications using mapped axis
        await client.start_notify(
            INDOOR_BIKE_DATA,
            lambda sender, data: device_notification_handler(sender, data, axis),
        )
        print(f"Device {dev_index}: Subscribed to Indoor Bike Data notifications.")
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print(f"Device {dev_index}: Task cancelled, disconnecting...")
        finally:
            await client.stop_notify(INDOOR_BIKE_DATA)
            print(f"Device {dev_index}: Unsubscribed and disconnected.")


# --- Main Routine: Connect to Up to 4 KICKR Devices Simultaneously ---
async def run():
    print("Scanning for BLE devices advertising the Fitness Machine service...")
    devices = await BleakScanner.discover(timeout=10.0)

    # Filter devices that have "KICKR" in their name.
    kickr_devices = [d for d in devices if d.name and "KICKR" in d.name]
    if not kickr_devices:
        print("No KICKR devices found. Exiting.")
        return

    # Limit to up to 4 devices.
    selected_devices = kickr_devices[:4]
    print(f"Selected {len(selected_devices)} KICKR device(s) for connection.")

    # Create asynchronous tasks for each device.
    tasks = []
    for idx, dev in enumerate(selected_devices):
        tasks.append(asyncio.create_task(handle_device(dev, idx)))

    # Run all device tasks concurrently.
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received; cancelling tasks...")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(run())
