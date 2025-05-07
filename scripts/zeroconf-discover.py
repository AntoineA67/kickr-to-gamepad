from zeroconf import ServiceBrowser, Zeroconf


class KickrListener:
    def __init__(self):
        self.found = []

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        ip = socket.inet_ntoa(info.addresses[0])
        self.found.append(ip)


zeroconf = Zeroconf()
listener = KickrListener()
ServiceBrowser(zeroconf, "_wahoo-fitness-tnp._tcp.local.", listener)
await asyncio.sleep(2)  # give it a moment to discover
DEVICE_IPS = listener.found
zeroconf.close()
