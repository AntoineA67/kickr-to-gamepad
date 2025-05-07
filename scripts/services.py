#!/usr/bin/env python3

# Service UUIDs
SERVICES = {
    'fitnessMachine':      '00001826-0000-1000-8000-00805f9b34fb',
    'cyclingPower':        '00001818-0000-1000-8000-00805f9b34fb',
    'heartRate':           '0000180d-0000-1000-8000-00805f9b34fb',
    'speedCadence':        '00001816-0000-1000-8000-00805f9b34fb',
    'battery':             '0000180f-0000-1000-8000-00805f9b34fb',
    'fec':                 '6e40fec1-b5a3-f393-e0a9-e50e24dcca9e',
    'wahooFitnessMachine': 'a026ee0b-0a7d-4ab3-97fa-f1500f9feb8b',
    'raceController':      '00000001-19ca-4651-86e5-fa29dcdd09d1',
    'smo2':                '6404d801-4cb9-11e8-b566-0800200c9a66',
    'coreTemp':            '00002100-5b1e-4347-b07c-97b514dae121',
    'deviceInformation':   '0000180a-0000-1000-8000-00805f9b34fb',
    'linkLoss':            '00001803-0000-1000-8000-00805f9b34fb',
    'txPower':             '00001804-0000-1000-8000-00805f9b34fb',
    'immediateAlert':      '00001802-0000-1000-8000-00805f9b34fb',
    'cyclingSpeedCadence': '00001816-0000-1000-8000-00805f9b34fb',
    'cyclingPower':        '00001818-0000-1000-8000-00805f9b34fb',
    'heartRate':           '0000180d-0000-1000-8000-00805f9b34fb',
    'battery':             '0000180f-0000-1000-8000-00805f9b34fb',
    'fitnessMachine':      '00001826-0000-1000-8000-00805f9b34fb',
    'wahooTrainer':        'a026ee01-0a7d-4ab3-97fa-f1500f9feb8b',
    'wahooTrainerControl': 'a026ee03-0a7d-4ab3-97fa-f1500f9feb8b',
    'wahooTrainerData':    'a026ee06-0a7d-4ab3-97fa-f1500f9feb8b',
}

# Characteristic UUIDs
CHARACTERISTICS = {
    # Fitness Machine
    'indoorBikeData':                '00002ad2-0000-1000-8000-00805f9b34fb',
    'fitnessMachineControlPoint':    '00002ad9-0000-1000-8000-00805f9b34fb',
    'fitnessMachineFeature':         '00002acc-0000-1000-8000-00805f9b34fb',
    'supportedResistanceLevelRange': '00002ad6-0000-1000-8000-00805f9b34fb',
    'supportedPowerRange':           '00002ad8-0000-1000-8000-00805f9b34fb',
    'fitnessMachineStatus':          '00002ada-0000-1000-8000-00805f9b34fb',

    # Cycling Power
    'cyclingPowerMeasurement':       '00002a63-0000-1000-8000-00805f9b34fb',
    'cyclingPowerFeature':           '00002a65-0000-1000-8000-00805f9b34fb',
    'cyclingPowerControlPoint':      '00002a66-0000-1000-8000-00805f9b34fb',
    'wahooTrainer':                  'a026e005-0a7d-4ab3-97fa-f1500f9feb8b',

    # Heart Rate
    'heartRateMeasurement':          '00002a37-0000-1000-8000-00805f9b34fb',

    # Cycling Speed and Cadence
    'speedCadenceMeasurement':       '00002a5b-0000-1000-8000-00805f9b34fb',
    'speedCadenceFeature':           '00002a5c-0000-1000-8000-00805f9b34fb',
    'speedCadenceControlPoint':      '00002a55-0000-1000-8000-00805f9b34fb',

    # Battery
    'batteryLevel':                  '00002a19-0000-1000-8000-00805f9b34fb',
    'batteryLevelStatus':            '00002bed-0000-1000-8000-00805f9b34fb',

    # Device Information
    'manufacturerNameString':        '00002a29-0000-1000-8000-00805f9b34fb',
    'modelNumberString':             '00002a24-0000-1000-8000-00805f9b34fb',
    'firmwareRevisionString':        '00002a26-0000-1000-8000-00805f9b34fb',

    # FEC over BLE
    'fec2':                          '6e40fec2-b5a3-f393-e0a9-e50e24dcca9e',
    'fec3':                          '6e40fec3-b5a3-f393-e0a9-e50e24dcca9e',

    # Wahoo Fitness Machine
    'wahooFitnessMachineControlPoint': 'a026e037-0a7d-4ab3-97fa-f1500f9feb8b',

    # Race Controller (Zwift)
    'raceControllerMeasurement':     '00000002-19ca-4651-86e5-fa29dcdd09d1',
    'raceControllerControlPoint':    '00000003-19ca-4651-86e5-fa29dcdd09d1',
    'raceControllerResponse':        '00000004-19ca-4651-86e5-fa29dcdd09d1',

    # SmO2 Moxy
    'smo2SensorData':                '6404d804-4cb9-11e8-b566-0800200c9a66',
    'smo2DeviceControl':             '6404d810-4cb9-11e8-b566-0800200c9a66',
    'smo2ControlPoint':              '6404d811-4cd9-11e8-b566-0800200c9a66',

    # CoreTemp
    'coreBodyTemp':                  '00002101-5b1e-4347-b07c-97b514dae121',
    'corePrivate':                   '00004200-f366-40b2-ac37-70cce0aa83b1',

    # Others
    'sensorLocation':                    '00002a5d-0000-1000-8000-00805f9b34fb',
    'clientCharacteristicConfiguration': '00002902-0000-1000-8000-00805f9b34fb',
}

# Combine services and characteristics into one dictionary
UUIDS = {**SERVICES, **CHARACTERISTICS}

# Service to Characteristic UUID mapping
def generate_service_char_map():
    """Generate a mapping of services to their characteristics based on UUID patterns"""
    service_char_map = {}
    
    # Extract the base UUID pattern (last 8 bytes)
    base_uuid = '0000-1000-8000-00805f9b34fb'
    
    for service_name, service_uuid in SERVICES.items():
        # Get the service UUID prefix (first 8 bytes)
        service_prefix = service_uuid.split('-')[0]
        
        # Find all characteristics that belong to this service
        service_chars = {}
        for char_name, char_uuid in CHARACTERISTICS.items():
            # Check if the characteristic UUID starts with the service prefix
            if char_uuid.startswith(service_prefix):
                # Extract the characteristic UUID (first 4 bytes after 0000)
                char_uuid_short = char_uuid.split('-')[0]
                service_chars[char_name] = f"0x{char_uuid_short[4:].upper()}"
        
        if service_chars:
            service_char_map[service_name] = service_chars
    
    return service_char_map

SERVICE_CHAR_MAP = generate_service_char_map()

def get_uuid_name(uuid):
    """Convert a UUID to its human-readable name"""
    for name, value in UUIDS.items():
        if value.lower() == uuid.lower():
            return name
    return None

def get_uuid_value(name):
    """Get the UUID value for a given name"""
    return UUIDS.get(name)

def get_service_name(uuid):
    """Get the service name for a given UUID"""
    for name, value in SERVICES.items():
        if value.lower() == uuid.lower():
            return name
    return None

def get_characteristic_name(uuid):
    """Get the characteristic name for a given UUID"""
    for name, value in CHARACTERISTICS.items():
        if value.lower() == uuid.lower():
            return name
    return None

def parse_service_uuids(data):
    """Parse a raw data packet containing service UUIDs and return a list of (uuid, name, characteristics) tuples"""
    services = []
    # Each service UUID is 16 bytes
    for i in range(0, len(data), 16):
        if i + 16 > len(data):
            break
        uuid_bytes = data[i:i+16]
        # Convert bytes to UUID string format
        uuid = uuid_bytes.hex()
        # Format as standard UUID string
        uuid = f"{uuid[0:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:32]}"
        name = get_service_name(uuid)
        
        # Get the corresponding characteristics for this service
        characteristics = SERVICE_CHAR_MAP.get(name, {})
            
        services.append((uuid, name, characteristics))
    return services

def parse_discovered_characteristics(data):
    """Parse a raw data packet containing discovered characteristics and return a list of (uuid, name, properties) tuples"""
    characteristics = []
    # Skip the header (6 bytes) and parse each characteristic
    # Each characteristic entry is 21 bytes:
    # - 2 bytes: handle
    # - 1 byte: properties
    # - 2 bytes: value handle
    # - 16 bytes: UUID
    entry_size = 21
    for i in range(6, len(data), entry_size):
        if i + entry_size > len(data):
            break
            
        # Extract the characteristic data
        entry = data[i:i+entry_size]
        if len(entry) < entry_size:
            break
            
        # Extract the UUID (last 16 bytes)
        uuid_bytes = entry[5:21]
        uuid = uuid_bytes.hex()
        # Format as standard UUID string
        uuid = f"{uuid[0:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:32]}"
        
        # Get the characteristic name
        name = get_characteristic_name(uuid)
        
        # Get the properties (1 byte)
        properties = entry[2]
        
        # Get the value handle (2 bytes)
        value_handle = int.from_bytes(entry[3:5], byteorder='little')
        
        characteristics.append((uuid, name, properties, value_handle))
    
    return characteristics

def get_property_names(properties):
    """Convert property flags to human-readable names"""
    property_names = []
    if properties & 0x01:  # READ
        property_names.append("READ")
    if properties & 0x02:  # WRITE
        property_names.append("WRITE")
    if properties & 0x04:  # NOTIFY
        property_names.append("NOTIFY")
    if properties & 0x08:  # INDICATE
        property_names.append("INDICATE")
    if properties & 0x10:  # WRITE_NO_RESPONSE
        property_names.append("WRITE_NO_RESPONSE")
    if properties & 0x20:  # BROADCAST
        property_names.append("BROADCAST")
    if properties & 0x40:  # AUTHENTICATED_SIGNED_WRITES
        property_names.append("AUTHENTICATED_SIGNED_WRITES")
    if properties & 0x80:  # EXTENDED_PROPERTIES
        property_names.append("EXTENDED_PROPERTIES")
    return property_names

