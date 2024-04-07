import time
import can
from can.interfaces.udp_multicast import UdpMulticastBus

# The bus can be created using the can.Bus wrapper class or using UdpMulticastBus directly
with can.Bus(channel=UdpMulticastBus.DEFAULT_GROUP_IPv4, interface='udp_multicast') as bus_1, \
        UdpMulticastBus(channel=UdpMulticastBus.DEFAULT_GROUP_IPv4) as bus_2:

    # register a callback on the second bus that prints messages to the standard out
    notifier = can.Notifier(bus_2, [can.Printer()])

    # create and send a message with the first bus, which should arrive at the second one
    message = can.Message(arbitration_id=0x123, data=[1, 2, 3])
    bus_1.send(message)

    # give the notifier enough time to get triggered by the second bus
    time.sleep(2.0)
