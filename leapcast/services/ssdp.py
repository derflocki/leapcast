# -*- coding: utf8 -*-

from __future__ import unicode_literals
import datetime
import socket
from twisted.internet import reactor, task
from twisted.internet.protocol import DatagramProtocol
from leapcast.utils import render
from leapcast.environment import Environment


class SSDP(DatagramProtocol):
    SSDP_ADDR = '239.255.255.250'
    SSDP_PORT = 1900
    SSDP_IP_PORT = '239.255.255.250:1900'
    header = '''\
    HTTP/1.1 200 OK\r
    LOCATION: http://$ip:8008/ssdp/device-desc.xml\r
    CACHE-CONTROL: max-age=1800\r
    CONFIGID.UPNP.ORG: 7337\r
    BOOTID.UPNP.ORG: 7337\r
    USN: uuid:$uuid\r
    ST: urn:dial-multiscreen-org:service:dial:1\r
    \r
    '''
    upnp_header_msearch = '''\
    HTTP/1.1 200 OK\r
    LOCATION: http://$ip:8008/mr/ssdp.xml\r
    CACHE-CONTROL: max-age=1800\r
    Server: UPnP/1.1 leapcast
    EXT: \r
    DATE: $date\r
    USN: uuid:$uuid::$st\r
    ST: $st\r
    \r
    '''
    
    upnp_header_notify = '''\
    NOTIFY * HTTP/1.1\r
    HOST: $ssdp_ipport
    LOCATION: http://$ip:8008/mr/ssdp.xml\r
    NTS: $nts\r
    CACHE-CONTROL: max-age=1800\r
    Server: UPnP/1.1 leapcast
    USN: $usn\r
    NT: $nt\r
    \r
    '''
    
    def __init__(self):
        self.notify_ip = "127.0.0.1"
        self.transport = reactor.listenMulticast(
            self.SSDP_PORT, self, listenMultiple=True)
        self.transport.setLoopbackMode(1)
        self.transport.joinGroup(self.SSDP_ADDR,)

    def stop(self):
        nts = "ssdp:byebye"
        for nt in ["upnp:rootdevice", "uuid:%s"%Environment.uuid, "urn:schemas-upnp-org:device:MediaRenderer:1", "urn:schemas-upnp-org:service:AVTransport:1", "urn:schemas-upnp-org:service:ConnectionManager:1", "urn:schemas-upnp-org:service:RenderingControl:1"]:
            usn = "uuid:%s::%s" %(Environment.uuid, nt)
            data = render(self.upnp_header_notify).substitute(
                ip=self.notify_ip,
                uuid=Environment.uuid,
                nt=nt,
                nts=nts,
                usn=usn,
                ssdp_ipport=self.SSDP_IP_PORT
            )
            #print data
            self.transport.write(data, (self.SSDP_ADDR, self.SSDP_PORT))
            
        self.transport.leaveGroup(self.SSDP_ADDR)
        self.transport.stopListening()
    def notify(self):
        nts = "ssdp:alive"
        for nt in ["upnp:rootdevice", "uuid:%s"%Environment.uuid, "urn:schemas-upnp-org:device:MediaRenderer:1", "urn:schemas-upnp-org:service:AVTransport:1", "urn:schemas-upnp-org:service:ConnectionManager:1", "urn:schemas-upnp-org:service:RenderingControl:1"]:
            if nt[:4] == "uuid":
                usn = nt
            else:
                usn = "uuid:%s::%s" %(Environment.uuid, nt)
            data = render(self.upnp_header_notify).substitute(
                ip=self.notify_ip,
                uuid=Environment.uuid,
                nt=nt,
                nts=nts,
                usn=usn,
                ssdp_ipport=self.SSDP_IP_PORT
            )
            #print data
            self.transport.write(data, (self.SSDP_ADDR, self.SSDP_PORT))

    def startProtocol(self):
        #self.lc = task.LoopingCall(self.notify)
        #self.lc.start(15)
    
    def get_remote_ip(self, address):
        # Create a socket to determine what address the client should
        # use
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(address)
        iface = s.getsockname()[0]
        s.close()
        return unicode(iface)

    def datagramReceived(self, datagram, address):
        if not "M-SEARCH * HTTP/1.1" in datagram:
            return
        if "urn:dial-multiscreen-org:service:dial:1" in datagram:
            pass
            data = render(self.header).substitute(
                ip=self.get_remote_ip(address),
                uuid=Environment.uuid
            )
            self.transport.write(data, address)
        else: 
            #print datagram
            st = ""
            if ("ssdp:all" in datagram or "urn:schemas-upnp-org:device:MediaRenderer:1" in datagram):
                st = "urn:schemas-upnp-org:device:MediaRenderer:1"
            elif ("upnp:rootdevice" in datagram):
                st = "upnp:rootdevice"
            elif ("urn:schemas-upnp-org:service:AVTransport:1" in datagram):
                st = "urn:schemas-upnp-org:service:AVTransport:1"
            data = render(self.upnp_header_msearch).substitute(
                ip=self.get_remote_ip(address),
                date=datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S %Z'),
                uuid=Environment.uuid,
                st=st
            )
            #print data
            self.transport.write(data, address)


def StartLeapUPNPServer():
    sobj = SSDP()
    reactor.addSystemEventTrigger('before', 'shutdown', sobj.stop)
