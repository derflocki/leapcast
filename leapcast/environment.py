from __future__ import unicode_literals
import argparse
import logging
import uuid

logger = logging.getLogger('Environment')


class Environment(object):
    channels = dict()
    global_status = dict()
    friendlyName = 'leapcast'
    user_agent = 'Mozilla/5.0 (CrKey - 0.9.3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1573.2 Safari/537.36'
    chrome = '/usr/bin/chromium-browser'
    vlc = '/usr/bin/cvlc'
    fullscreen = True
    interface = None
    uuid = None
    verbosity = logging.INFO

def parse_cmd():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', action='store_true',
                        default=False, help='Debug')
    parser.add_argument('--name', help='Friendly name for this device')
    parser.add_argument('--user_agent', help='Custom user agent')
    parser.add_argument('--chrome', help='Path to Google Chrome executable')
    parser.add_argument('--vlc', help='Path to VLC executable')
    parser.add_argument('--fullscreen', action='store_true',
                        default=True, help='Start in full-screen mode')
    args = parser.parse_args()

    if args.name:
        Environment.friendlyName = args.name
        logger.debug('Service name is %s' % Environment.friendlyName)

    if args.user_agent:
        Environment.user_agent = args.user_agent
        logger.debug('User agent is %s' % args.user_agent)

    if args.chrome:
        Environment.chrome = args.chrome
        logger.debug('Chrome path is %s' % args.chrome)

    if args.chrome:
        Environment.vlc = args.vlc
        logger.debug('VLC path is %s' % args.chrome)

    if args.fullscreen:
        Environment.fullscreen = True

    if args.d:
        Environment.verbosity = logging.DEBUG

    generate_uuid()


def generate_uuid():
    Environment.uuid = str(uuid.uuid5(
        uuid.NAMESPACE_DNS, ('device.leapcast.%s' % Environment.friendlyName).encode('utf8')))
