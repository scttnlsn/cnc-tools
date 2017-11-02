import logging
import re
import serial
import sys
import time

logging_handler = logging.StreamHandler(sys.stdout)
logging_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging_handler)

def connect(device, baud = 115200):
    return serial.Serial(device, baud)

class Coordinates(object):

    @classmethod
    def parse(cls, value):
        x, y, z = value.split(',')
        return cls(float(x), float(y), float(z))

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __eq__(self, other):
        return (self.x == other.x) and (self.y == other.y) and (self.z == other.z)

    def __add__(self, other):
        return self.__class__(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return self.__class__(self.x - other.x, self.y - other.y, self.z - other.z)

    def __repr__(self):
        return '%f,%f,%f' % (self.x, self.y, self.z)

class Response(object):

    error_regex = re.compile('^error:(\d+)')

    @classmethod
    def is_response(cls, value):
        return cls.error_regex.match(value) != None or value == 'ok'

    def __init__(self, value):
        self.value = value

    def is_success(self):
        return self.value == 'ok'

    def is_error(self):
        return self.error_regex.match(self.value) != None

    def error_code(self):
        if self.is_error():
            match = self.error_regex.match(self.value)
            return int(match.group(1))

class Status(object):

    regex = re.compile('\<(\w+)\|(.+)\>')

    @classmethod
    def is_status(cls, value):
        return cls.regex.match(value) != None

    def __init__(self, value):
        self.value = value
        if not self.is_status(value):
            raise Exception('invalid status format')

        match = self.regex.match(self.value)
        self.state = match.group(1)
        self.segments = {}

        for segment in match.group(2).split('|'):
            name, value = segment.split(':')
            self.segments[name] = value

    def is_idle(self):
        return self.state == 'Idle'

    def mpos(self):
        if 'MPos' in self.segments:
            return Coordinates.parse(self.segments['MPos'])

    def wco(self):
        if 'WCO' in self.segments:
            return Coordinates.parse(self.segments['WCO'])

class PendingMessages(Exception):
    pass

class SendError(Exception):
    pass

class Sender(object):

    polling_interval = 0.2

    def __init__(self, serial):
        self.serial = serial
        self.messages = []

        lines = self._read_until(lambda line: re.match(r'^Grbl.*', line))
        if not re.match(r'^Grbl 1\.1.*', lines[-1]):
            raise Exception('Unsupported Grbl version')

        self.mpos = Coordinates(0.0, 0.0, 0.0)
        self.wco = Coordinates(0.0, 0.0, 0.0)

    def receive(self):
        lines = self._read_until(lambda line: Response.is_response(line))
        self.messages = lines[0:-1]
        return Response(lines[-1])

    def read_messages(self):
        messages = self.messages
        self.messages = []
        return messages

    def message(self):
        messages = self.read_messages()
        assert len(messages) == 1
        return messages[0]

    def send_gcode(self, value):
        if len(self.messages) > 0:
            raise PendingMessages()

        logger.info('send: %s' % value)
        self.serial.write('%s\n' % value)

        response = self.receive()
        if response.is_error():
            raise SendError(response.error_code())

        return response

    def status(self):
        self.serial.write('?')
        self.serial.flush()
        lines = self._read_until(lambda line: Status.is_status(line))
        self.messages += lines[0:-1]
        return self._update_status(Status(lines[-1]))

    def wait(self):
        while True:
            if self.status().is_idle():
                break
            time.sleep(self.polling_interval)

    def position(self):
        return self.mpos - self.wco

    def _read_until(self, f):
        lines = []

        while True:
            line = self.serial.readline().strip()
            if len(line) > 0:
                logger.info('recv: %s' % line)
                lines.append(line)
            if f(line):
                break

        return lines

    def _update_status(self, status):
        self.mpos = status.mpos()
        wco = status.wco()
        if wco:
            self.wco = wco
        return status
