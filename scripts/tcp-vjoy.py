#!/usr/bin/env python3
import asyncio
import logging
from dircon_packet import DirconPacket, DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION, DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS, DPKT_PARSE_WAIT
from services import CHARACTERISTICS
from pyvjoystick import vigem as vg

# Device connection parameters
DEVICE_IP = "169.254.3.1"
DEVICE_PORT = 36866

# Virtual gamepad setup
gamepad = vg.VX360Gamepad()
print("Virtual Xbox360 gamepad created via ViGEmBus")

# Speed scaling
MAX_SPEED_KPH = 80.0  # maximum expected speed

def map_speed_to_stick(speed):
    return int((min(speed, MAX_SPEED_KPH) / MAX_SPEED_KPH) * 32767)

# Store latest speed
global_speed = 0.0

def update_gamepad():
    x = map_speed_to_stick(global_speed)
    try:
        gamepad.left_joystick(x_value=x, y_value=0)
        gamepad.update()
        print(f"Gamepad updated: LX={x}")
    except Exception as e:
        print("Error updating gamepad:", e)

async def tcp_vjoy():
    logging.basicConfig(level=logging.INFO)
    try:
        reader, writer = await asyncio.open_connection(DEVICE_IP, DEVICE_PORT)
    except Exception as e:
        logging.error(f"Failed to connect to {DEVICE_IP}:{DEVICE_PORT}: {e}")
        return
    logging.info(f"Connected to {DEVICE_IP}:{DEVICE_PORT}")

    # Enable notifications for Indoor Bike Data
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

        # Parse incoming packets
        resp = DirconPacket()
        result = resp.parse(buf, seq - 1)
        if result == DPKT_PARSE_WAIT:
            continue
        if result < 0:
            logging.error("Parse error, resetting buffer")
            buf = b""
            continue
        buf = buf[result:]

        # Handle notification
        if resp.Identifier == DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION:
            decoded = resp.handle_notification()
            if decoded and "speed" in decoded:
                global global_speed
                global_speed = decoded["speed"]
                update_gamepad()

    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    asyncio.run(tcp_vjoy())