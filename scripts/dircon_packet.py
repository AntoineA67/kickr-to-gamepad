#!/usr/bin/env python3
import struct

INDOOR_BIKE_DATA_CHAR_UUID = 0x2AD2
BIKE_RESISTANCE_GAIN_CHAR_UUID = 0x2AD9


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
DPKT_RESPCODE_CHARACTERISTIC_WRITE_FAILED = 0x06
DPKT_RESPCODE_UNKNOWN_PROTOCOL = 0x07

DPKT_RESPCODE_UNEXPECTED_ERROR = 0x02

# Parse return codes
DPKT_PARSE_ERROR = -20
DPKT_PARSE_WAIT = -3

# Positions in the base UUID (positions 2 and 3)
DPKT_POS_SH8 = 2
DPKT_POS_SH0 = 3

# The base UUID defined in the original code.
BASE_UUID = bytearray([
    0x00, 0x00, 0x18, 0x26, 0x00, 0x00, 0x10, 0x00,
    0x80, 0x00, 0x00, 0x80, 0x5F, 0x9B, 0x34, 0xFB
])

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
        "present": lambda flags: ((flags >> 0) & 1) == 0,
        "short": "speed",
    },
    {
        "name": "AverageSpeed",
        "size": 2,
        "type": "Uint16",
        "resolution": 0.01,
        "unit": "kph",
        "present": lambda flags: ((flags >> 1) & 1) == 1,
    },
    {
        "name": "InstantaneousCadence",
        "size": 2,
        "type": "Uint16",
        "resolution": 0.5,
        "unit": "rpm",
        "present": lambda flags: ((flags >> 2) & 1) == 1,
        "short": "cadence",
    },
    {
        "name": "AverageCadence",
        "size": 2,
        "type": "Uint16",
        "resolution": 0.5,
        "unit": "rpm",
        "present": lambda flags: ((flags >> 3) & 1) == 1,
    },
    {
        "name": "TotalDistance",
        "size": 3,
        "type": "Uint24",
        "resolution": 1,
        "unit": "m",
        "present": lambda flags: ((flags >> 4) & 1) == 1,
        "short": "distance",
    },
    {
        "name": "ResistanceLevel",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "unitless",
        "present": lambda flags: ((flags >> 5) & 1) == 1,
    },
    {
        "name": "InstantaneousPower",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "W",
        "present": lambda flags: ((flags >> 6) & 1) == 1,
        "short": "power",
    },
    {
        "name": "AveragePower",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "W",
        "present": lambda flags: ((flags >> 7) & 1) == 1,
    },
    {
        "name": "TotalEnergy",
        "size": 2,
        "type": "Int16",
        "resolution": 1,
        "unit": "kcal",
        "present": lambda flags: ((flags >> 8) & 1) == 1,
    },
    {
        "name": "EnergyPerHour",
        "size": 2,
        "type": "Int16",
        "resolution": 1,
        "unit": "kcal",
        "present": lambda flags: ((flags >> 9) & 1) == 1,
    },
    {
        "name": "EnergyPerMinute",
        "size": 1,
        "type": "Uint8",
        "resolution": 1,
        "unit": "kcal",
        "present": lambda flags: ((flags >> 10) & 1) == 1,
    },
    {
        "name": "HeartRate",
        "size": 1,
        "type": "Uint8",
        "resolution": 1,
        "unit": "bpm",
        "present": lambda flags: ((flags >> 11) & 1) == 1,
        "short": "heartRate",
    },
    {
        "name": "MetabolicEquivalent",
        "size": 1,
        "type": "Uint8",
        "resolution": 1,
        "unit": "me",
        "present": lambda flags: ((flags >> 12) & 1) == 1,
    },
    {
        "name": "ElapsedTime",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "s",
        "present": lambda flags: ((flags >> 13) & 1) == 1,
    },
    {
        "name": "RemainingTime",
        "size": 2,
        "type": "Uint16",
        "resolution": 1,
        "unit": "s",
        "present": lambda flags: ((flags >> 14) & 1) == 1,
    },
]

# -------------------------------------------------------------------
# DirconPacket class: Implements encoding and decoding of Dircon packets.
# This mirrors the logic in the original dirconpacket.cpp/h.
# -------------------------------------------------------------------
class DirconPacket:
    def __init__(self):
        self.MessageVersion = 1
        self.Identifier = DPKT_MSGID_ERROR
        self.SequenceNumber = 0
        self.ResponseCode = DPKT_RESPCODE_SUCCESS_REQUEST
        self.Length = 0
        self.uuid = 0
        self.uuids = []  # List of 16-bit UUIDs (integers)
        self.additional_data = b""
        self.isRequest = False
        self.last_crank_revs = 0
        self.last_crank_time = 0
        self.last_wheel_revs = 0
        self.last_wheel_time = 0

    def decode_indoor_bike_data(self, data: bytes):
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

    def handle_notification(self):
        """Handle a notification packet and return formatted data"""
        if self.Identifier != DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION:
            return None
        
        dev_index = 0

        if self.uuid == INDOOR_BIKE_DATA_CHAR_UUID:  # Cycling Power Measurement
            decoded = self.decode_indoor_bike_data(self.additional_data)
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
                # global_speeds[dev_index] = speed_kph
                print(f"Device {dev_index}: Instantaneous Speed = {speed_kph:.2f} kph")
                # update_gamepad()
            else:
                print(f"Device {dev_index}: Instantaneous speed not present.")
            return decoded
        return None

    def parse(self, buf: bytes, last_seq_number: int) -> int:
        if len(buf) < DPKT_MESSAGE_HEADER_LENGTH:
            return DPKT_PARSE_WAIT

        self.MessageVersion = buf[0]
        self.Identifier = buf[1]
        self.SequenceNumber = buf[2]
        self.ResponseCode = buf[3]
        self.Length = (buf[4] << 8) | buf[5]
        self.isRequest = False
        
        # print(f"Received packet: {self.Identifier} {self.Length}")

        total_length = DPKT_MESSAGE_HEADER_LENGTH + self.Length
        if len(buf) < total_length:
            return DPKT_PARSE_WAIT

        if self.ResponseCode != DPKT_RESPCODE_SUCCESS_REQUEST:
            return total_length

        if self.Identifier == DPKT_MSGID_DISCOVER_SERVICES:
            if self.Length == 0:
                self.isRequest = (last_seq_number <= 0 or last_seq_number != self.SequenceNumber)
                return DPKT_MESSAGE_HEADER_LENGTH
            elif self.Length % 16 == 0:
                self.uuids = []
                count = self.Length // 16
                offset = DPKT_MESSAGE_HEADER_LENGTH
                for _ in range(count):
                    block = buf[offset: offset + 16]
                    uuid_val = (block[DPKT_POS_SH8] << 8) | block[DPKT_POS_SH0]
                    self.uuids.append(uuid_val)
                    offset += 16
                return total_length
            else:
                return DPKT_PARSE_ERROR - total_length
        elif self.Identifier == DPKT_MSGID_DISCOVER_CHARACTERISTICS:
            if self.Length >= 16:
                offset = DPKT_MESSAGE_HEADER_LENGTH
                block = buf[offset: offset + 16]
                self.uuid = (block[DPKT_POS_SH8] << 8) | block[DPKT_POS_SH0]
                if self.Length == 16:
                    self.isRequest = (last_seq_number <= 0 or last_seq_number != self.SequenceNumber)
                    return total_length
                elif (self.Length - 16) % 17 == 0:
                    self.uuids = []
                    self.additional_data = b""
                    offset += 16
                    count = (self.Length - 16) // 17
                    for _ in range(count):
                        block = buf[offset: offset + 16]
                        uuid_val = (block[DPKT_POS_SH8] << 8) | block[DPKT_POS_SH0]
                        self.uuids.append(uuid_val)
                        self.additional_data += buf[offset + 16: offset + 17]
                        offset += 17
                    return total_length
                else:
                    return DPKT_PARSE_ERROR - total_length
            else:
                return DPKT_PARSE_ERROR - total_length
        elif self.Identifier == DPKT_MSGID_READ_CHARACTERISTIC:
            # print(f"Read Characteristic: {self.Length}")
            if self.Length >= 16:
                offset = DPKT_MESSAGE_HEADER_LENGTH
                block = buf[offset: offset + 16]
                self.uuid = (block[DPKT_POS_SH8] << 8) | block[DPKT_POS_SH0]
                # print(f"length: {self.Length}, buf: {buf.hex()}")
                if self.Length == 16:
                    self.isRequest = (last_seq_number <= 0 or last_seq_number != self.SequenceNumber)
                    self.additional_data = buf[offset + 4: total_length]
                # else:
                #     self.additional_data = buf[offset + 16: total_length]
                    # print(f"Additional Data on read: {self.additional_data.hex()}")    
                return total_length
            else:
                return DPKT_PARSE_ERROR - total_length
        elif self.Identifier == DPKT_MSGID_WRITE_CHARACTERISTIC:
            if self.Length > 16:
                offset = DPKT_MESSAGE_HEADER_LENGTH
                block = buf[offset: offset + 16]
                self.uuid = (block[DPKT_POS_SH8] << 8) | block[DPKT_POS_SH0]
                self.additional_data = buf[offset + 16: total_length]
                self.isRequest = (last_seq_number <= 0 or last_seq_number != self.SequenceNumber)
                return total_length
            else:
                return DPKT_PARSE_ERROR - total_length
        elif self.Identifier == DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS:
            if self.Length in (16, 17):
                offset = DPKT_MESSAGE_HEADER_LENGTH
                block = buf[offset: offset + 16]
                self.uuid = (block[DPKT_POS_SH8] << 8) | block[DPKT_POS_SH0]
                if self.Length == 17:
                    self.isRequest = True
                    self.additional_data = buf[offset + 16: offset + 17]
                return total_length
            else:
                return DPKT_PARSE_ERROR - total_length
        elif self.Identifier == DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION:
            if self.Length > 16:
                offset = DPKT_MESSAGE_HEADER_LENGTH
                block = buf[offset: offset + 16]
                self.uuid = (block[DPKT_POS_SH8] << 8) | block[DPKT_POS_SH0]
                self.additional_data = buf[offset + 16: total_length]
                return total_length
            else:
                return DPKT_PARSE_ERROR - total_length
        else:
            return DPKT_PARSE_ERROR - total_length

    def encode(self, last_seq_number: int) -> bytes:
        if self.Identifier == DPKT_MSGID_ERROR:
            return b""
        if self.isRequest:
            self.SequenceNumber = last_seq_number & 0xFF
        elif self.Identifier == DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION:
            self.SequenceNumber = 0
        else:
            self.SequenceNumber = last_seq_number
        self.MessageVersion = 1

        out = bytearray()
        out.append(self.MessageVersion)
        out.append(self.Identifier)
        out.append(self.SequenceNumber)
        out.append(self.ResponseCode)
        payload = bytearray()

        # Build payload based on message type.
        if (not self.isRequest) and self.ResponseCode != DPKT_RESPCODE_SUCCESS_REQUEST:
            self.Length = 0
        else:
            if self.Identifier == DPKT_MSGID_DISCOVER_SERVICES:
                if self.isRequest:
                    self.Length = 0
                else:
                    self.Length = len(self.uuids) * 16
                    for u in self.uuids:
                        block = bytearray(BASE_UUID)
                        block[DPKT_POS_SH8] = (u >> 8) & 0xFF
                        block[DPKT_POS_SH0] = u & 0xFF
                        payload.extend(block)
            elif self.Identifier == DPKT_MSGID_DISCOVER_CHARACTERISTICS and (not self.isRequest):
                self.Length = 16 + len(self.uuids) * 17
                block = bytearray(BASE_UUID)
                block[DPKT_POS_SH8] = (self.uuid >> 8) & 0xFF
                block[DPKT_POS_SH0] = self.uuid & 0xFF
                payload.extend(block)
                for i, u in enumerate(self.uuids):
                    block = bytearray(BASE_UUID)
                    block[DPKT_POS_SH8] = (u >> 8) & 0xFF
                    block[DPKT_POS_SH0] = u & 0xFF
                    payload.extend(block)
                    if i < len(self.additional_data):
                        payload.append(self.additional_data[i])
                    else:
                        payload.append(0)
            elif ((self.Identifier in (DPKT_MSGID_READ_CHARACTERISTIC,
                                       DPKT_MSGID_DISCOVER_CHARACTERISTICS) and self.isRequest)
                  or (self.Identifier == DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS and not self.isRequest)):
                self.Length = 16
                block = bytearray(BASE_UUID)
                block[DPKT_POS_SH8] = (self.uuid >> 8) & 0xFF
                block[DPKT_POS_SH0] = self.uuid & 0xFF
                payload.extend(block)
            elif self.Identifier in (DPKT_MSGID_WRITE_CHARACTERISTIC, DPKT_MSGID_UNSOLICITED_CHARACTERISTIC_NOTIFICATION) \
                 or (self.Identifier == DPKT_MSGID_READ_CHARACTERISTIC and not self.isRequest) \
                 or (self.Identifier == DPKT_MSGID_ENABLE_CHARACTERISTIC_NOTIFICATIONS and self.isRequest):
                self.Length = 16 + len(self.additional_data)
                block = bytearray(BASE_UUID)
                block[DPKT_POS_SH8] = (self.uuid >> 8) & 0xFF
                block[DPKT_POS_SH0] = self.uuid & 0xFF
                payload.extend(block)
                payload.extend(self.additional_data)
            else:
                self.Length = 0

        out.append((self.Length >> 8) & 0xFF)
        out.append(self.Length & 0xFF)
        out.extend(payload)
        return bytes(out) 