# cnc-tools

CNC tools for working with Gcode and Grbl

### grbl.py

Minimal wrapper for communicating with Grbl board via serial device.

### probe.py

```
usage: probe.py [-h] -o OUTPUT -d DEVICE --x-max X_MAX [--x-step X_STEP]
                --y-max Y_MAX [--y-step Y_STEP] [--z-min Z_MIN]
                [--feedrate FEEDRATE]

Probe Z surface

optional arguments:
  -h, --help           show this help message and exit
  -o OUTPUT            path to output file
  -d DEVICE            serial device
  --x-max X_MAX        max x value
  --x-step X_STEP      x step increment
  --y-max Y_MAX        max y value
  --y-step Y_STEP      y step increment
  --z-min Z_MIN        minimum z value
  --feedrate FEEDRATE  probe feedrate
```

### gcode.py

```
usage: gcode.py [-h] -g GCODE {adjust,extent} ...

Process gcode files

optional arguments:
  -h, --help       show this help message and exit
  -g GCODE         path to input gcode file

commands:
  {adjust,extent}
    adjust         adjust gcode z values
    extent         output gcode extent
```

```
usage: gcode.py adjust [-h] -p POINTS

optional arguments:
  -h, --help  show this help message and exit
  -p POINTS   path to points file
```
