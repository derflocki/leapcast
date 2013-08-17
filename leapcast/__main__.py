#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import unicode_literals
import threading
import signal
import logging
import sys
import os
from os import environ
import time

from twisted.internet import reactor
import tornado.ioloop
from  tornado import web
import tornado.websocket
from leapcast.environment import parse_cmd
from leapcast.apps.default import *
from leapcast.services.rest import *
from leapcast.services.ssdp import StartLeapUPNPServer
from leapcast.services.websocket import *
from leapcast.services.upnp import MediaRenderer, SSDPHandler, AvTransportService, EventHandler

logger = logging.getLogger('Leapcast')

class HTTPThread(object):
    def run(self):
        self.application = web.Application([
            (r"/ssdp/device-desc.xml", DeviceHandler),
            (r"/apps", DeviceHandler),
            
            (r"/mr/ssdp.xml", MediaRenderer),
            (r"/mr/icon-48.png", MediaRenderer),
            
            (r"/mr/avt/control", AvTransportService),
            (r"/mr/avt/event", EventHandler),
            (r"/mr/avt/scpd", SSDPHandler),
            
            (r"/mr/cm/scpd", SSDPHandler),
            (r"/mr/rc/scpd", SSDPHandler),

            self.register_app(ChromeCast),
            self.register_app(YouTube),
            self.register_app(PlayMovies),
            self.register_app(GoogleMusic),
            self.register_app(GoogleCastSampleApp),
            self.register_app(GoogleCastPlayer),
            self.register_app(TicTacToe),
            self.register_app(Fling),

            (r"/connection", ServiceChannel),
            (r"/connection/([^\/]+)", ChannelFactory),
            (r"/receiver/([^\/]+)", ReceiverChannel),
            (r"/session/([^\/]+)", ApplicationChannel),
            (r"/system/control", CastPlatform),
        ], debug=True)
        self.application.listen(8008)
        tornado.ioloop.IOLoop.instance().start()

    def start(self):
        threading.Thread(target=self.run).start()

    def shutdown(self, ):
        logger.info('Stopping HTTP server')
        reactor.callFromThread(reactor.stop)
        logger.info('Stopping DIAL server')
        tornado.ioloop.IOLoop.instance().stop()

    def register_app(self, app):
        name = app.__name__
        logger.debug('Added %s app' % name)
        return (r"(/apps/" + name + "|/apps/" + name + ".*)", app)

    def sig_handler(self, sig, frame):
        tornado.ioloop.IOLoop.instance().add_callback(self.shutdown)


def main():
    parse_cmd()
    logging.basicConfig(level=Environment.verbosity)

    if sys.platform == 'darwin' and environ.get('TMUX') is not None:
        logger.error('Running Chrome inside tmux on OS X might cause problems.'
                     ' Please start leapcast outside tmux.')
        sys.exit(1)

    server = HTTPThread()
    server.start()
    signal.signal(signal.SIGTERM, server.sig_handler)
    signal.signal(signal.SIGINT, server.sig_handler)
    
    reactor.callWhenRunning(StartLeapUPNPServer)
    reactor.run()


if __name__ == "__main__":
    main()
