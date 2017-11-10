import argparse
import grbl
import logging
import numpy
import re
import sys

class Result:
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

class Probe:

    def __init__(self, sender):
        self.sender = sender

    def __call__(self, min_z, feedrate):
        self.sender.send_gcode('G38.2 Z%s F%s' % (min_z, feedrate))
        result = Result(self.sender.message())
        return result

    def find_z_origin(self, min_z, feedrate):
        # raise z in case we're already touching the surface
        sender.send_gcode('G0 Z1')

        result = self(min_z, feedrate)
        if result.is_success():
            # slowly go back to probe result in case we overshot (decelerating)
            self.sender.send_gcode('G1 Z%f F1' % result.position.z)
            self.sender.wait()

            # zero out work offsets
            self.sender.send_gcode('G92 Z0')
            self.sender.wait()
        else:
            raise Exception('probe failed')

class GridProbe:

    def __init__(self, probe, **kwargs):
        self.probe = probe
        self.sender = self.probe.sender

        self.x_max = float(kwargs['x_max'])
        self.x_step = float(kwargs['x_step'])
        self.y_max = float(kwargs['y_max'])
        self.y_step = float(kwargs['y_step'])

        self.z_min = float(kwargs['z_min'])
        self.feedrate = float(kwargs['feedrate'])

    def points(self):
        points = []
        x_max = self.x_max
        x_num = x_max / self.x_step + 1
        y_max = self.y_max
        y_num = y_max / self.y_step + 1

        y_min = 0

        for x in numpy.linspace(0, x_max, x_num):
            for y in numpy.linspace(y_min, y_max, y_num):
                points.append((x, y))
            y_min, y_max = y_max, y_min

        return points

    def probe_position(self, x, y):
        sender.send_gcode('G0 Z1')
        sender.send_gcode('G0 X%f Y%f' % (x, y))
        return self.probe(self.z_min, self.feedrate)

    def run(self):
        for x, y in self.points():
            result = self.probe_position(x, y)
            position = result.position - sender.wco
            yield position

def parse_args():
    parser = argparse.ArgumentParser(description='Probe Z surface')
    parser.add_argument('-o', metavar='OUTPUT', dest='output', help='path to output file', required=True)
    parser.add_argument('-d', metavar='DEVICE', dest='device', help='serial device', required=True)
    parser.add_argument('--x-max', metavar='X_MAX', dest='x_max', help='max x value', required=True)
    parser.add_argument('--x-step', metavar='X_STEP', dest='x_step', help='x step increment')
    parser.add_argument('--y-max', metavar='Y_MAX', dest='y_max', help='max y value', required=True)
    parser.add_argument('--y-step', metavar='Y_STEP', dest='y_step', help='y step increment')
    parser.add_argument('--z-min', metavar='Z_MIN', dest='z_min', help='minimum z value')
    parser.add_argument('--feedrate', metavar='FEEDRATE', dest='feedrate', help='probe feedrate')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    serial = grbl.connect(args.device)
    sender = grbl.Sender(serial)
    probe = Probe(sender)

    probe.find_z_origin(-10, 50)

    grid = GridProbe(probe,
                     x_max=args.x_max, x_step=args.x_step or 10,
                     y_max=args.y_max, y_step=args.y_step or 10,
                     z_min=args.z_min or -0.5,
                     feedrate=args.feedrate or 50)

    results = []

    print('probing...')
    for point in grid.run():
        print('result: %f,%f,%f' % (point.x, point.y, point.z))
        results.append(point)

    # raise and return to xy origin
    sender.send_gcode('G0 Z1')
    sender.send_gcode('G0 X0 Y0')

    with open(args.output, 'w') as f:
        for coord in results:
            f.write('%s,%s,%s\n' % (coord.x, coord.y, coord.z))
