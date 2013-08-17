from __future__ import unicode_literals

import base64
from leapcast.environment import Environment
from leapcast.services.websocket import App
from leapcast.utils import render
import tornado.web

from tornadows import soaphandler, webservices
from tornadows import xmltypes, complextypes
from tornadows.soaphandler import webservice
from xml.sax.saxutils import escape

import datetime, time

##For the debugService
import inspect
import logging
logger = logging.getLogger('Leapcast')

import xml.dom.minidom
from tornadows import soap
###

class UpnpServiceDebug(soaphandler.SoapHandler):
    def _getElementFromMessage(self,name,document):
        """ Private method to search and return elements from XML """
        list_of_elements = []
        for e in document.documentElement.childNodes:
            if e.nodeType == e.ELEMENT_NODE and e.nodeName.count(name) >= 1:
                list_of_elements.append(e)
        return list_of_elements
    def _parseSoap(self,xmldoc):
        """ Private method parse a message soap from a xmldoc like string
            _parseSoap() return a soap.SoapMessage().
        """
        xmldoc = xmldoc.replace('\n',' ').replace('\t',' ').replace('\r',' ')
        document = xml.dom.minidom.parseString(xmldoc)
        prefix = document.documentElement.prefix
        namespace = document.documentElement.namespaceURI

        header = self._getElementFromMessage('Header',document)
        body   = self._getElementFromMessage('Body',document)

        header_elements = self._parseXML(header)
        print "parese body"
        body_elements = self._parseXML(body)
        soapMsg = soap.SoapMessage()
        for h in header_elements:
            soapMsg.setHeader(h)
        for b in body_elements:
            soapMsg.setBody(b)
        return soapMsg
    def post(self):
        """ Method post() to process of requests and responses SOAP messages """
        self._request = self._parseSoap(self.request.body)
        
        
        
        soapaction = self.request.headers['SOAPAction'].replace('"','')
        self.set_header('Content-Type','text/xml')
        for operations in dir(self):
            operation = getattr(self,operations)
            method = ''
            if callable(operation) and hasattr(operation,'_is_operation'):
                num_methods = self._countOperations()
                if hasattr(operation,'_operation') and soapaction.endswith(getattr(operation,'_operation')) and num_methods > 1:
                    method = getattr(operation,'_operation') 
                    self._response = self._executeOperation(operation,method=method)
                    break
                elif num_methods == 1:
                    self._response = self._executeOperation(operation,method='')
                    break

        soapmsg = self._response.getSoap().toxml()
        self.write(soapmsg)
    def _executeOperation(self,operation,method=''):
        """ Private method that executes operations of web service """
        params = []
        response = None
        res = None
        typesinput = getattr(operation,'_input')
        args  = getattr(operation,'_args')

        if inspect.isclass(typesinput) and issubclass(typesinput,complextypes.ComplexType):
            obj = self._parseComplexType(typesinput,self._request.getBody()[0],method=method)
            response = operation(obj)
        elif hasattr(operation,'_inputArray') and getattr(operation,'_inputArray'):
            params = self._parseParams(self._request.getBody()[0],typesinput,args)
            response = operation(params)
        else:
            print "getBody()[0]",self._request.getBody()[0]
            params = self._parseParams(self._request.getBody()[0],typesinput,args)
            print "params",params
            response = operation(*params)
        is_array = None
        if hasattr(operation,'_outputArray') and getattr(operation,'_outputArray'):
            is_array = getattr(operation,'_outputArray')

        typesoutput = getattr(operation,'_output')
        if inspect.isclass(typesoutput) and issubclass(typesoutput,complextypes.ComplexType):
            res = self._createReturnsComplexType(response)
        else:
            res = self._createReturns(response,is_array)

        return res
    def _parseXML(self,elements):
        """ Private method parse and digest the xml.dom.minidom.Element 
            finding the childs of Header and Body from soap message. 
            Return a list object with all of child Elements.
        """
        elem_list = []
        
        if len(elements) <= 0:
            return elem_list
        if elements[0].childNodes.length <= 0:
            return elem_list
        for element in elements[0].childNodes:
            if element.nodeType == element.ELEMENT_NODE:
                return [element]
                prefix = element.prefix
                namespace = element.namespaceURI
                if prefix != None and namespace != None:
                    element.setAttribute('xmlns:'+prefix,namespace)
                else:
                    element.setAttribute('xmlns:xsd',"http://www.w3.org/2001/XMLSchema")
                    element.setAttribute('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance")
                print "element", element.toxml()
                elem_list.append(xml.dom.minidom.parseString(element.toxml()))
        return elem_list
    def _parseParams(self,elements,types=None,args=None):
        """ Private method to parse a Body element of SOAP Envelope and extract
            the values of the request document like parameters for the soapmethod,
            this method return a list values of parameters.
         """
        values   = []
        for tagname in args:
            print "tagname", tagname
            type = types[tagname]
            values += self._findValues(tagname,type,elements)
        return values
    def _findValues(self,name,type,xml):
        """ Private method to find the values of elements in the XML of input """
        print "xml", xml.toxml()
        print "name", name
        elems = xml.getElementsByTagName(name)
        values = []
        print "elems", elems
        for e in elems:
            print "e", e
            if e.hasChildNodes and len(e.childNodes) > 0:
                v = None
                if inspect.isclass(type) and (issubclass(type,xmltypes.PrimitiveType) or isinstance(type,xmltypes.Array)):
                    v = type.genType(e.childNodes[0].nodeValue)
                elif hasattr(type,'__name__') and (not issubclass(type,xmltypes.PrimitiveType) or not isinstance(type,xmltypes.Array)):
                    v = complextypes.convert(type.__name__,e.childNodes[0].nodeValue)
                values.append(v)
            else:
                values.append(None)
        return values

class UpnpType(complextypes.ComplexType):
    def __str__(self):
        s=[]
        members = [attr for attr in dir(self) if not callable(attr) and not attr.startswith("__")]
        for m in members:
            s.append("%s: %s" % (m, getattr(self, m)))
        return ", ".join(s)
class SetAVTransportURIResponse(complextypes.ComplexType):
    pass

class GetTransportInfoResponse(UpnpType):
    CurrentTransportState = str
    CurrentTransportStatus = str
    CurrentSpeed = str
    
    def __init__(self):
        self.CurrentSpeed = 1
        self.CurrentTransportState = "NO_MEDIA_PRESENT"
        self.CurrentTransportStatus = "OK"
    @staticmethod
    def getFromVLCStatus(vlc_status):
        response = GetTransportInfoResponse()
        if "( state stopped )" in vlc_status:
            response.CurrentTransportState = "STOPPED"
        elif "( state playing )" in vlc_status:
            response.CurrentTransportState = "PLAYING"
        elif "( state paused )" in vlc_status:
            response.CurrentTransportState = "PAUSED_PLAYBACK"
        return response
class PositionInfoResponse(UpnpType):
    Track = int
    TrackDuration = str
    TrackMetaData = str
    TrackURI = str
    RelTime = str
    AbsTime = str
    RelCount = int
    AbsCount = int
    
    def __init__(self):
        self.Track = 0
        self.TrackDuration = "00:00:00"
        self.TrackMetaData = ""
        self.TrackURI = ""
        self.RelCount = "00:00:00"
        self.AbsTime = "00:00:00"
        self.AbsCount = 2147483647
        self.RelCount = 2147483647
        self.RelTime = "00:00:00"


class StopResponse(complextypes.ComplexType):
    pass

class PlayResponse(complextypes.ComplexType):
    pass

class PauseResponse(complextypes.ComplexType):
    pass

class SeekResponse(complextypes.ComplexType):
    ok=int
    pass

class UpnpService(soaphandler.SoapHandler):
    def _parseXML(self,elements):
        """ Private method parse and digest the xml.dom.minidom.Element 
            finding the childs of Header and Body from soap message. 
            Return a list object with all of child Elements.
        """
        elem_list = []
        
        if len(elements) <= 0:
            return elem_list
        if elements[0].childNodes.length <= 0:
            return elem_list
        for element in elements[0].childNodes:
            if element.nodeType == element.ELEMENT_NODE:
                return [element]
                prefix = element.prefix
                namespace = element.namespaceURI
                if prefix != None and namespace != None:
                    element.setAttribute('xmlns:'+prefix,namespace)
                else:
                    element.setAttribute('xmlns:xsd',"http://www.w3.org/2001/XMLSchema")
                    element.setAttribute('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance")
                print "element", element.toxml()
                elem_list.append(xml.dom.minidom.parseString(element.toxml()))
        return elem_list

from vlcclient import VLCClient
vlc = VLCClient('127.0.0.1')
vlc.connect()

class UpnpStatus:
    CurrentURI=""
    CurrentURIMetadata=""

status = UpnpStatus()
class AvTransportService(UpnpService):

    @webservice(_params=[int,str,str], _returns=SetAVTransportURIResponse)
    def SetAVTransportURI(self,InstanceID,CurrentURI, CurrentURIMetaData):
        status.CurrentURI = CurrentURI
        status.CurrentURIMetadata = CurrentURIMetaData
        logger.debug("SetAVTransportURI: %s" % CurrentURI)
        vlc.clear()
        vlc.enqueue(CurrentURI)
        time.sleep(.5)
        return SetAVTransportURIResponse()
    
    @webservice(_params=[int],_returns=GetTransportInfoResponse)
    def GetTransportInfo(self, InstanceID=0):
        logger.debug("GetTransportInfo: %s" % InstanceID)
        response = GetTransportInfoResponse.getFromVLCStatus(vlc.status())
        return response
    
    @webservice(_params=[int], _returns=PositionInfoResponse)
    def GetPositionInfo(self, InstanceID=0):
        logger.debug("GetPositionInfo: %s" % InstanceID)
        
        pi = PositionInfoResponse()
        pi.TrackURI = status.CurrentURI
        pi.TrackMetaData = escape(status.CurrentURIMetadata)
        if vlc.is_playing():
            pi.TrackDuration = str(datetime.timedelta(seconds=vlc.get_length()))
            pi.AbsTime = str(datetime.timedelta(seconds=vlc.get_time()))
            pi.RelTime = str(datetime.timedelta(seconds=vlc.get_time()))
        return pi
    
    @webservice(_params=[int], _returns=StopResponse)
    def Stop(self, InstanceID=0):
        logger.debug("Stop: %s" % InstanceID)
        vlc.stop()
        return StopResponse()
    
    @webservice(_params=[int, int], _returns=PlayResponse)
    def Play(self, InstanceID, Speed):
        logger.debug("Play: %s, %s" % (InstanceID, Speed))
        vlc.play()
        return PlayResponse()
    
    @webservice(_params=[int], _returns=PauseResponse)
    def Pause(self, InstanceID=0):
        logger.debug("Pause: %s" % InstanceID)
        vlc.pause()
        return PauseResponse()
    
    @webservice(_params=[int,str,str], _returns=SeekResponse)
    def Seek(self,InstanceID, Unit, Target):
        logger.debug("Seek: %s, %s, %s" % (InstanceID, Unit, Target))
        if Unit == "REL_TIME" or Unit == "ABS_TIME":
            time = sum(int(i) * 60**index for index, i in enumerate(Target.split(":")[::-1]))
            vlc.seek(time)
            pass
        return SeekResponse()



    def GetMediaInfo (self,):
        pass
    def GetDeviceCapabilities (self):
        pass
    def GetTransportSettings (self):
        pass


class ConnectionManagerService(UpnpService):
    pass
class EventHandler(tornado.web.RequestHandler):
    pass
class SSDPHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/xml")
        if self.request.uri == "/mr/avt/scpd":
            self.render("data/mr/avt/scpd.xml")
        elif self.request.uri == "/mr/cm/scpd":
            self.render("data/mr/cm/scpd.xml")
        elif self.request.uri == "/mr/rc/scpd":
            self.render("data/mr/rc/scpd.xml")
        
class MediaRenderer(tornado.web.RequestHandler):
    '''
    Holds info about device
    '''
    icon = '''iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAMAAABg3Am1AAABR1BMVEUAAABBgPNBgPNCgPNBgPNBgfNCgfRBgPNBgfNBgfNCgfRCgfRCgfRBgPNCgfRCgfRBgPRBgfRCgfRCgfNCgfRBgPNCgfRCgfRBgfNCgPNCgfRCgPRCgfRCgfRCgfRCgPRCgfRCgfRCgfRCgfRCgPRCgfNCgfRCgfRBgPNBgfNBgPNBgfNCgfRCgfRCgPRBgPNCgfRCgfRBgPNCgfRCgPRCgfRCgPRCgfRCgPRCgPRCgfRBgfNCgfRCgfRCgPRCgfRCgPNCgfRBgfRBgPNBgfNBgPRCgfRCgfNCgfNCgfNCgfRCgfRCgfRCgfRCgfRCgfRCgfRCgfRBgfRCgfRBgPNCgfNCgfRCgfRCgfRCgPRBgPRCgfRBgfNCgfRBgPNBgfNCgPNCgfNBgfNCgfNCgfRBgPNBgPRBgfNBgfRCgPNCgPRCgfNCgfTceuSvAAAAZXRSTlMAAQICAwMDBAUICAkKEhIUFRUVFhYYGx0fJCUsLDQ5PDw9P0FERktSYGFjbm9ydHV6fIOGh4eKiouMjJGTlpyjqKmqrLS1t7zAwsPM2dvc4OHi5ebn6Ort8PH1+fr6+/v9/f7+/pj2+4gAAAEkSURBVHja7dRHT8NQEIXRC4QeWui9E3rHoYbeCb2bnnHsvHf//5otDshlByjf/kgz0miQ709XsJzw7ysoceifC9jhgdzeeHSn3KDYolkNj7psN4jYNGNeoEfnjBQWRCxf8OtHKtx9ZYMvcNdfERIAIcDpwXxLKEBN53gwDKCmOJexwGBkj1rIj7ngSxdNpiii1gOCaCmABWrhYTDwcrEKoF1TOBtwaT6PArEHitMbBLxThEmgKSOSCgLatpQIt4Fxpjn1E+h0A6D7Sshp4NyW6wgqT3I7c1ygFah51GLWoiNDqxk4srzfjOwDjU9ir6H8XlQSGKA3SGc3gQ0qlmFHqzcAE2Pfcx2fiqOK5BDiWVr18MswEsPAjLHYh+iKsVSHfP+uTzaPpBkw+zEOAAAAAElFTkSuQmCC'''
    device_min_broken = '''<?xml version="1.0" encoding="UTF-8"?>
    <root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:dlna="urn:schemas-dlna-org:device-1-0">
        <specVersion>
            <major>1</major>
            <minor>0</minor>
        </specVersion>
        <device>
            <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
            <friendlyName>$friendlyName</friendlyName>
            <manufacturer>leapcast</manufacturer>
            <modelName>Eureka Dongle</modelName>
            <UDN>uuid:$uuid-mr</UDN>
            <iconList>
                <icon>
                    <mimetype>image/png</mimetype>
                    <width>48</width>
                    <height>48</height>
                    <depth>24</depth>
                    <url>/mr/icon-48.png</url>
                </icon>
            </iconList>
            <serviceList>
                <service>
                    <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
                    <serviceId>urn:upnp-org:serviceId:AVTransport</serviceId>
                    <controlURL>/mr/avt/control</controlURL>
                    <eventSubURL>/mr/avt/event</eventSubURL>
                    <SCPDURL>/mr/avt/scpd</SCPDURL>
                </service>
            </serviceList>
            <presentationURL>$path</presentationURL>
        </device>
    </root>'''
    device = '''<?xml version="1.0" encoding="UTF-8"?>
    <root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:dlna="urn:schemas-dlna-org:device-1-0">
        <specVersion>
            <major>1</major>
            <minor>0</minor>
        </specVersion>
        <device>
            <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
            <friendlyName>$friendlyName</friendlyName>
            <manufacturer>leapcast</manufacturer>
            <modelName>Eureka Dongle</modelName>
            <UDN>uuid:$uuid</UDN>
            <iconList>
                <icon>
                    <mimetype>image/png</mimetype>
                    <width>48</width>
                    <height>48</height>
                    <depth>24</depth>
                    <url>/mr/icon-48.png</url>
                </icon>
            </iconList>
            <serviceList>
                <service>
                    <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
                    <serviceId>urn:upnp-org:serviceId:AVTransport</serviceId>
                    <controlURL>/mr/avt/control</controlURL>
                    <eventSubURL>/mr/avt/event</eventSubURL>
                    <SCPDURL>/mr/avt/scpd</SCPDURL>
                </service>
                <service>
                    <serviceType>urn:schemas-upnp-org:service:ConnectionManager:1</serviceType>
                    <serviceId>urn:upnp-org:serviceId:ConnectionManager</serviceId>
                    <SCPDURL>/mr/cm/scpd</SCPDURL>
                    <controlURL>/mr/cm/control</controlURL>
                    <eventSubURL>/mr/cm/event</eventSubURL>
                </service>
                <service>
                    <serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType>
                    <serviceId>urn:upnp-org:serviceId:RenderingControl</serviceId>
                    <SCPDURL>/mr/rc/scpd</SCPDURL>
                    <controlURL>/mr/rc/control</controlURL>
                    <eventSubURL>/mr/rc/event</eventSubURL>
                </service>
            </serviceList>
            <presentationURL>$path</presentationURL>
        </device>
    </root>'''

    def get(self):
        if self.request.uri == "/mr/icon-48.png":
            self.set_header("Content-Type", "image/png")
            self.write(base64.b64decode(self.icon))
        else:
            self.set_header("Content-Type", 'text/xml; charset="utf-8"')
            self.write(render(self.device).substitute(
                dict(
                    friendlyName=Environment.friendlyName,
                    uuid=Environment.uuid,
                    path="http://%s" % self.request.host)
                )
            )


# class ChannelFactory(tornado.web.RequestHandler):
# 
#     '''
#     Creates Websocket Channel. This is requested by 2nd screen application
#     '''
#     @tornado.web.asynchronous
#     def post(self, app=None):
#         self.app = App.get_instance(app)
#         self.set_header(
#             "Access-Control-Allow-Method", "POST, OPTIONS")
#         self.set_header("Access-Control-Allow-Headers", "Content-Type")
#         self.set_header("Content-Type", "application/json")
#         ## TODO: Use information from REGISTER packet
#         ## TODO: return url based on channel property
#         ## TODO: defer request until receiver connects
#         self.finish(
#             '{"URL":"ws://%s/session/%s?%s","pingInterval":3}' % (
#             self.request.host, app, self.app.get_apps_count())
#         )
