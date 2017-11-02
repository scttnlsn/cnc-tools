import argparse
import csv
import numpy as np
import scipy.interpolate as interpolate
import sys
import re

class Line:

    def __init__(self, value):
        self.value = value

    def coordinates(self, current):
        result = current[:]

        for i, axis in enumerate(('x', 'y', 'z')):
            pos = self.axis_position(axis)
            if pos:
                result[i] = pos

        return result

    def axis_position(self, axis):
        match = self._search_axis(axis)
        if match:
            return float(match.group(1))

    def replace(self, axis, value):
        return Line(self._axis_regex(axis).sub('%s%f' % (axis, value), self.value))

    def append(self, value):
        return Line(self.value + value)

    def set_z(self, z):
        if self.axis_position('z') is not None:
            return self.replace('z', z)
        elif self.axis_position('x') is not None or self.axis_position('y') is not None:
            return self.append(' Z%f' % z)
        else:
            return self

    def _search_axis(self, axis):
        return self._axis_regex(axis).search(self.value)

    def _axis_regex(self, axis):
        return re.compile('%s\s*(-?[0-9]+\.[0-9]+)' % axis, re.IGNORECASE)

class Gcode:

    @classmethod
    def parse(cls, value):
        return cls([Line(line) for line in value.split('\n')])

    def __init__(self, lines):
        self.lines = lines

    def __str__(self):
        return '\n'.join([line.value for line in self.lines])

    def positions(self):
        coordinates = [0, 0, 0]
        positions = []

        for i, line in enumerate(self.lines):
            coordinates = line.coordinates(coordinates)
            positions.append((i, coordinates[:]))

        return positions

    def extent(self):
        mins = [0, 0, 0]
        maxes = [0, 0, 0]

        for i, line in enumerate(self.lines):
            coordinates = line.coordinates([None, None, None])
            for i, _ in enumerate(('x', 'y', 'z')):
                if coordinates[i] is not None:
                    mins[i] = min(coordinates[i], mins[i])
                    maxes[i] = max(coordinates[i], maxes[i])

        return mins, maxes

    def adjust_z(self, probed_points):
        probed_xy = probed_points[:, 0:2]
        probed_z = probed_points[:, 2]

        gcode_positions = self.positions()
        gcode_coordinates = np.vstack([item[1] for item in gcode_positions])
        gcode_xy = gcode_coordinates[:, :2]
        gcode_z = gcode_coordinates[:, 2]
        interpolated_z = interpolate.griddata(probed_xy, probed_z, gcode_xy, method='linear') + gcode_z

        lines = self.lines[:]
        for i, z in enumerate(interpolated_z):
            line_number = gcode_positions[i][0]

            if np.isnan(z):
                raise Exception('coordinates out of bounds')

            lines[line_number] = lines[line_number].set_z(z)

        return Gcode(lines)

def open_gcode(path):
    gcode = None
    with open(path) as f:
        gcode = Gcode.parse(f.read())
    return gcode

def adjust(gcode_path, points_path):
    input_gcode = open_gcode(gcode_path)
    probed_points = np.genfromtxt(points_path, delimiter=',', dtype=np.double)
    output_gcode = input_gcode.adjust_z(probed_points)
    print(output_gcode)

def extent(gcode_path):
    gcode = open_gcode(gcode_path)
    mins, maxes = gcode.extent()
    for i, axis in enumerate(('x', 'y', 'z')):
        print('%s: %f - %f' % (axis, mins[i], maxes[i]))

def parse_args():
    parser = argparse.ArgumentParser(description='Process gcode files')
    parser.add_argument('-g', metavar='GCODE', dest='gcode', help='path to input gcode file', required=True)

    subparsers = parser.add_subparsers(title='commands')
    adjust_parser = subparsers.add_parser('adjust', help='adjust gcode z values')
    adjust_parser.set_defaults(which='adjust')
    adjust_parser.add_argument('-p', metavar='POINTS', dest='points', help='path to points file', required=True)

    extent_parser = subparsers.add_parser('extent', help='output gcode extent')
    extent_parser.set_defaults(which='extent')

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    if args.which == 'adjust':
        adjust(args.gcode, args.points)
    elif args.which == 'extent':
        extent(args.gcode)
