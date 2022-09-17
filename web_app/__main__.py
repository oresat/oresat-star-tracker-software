import os
import sys

from loguru import logger
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application
from tornado.options import options, define, parse_command_line

from .stream_handler import StreamHandler

LOG_FORMAT = '<green>{time}</green> | {level} | <level>{message}</level>'

DEBUG = os.getenv('DEBUG', 'false')
PORT = os.getenv('PORT', '8888')

define('debug', default=DEBUG.lower() == 'true', help='run in debug mode')
define('port', default=int(PORT), help='webs app port')


class MainHandler(RequestHandler):
    '''Handler for allow users to login'''

    def get(self):
        self.render('templates/stream.html')

    def post(self):
        self.render('templates/stream.html')


HANDLERS = [
    (r'/', MainHandler),
    (r'/websocket', StreamHandler),
]

if __name__ == '__main__':
    parse_command_line()

    logger.remove()  # remove default logger
    if options.debug:
        logger.add(sys.stdout, format=LOG_FORMAT, level='DEBUG')
    else:
        logger.add(sys.stdout, format=LOG_FORMAT, level='INFO')

    app = Application(
        HANDLERS,
        debug=options.debug
    )

    app.listen(options.port)

    try:
        IOLoop.instance().start()
    except KeyboardInterrupt:
        sys.exit()
