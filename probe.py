import grbl
import logging
import numpy
import re
import sys

class Result(object):
    regex = re.compile('\[PRB:(.*)\]')

    def __init__(self, value):
        self.value = value

        if not self.regex.match(value):
            raise Exception('invalid format')

        match = self.regex.match(self.value)
        coords, self.code = match.group(1).split(':')
        self.position = grbl.Coordinates.parse(coords)

    def is_success(self):
        return self.code == '1'

class Probe(object):

    def __init__(self, sender):
        self.sender = sender

    def probe(self, min_z, feedrate):
        self.sender.send_gcode('G38.2 Z%s F%s' % (min_z, feedrate))
        result = Result(self.sender.message())
        return result

    def find_z_origin(self, min_z, feedrate):
        result = self.probe(min_z, feedrate)

        if result.is_success():
            # slowly go back to probe result in case we overshot (decelerating)
            self.sender.send_gcode('G1 Z%s F1' % result.position.z)

            # zero out work offsets
            self.sender.send_gcode('G92 Z0')
        else:
            raise Exception('probe failed')

def grid_points(x_max, x_step, y_max, y_step):
    points = []
    x_num = x_max / x_step + 1
    y_num = y_max / y_step + 1

    y_min = 0

    for x in numpy.linspace(0, x_max, x_num):
        for y in numpy.linspace(y_min, y_max, y_num):
            points.append((x, y))
        y_min, y_max = y_max, y_min

    return points

if __name__ == '__main__':
    serial = grbl.connect(sys.argv[1])
    sender = grbl.Sender(serial)
    probe = Probe(sender)

    # raise z in case we're already touching surface
    sender.send_gcode('G0 Z1')

    probe.find_z_origin(-10, 50)

    sender.wait
    print('position: %s' % sender.position())

    points = []

    for x, y in grid_points(50, 10, 50, 10):
        print('probing: %f,%f...' % (x, y))

        sender.send_gcode('G0 Z1')
        sender.send_gcode('G0 X%f Y%f' % (x, y))

        result = probe.probe(-0.5, 50)
        position = result.position - sender.wco
        points.append(position)

        print('position: %s' % position)

    # return to origin
    sender.send_gcode('G0 Z1')
    sender.send_gcode('G0 X0 Y0')

    with open('z_offsets.csv') as f:
        for coord in points:
            f.write('%s,%s,%s' % (coord.x, coord.y, coord.z))
