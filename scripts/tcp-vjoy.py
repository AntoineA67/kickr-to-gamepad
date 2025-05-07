#!/usr/bin/env python3
import asyncio
import logging
from dircon_packet import DirconPacket, DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION, DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS, DPKT_PARSE_WAIT
from services import CHARACTERISTICS
from pyvjoystick import vigem as vg

# List of Kickr device IPs (TCP)
DEVICE_IPS = [
    "169.254.3.1",
    "169.254.3.2",
    "169.254.3.3",
    "169.254.3.4",
]

# Device TCP port
DEVICE_PORT = 36866

# Virtual gamepad setup
gamepad = vg.VX360Gamepad()
print("Virtual Xbox360 gamepad created via ViGEmBus")

# Speed scaling
MAX_SPEED_KPH = 80.0  # maximum expected speed

def map_speed_to_stick(speed):
    return int((min(speed, MAX_SPEED_KPH) / MAX_SPEED_KPH) * 32767) * 2

# Store latest speed for each device
global_speeds = {i: 0.0 for i in range(len(DEVICE_IPS))}

# Refactored update_gamepad to use multiple device speeds
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

# Per-device TCP handler
async def handle_device(ip, dev_index):
    logging.info(f"Device {dev_index}: Connecting to {ip}:{DEVICE_PORT}")
    try:
        reader, writer = await asyncio.open_connection(ip, DEVICE_PORT)
    except Exception as e:
        logging.error(f"Device {dev_index}: Connection failed to {ip}: {e}")
        return
    logging.info(f"Device {dev_index}: Connected to {ip}")

    seq = 1
    pkt = DirconPacket()
    pkt.isRequest = True
    pkt.Identifier = DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS
    pkt.uuid = int(CHARACTERISTICS["indoorBikeData"].split("-")[0], 16)
    writer.write(pkt.encode(seq))
    await writer.drain()
    seq += 1

    buf = b""
    while True:
        data = await reader.read(1024)
        if not data:
            break
        buf += data

        resp = DirconPacket()
        result = resp.parse(buf, seq - 1)
        if result == DPKT_PARSE_WAIT:
            continue
        if result < 0:
            logging.error(f"Device {dev_index}: Parse error, resetting buffer")
            buf = b""
            continue
        buf = buf[result:]

        if resp.Identifier == DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION:
            decoded = resp.handle_notification()
            if decoded and "speed" in decoded:
                global_speeds[dev_index] = decoded["speed"]
                update_gamepad()

    writer.close()
    await writer.wait_closed()

# Main entry: launch all device handlers
async def main():
    tasks = [asyncio.create_task(handle_device(ip, idx))
             for idx, ip in enumerate(DEVICE_IPS)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())