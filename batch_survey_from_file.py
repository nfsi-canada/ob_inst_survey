"""
Run ranging_survey_from_obsfile.py for several stations in sequence.
CLI inputs to be read from a CSV or JSON file (sole input argument here).
"""
import argparse
import json
import pandas as pd
import os
import subprocess
import warnings


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run trilateration survey calculation for several stations, using "
                                                 "previously tabulated range measurements (e.g. CSV file).")
    parser.add_argument('station_info', type=str,
                        help="CSV or JSON file with CLI inputs for one or more surveys. If CSV, column names must "
                             "match valid CLI inputs for the ranging_survey_from_obsfile.py script, with a priori "
                             "coordinates for inversion in columns 'startlat', 'startlon' and 'startdepth'.")

    args = parser.parse_args()

    # Read input file
    station_file = os.path.abspath(os.path.expanduser(os.path.expandvars(args.station_info)))
    if not os.path.isfile(station_file):
        raise IOError('Input file does not exist: {}'.format(os.path.normpath(station_file)))

    infile_directory = os.path.dirname(os.path.normpath(station_file))

    filetype = os.path.splitext(station_file)[-1].lower()
    if filetype == '.csv':
        station_info = pd.read_csv(station_file)
    elif filetype == '.json':
        sf = open(station_file)
        station_info = json.load(sf)
    else:
        raise IOError('Input file type {} not recognized. Must be CSV or JSON.'.format(filetype))

    if isinstance(station_info, pd.DataFrame):
        # Handle DataFrame read from CSV (decide actual format...)
        for row in station_info.itertuples():
            args_list = [
                'python',
                'ranging_survey_from_obsfile.py',
                '--outfilepath {}'.format(infile_directory)
            ]
            for key in station_info.columns.values.tolist():
                if key in ['startlat', 'startlon', 'startdepth']:
                    continue
                if getattr(row, key, False):
                    value = getattr(row, key)
                    if isinstance(value, bool):
                        args_list.append('--{0}'.format(key))
                    else:
                        args_list.append('--{0} {1}'.format(key, getattr(row, key)))

            lat_start = getattr(row, 'startlat', None)
            lon_start = getattr(row, 'startlon', None)
            dep_start = getattr(row, 'startdepth', None)
            if all([x is not None for x in [lat_start, lon_start, dep_start]]):
                args_list.append('--startcoord {} {} {}'.format(lon_start, lat_start, dep_start))

            subprocess.run(args_list)

    elif isinstance(station_info, dict):
        flags = None
        if 'flags' in station_info:
            flags = station_info.pop('flags')

        if 'stations' in station_info:
            stations = station_info.pop('stations')
        else:
            stations = []
            warnings.warn('No stations specified in input file.')

        for station in stations:
            args_list = [
                'python',
                'ranging_survey_from_obsfile.py',
                '--outfilepath {}'.format(infile_directory)
            ]
            for bkey in station_info:
                args_list.append('--{0} {1}'.format(bkey, station_info[bkey]))
            for skey in station:
                args_list.append('--{0} {1}'.format(skey, station[skey]))
            if flags is not None:
                for f in flags:
                    args_list.append('--{0}'.format(f))

            subprocess.run(args_list)

    else:
        warnings.warn('Unrecognized object type: {}'.format(type(station_info)))
