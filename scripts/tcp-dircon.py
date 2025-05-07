#!/usr/bin/env python3
import asyncio
import logging
from dircon_packet import DirconPacket, DPKT_MSGID_READ_CHARACTERISTIC, DPKT_PARSE_WAIT
from services import (
    SERVICES,
    CHARACTERISTICS,
    get_service_name,
    get_characteristic_name,
    parse_service_uuids,
    parse_discovered_characteristics,
    get_property_names,
)

# -------------------------------------------------------------------
# Constants and Definitions
# -------------------------------------------------------------------
DPKT_MESSAGE_HEADER_LENGTH = 6
DPKT_CHAR_PROP_FLAG_READ = 0x01
DPKT_CHAR_PROP_FLAG_WRITE = 0x02
DPKT_CHAR_PROP_FLAG_NOTIFY = 0x04

# Message Identifiers
DPKT_MSGID_ERROR = 0xFF
DPKT_MSGID_DISCOVER_SERVICES = 0x01
DPKT_MSGID_DISCOVER_CHARACTERISTICS = 0x02
DPKT_MSGID_READ_CHARACTERISTIC = 0x03
DPKT_MSGID_WRITE_CHARACTERISTIC = 0x04
DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS = 0x05
DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION = 0x06

# Response Codes
DPKT_RESPCODE_SUCCESS_REQUEST = 0x00
DPKT_RESPCODE_SERVICE_NOT_FOUND = 0x03
DPKT_RESPCODE_CHARACTERISTIC_NOT_FOUND = 0x04
DPKT_RESPCODE_CHARACTERISTIC_OPERATION_NOT_SUPPORTED = 0x05
DPKT_RESPCODE_UNEXPECTED_ERROR = 0x02

# Parse return codes
DPKT_PARSE_ERROR = -20

# Positions in the base UUID (positions 2 and 3)
DPKT_POS_SH8 = 2
DPKT_POS_SH0 = 3

# The base UUID defined in the original code.
BASE_UUID = bytearray(
    [
        0x00,
        0x00,
        0x18,
        0x26,
        0x00,
        0x00,
        0x10,
        0x00,
        0x80,
        0x00,
        0x00,
        0x80,
        0x5F,
        0x9B,
        0x34,
        0xFB,
    ]
)

# Device connection parameters
DEVICE_IP = "169.254.3.1"
DEVICE_PORT = 36866  # Adjust if your device uses another TCP port

# Map of resistance levels 1-10 to their corresponding values
resistance_values = {
    1: [0x32, 0x00],  # Level 1  (50)
    2: [0x64, 0x00],  # Level 2  (100)
    3: [0x96, 0x00],  # Level 3  (150)
    4: [0xC8, 0x00],  # Level 4  (200)
    5: [0xFA, 0x00],  # Level 5  (250)
    6: [0x2C, 0x01],  # Level 6  (300)
    7: [0x5E, 0x01],  # Level 7  (350)
    8: [0x90, 0x01],  # Level 8  (400)
    9: [0xC2, 0x01],  # Level 9  (450)
    10: [0xF4, 0x01],  # Level 10 (500)
    11: [0x26, 0x02],  # Level 11 (550)
    12: [0x58, 0x02],  # Level 12 (600)
}

# Message Identifiers mapping
MESSAGE_IDENTIFIERS = {
    DPKT_MSGID_ERROR: "ERROR",
    DPKT_MSGID_DISCOVER_SERVICES: "DISCOVER_SERVICES",
    DPKT_MSGID_DISCOVER_CHARACTERISTICS: "DISCOVER_CHARACTERISTICS",
    DPKT_MSGID_READ_CHARACTERISTIC: "READ_CHARACTERISTIC",
    DPKT_MSGID_WRITE_CHARACTERISTIC: "WRITE_CHARACTERISTIC",
    DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS: "ENABLE_NOTIFICATIONS",
    DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION: "NOTIFICATION",
}

# Response Codes mapping
RESPONSE_CODES = {
    DPKT_RESPCODE_SUCCESS_REQUEST: "SUCCESS",
    DPKT_RESPCODE_SERVICE_NOT_FOUND: "SERVICE_NOT_FOUND",
    DPKT_RESPCODE_CHARACTERISTIC_NOT_FOUND: "CHARACTERISTIC_NOT_FOUND",
    DPKT_RESPCODE_CHARACTERISTIC_OPERATION_NOT_SUPPORTED: "OPERATION_NOT_SUPPORTED",
    DPKT_RESPCODE_UNEXPECTED_ERROR: "UNEXPECTED_ERROR",
}


def set_resistance(level):
    if not 1 <= level <= 10:
        print("Resistance level must be between 1 and 10")
        return

    pkt = DirconPacket()
    pkt.MessageVersion = 1
    pkt.Identifier = DPKT_MSGID_WRITE_CHARACTERISTIC
    pkt.ResponseCode = DPKT_RESPCODE_SUCCESS_REQUEST
    pkt.uuid = int(CHARACTERISTICS["fitnessMachineControlPoint"].split("-")[0], 16)

    # Get the resistance value for the given level
    resistance_bytes = resistance_values[level]
    # Format the additional data with the resistance value
    pkt.additional_data = bytes(
        [0x11, 0x00, 0x00, 0x4F, 0x01] + resistance_bytes + [0x3C]
    )

    return pkt.encode(0)


class NotificationHandler:
    def __init__(self):
        self.enabled_notifications = set()

    def handle_notification(self, pkt):
        """Handle a notification packet"""
        result = pkt.handle_notification()


async def async_input(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)


async def send_request(writer, pkt, seq):
    """Send a request and return the sequence number for the next request"""
    request_bytes = pkt.encode(seq)
    print(f"Sending request: {request_bytes.hex()}")
    writer.write(request_bytes)
    await writer.drain()
    # logging.info("Sent request %s", pkt.Identifier)
    return seq + 1


async def discover_all_services_and_characteristics(writer, reader, seq):
    """Discover all services and their characteristics, then save to discover.txt"""
    # First discover all services
    pkt = DirconPacket()
    pkt.isRequest = True
    pkt.Identifier = DPKT_MSGID_DISCOVER_SERVICES
    seq = await send_request(writer, pkt, seq)

    # Wait for the response in the read_loop
    await asyncio.sleep(1)  # Give time for the response to arrive

    # Open file for writing
    with open("discover.txt", "w") as f:
        f.write("BLE Services and Characteristics Discovery\n")
        f.write("=========================================\n\n")

        # Get the services from the last response
        services = []
        for uuid, name, _ in parse_service_uuids(
            processed_data[DPKT_MESSAGE_HEADER_LENGTH:]
        ):
            if name:
                services.append((uuid, name))

        # For each service, discover its characteristics
        for service_uuid, service_name in services:
            f.write(f"Service: {service_name}\n")
            f.write(f"UUID: {service_uuid}\n")
            f.write("Characteristics:\n")

            # Discover characteristics for this service
            pkt = DirconPacket()
            pkt.isRequest = True
            pkt.Identifier = DPKT_MSGID_DISCOVER_CHARACTERISTICS
            pkt.uuid = int(service_uuid.split("-")[0], 16)
            seq = await send_request(writer, pkt, seq)

            # Wait for the response in the read_loop
            await asyncio.sleep(1)  # Give time for the response to arrive

            # Parse the characteristics from the last response
            characteristics = parse_discovered_characteristics(processed_data)

            # Write characteristics to file
            for char_uuid, char_name, properties, value_handle in characteristics:
                if char_name:
                    prop_names = get_property_names(properties)
                    f.write(f"  {char_name}:\n")
                    f.write(f"    UUID: {char_uuid}\n")
                    f.write(f"    Properties: {', '.join(prop_names)}\n")
                    f.write(f"    Value Handle: 0x{value_handle:04X}\n")
                else:
                    f.write(f"  Unknown Characteristic: {char_uuid}\n")

            f.write("\n")

    logging.info("Discovery complete. Results saved to discover.txt")
    return seq


# Add a global variable to store the last processed data
processed_data = None




async def tcp_client():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    try:
        reader, writer = await asyncio.open_connection(DEVICE_IP, DEVICE_PORT)
    except Exception as e:
        logging.error("Could not connect to %s:%s: %s", DEVICE_IP, DEVICE_PORT, e)
        return

    logging.info("Connected to device at %s:%s", DEVICE_IP, DEVICE_PORT)
    seq = 1
    notification_handler = NotificationHandler()

    async def read_loop():
        global processed_data
        read_buffer = b""  # Local buffer for the read loop
        while True:
            try:
                data = await reader.read(1024)
                if not data:
                    break
                print(f"\nRAW INCOMING DATA: {data.hex()}")
                read_buffer += data

                # Try to parse as a packet
                print(f"Read buffer: {read_buffer.hex()}")
                response_pkt = DirconPacket()
                result = response_pkt.parse(read_buffer, seq - 1)

                if result == DPKT_PARSE_WAIT:
                    print("Waiting for more data")
                    # If we need to wait for more data, continue reading
                    continue
                elif result < 0:
                    logging.error("Packet parse error (result=%d)", result)
                    read_buffer = b""
                else:
                    # If we have a valid packet, process it and remove the processed data
                    processed_data = read_buffer[:result]
                    read_buffer = read_buffer[result:]

                    if (
                        response_pkt.Identifier
                        == DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION
                    ):
                        notification_handler.handle_notification(response_pkt)
                    else:
                        msg_type = MESSAGE_IDENTIFIERS.get(
                            response_pkt.Identifier,
                            f"UNKNOWN (0x{response_pkt.Identifier:02X})",
                        )
                        resp_code = RESPONSE_CODES.get(
                            response_pkt.ResponseCode,
                            f"UNKNOWN (0x{response_pkt.ResponseCode:02X})",
                        )

                        logging.info("Received response:")
                        logging.info("  Message Type: %s", msg_type)
                        logging.info("  Response: %s", resp_code)

                        # Get UUID name if known
                        uuid_name = get_characteristic_name(f"{response_pkt.uuid:04x}")
                        if uuid_name:
                            logging.info(
                                "  UUID: %s (0x%04X)", uuid_name, response_pkt.uuid
                            )
                        else:
                            logging.info("  UUID: 0x%04X", response_pkt.uuid)

                        # For DISCOVER_SERVICES, the additional data contains the service UUIDs
                        if response_pkt.Identifier == DPKT_MSGID_DISCOVER_SERVICES:
                            # The additional data starts after the header (6 bytes)
                            service_data = processed_data[DPKT_MESSAGE_HEADER_LENGTH:]
                            logging.info("  Services:")
                            services = parse_service_uuids(service_data)
                            for uuid, name, characteristics in services:
                                if name:
                                    logging.info(f"    {name}: {uuid}")
                                    if characteristics:
                                        logging.info("      Characteristics:")
                                        for char_name, char_uuid in characteristics.items():
                                            logging.info(
                                                f"        {char_name}: {char_uuid}"
                                            )
                                else:
                                    logging.info(f"    Unknown Service: {uuid}")
                        elif response_pkt.Identifier == DPKT_MSGID_DISCOVER_CHARACTERISTICS:
                            # The additional data starts after the header (6 bytes)
                            char_data = processed_data[DPKT_MESSAGE_HEADER_LENGTH:]
                            logging.info("  Characteristics:")
                            characteristics = parse_discovered_characteristics(
                                processed_data
                            )
                            for uuid, name, properties, value_handle in characteristics:
                                if name:
                                    prop_names = get_property_names(properties)
                                    logging.info(f"    {name}:")
                                    logging.info(f"      UUID: {uuid}")
                                    logging.info(
                                        f"      Properties: {', '.join(prop_names)}"
                                    )
                                    logging.info(
                                        f"      Value Handle: 0x{value_handle:04X}"
                                    )
                                else:
                                    logging.info(f"    Unknown Characteristic: {uuid}")
                        else:
                            logging.info(
                                "  Additional Data (hex): %s",
                                response_pkt.additional_data.hex(),
                            )
            except Exception as e:
                logging.error(f"Error in read loop: {e}")
                break
    # Start a background task to read and print all incoming data
    read_task = asyncio.create_task(read_loop())

    while True:
        print("\nAvailable commands:")
        print("1. Read Speed Characteristic")
        print("2. Discover Services")
        print("3. Discover Characteristics")
        print("4. Write Characteristic")
        print("5. Enable Notifications")
        print("6. Disable Notifications")
        print("7. Discover All Services and Characteristics")
        print("q. Quit")

        choice = (await async_input("\nEnter your choice: ")).strip().lower()

        if choice == "q":
            read_task.cancel()
            break

        pkt = DirconPacket()
        pkt.isRequest = True

        if choice == "1":
            pkt.Identifier = DPKT_MSGID_READ_CHARACTERISTIC
            pkt.uuid = int(CHARACTERISTICS["indoorBikeData"].split("-")[0], 16)
        elif choice == "2":
            pkt.Identifier = DPKT_MSGID_DISCOVER_SERVICES
        elif choice == "3":
            pkt.Identifier = DPKT_MSGID_DISCOVER_CHARACTERISTICS
            pkt.uuid = int(SERVICES["fitnessMachine"].split("-")[0], 16)
        elif choice == "4":
            pkt.Identifier = DPKT_MSGID_WRITE_CHARACTERISTIC
            pkt.uuid = int(
                CHARACTERISTICS["fitnessMachineControlPoint"].split("-")[0], 16
            )

            print("\nResistance Control:")
            print("Enter a resistance level between 1-12")
            try:
                level = int(await async_input("Resistance level: "))
                if not 1 <= level <= 12:
                    print("Invalid level. Must be between 1 and 12.")
                    continue

                # Get the resistance value for the given level
                resistance_bytes = resistance_values[level]
                # Format the additional data with the resistance value
                pkt.additional_data = bytes(
                    [0x11, 0x00, 0x00] + [0x4F, 0x01] + resistance_bytes + [0x3C]
                )
                print(f"Setting resistance to level {level}")

            except ValueError:
                print("Invalid input. Please enter a number between 1 and 12.")
                continue
        elif choice == "5":
            pkt.Identifier = DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS
            pkt.uuid = int(CHARACTERISTICS["indoorBikeData"].split("-")[0], 16)
        elif choice == "6":
            pkt.Identifier = DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS
            pkt.uuid = int(CHARACTERISTICS["indoorBikeData"].split("-")[0], 16)
        elif choice == "7":
            seq = await discover_all_services_and_characteristics(writer, reader, seq)
            continue
        else:
            print("Invalid choice. Please try again.")
            continue

        seq = await send_request(writer, pkt, seq)

        # Small delay to allow response to arrive
        await asyncio.sleep(0.1)

    read_task.cancel()
    writer.close()
    await writer.wait_closed()
    logging.info("Connection closed")


async def main():
    await tcp_client()


if __name__ == "__main__":
    asyncio.run(main())
