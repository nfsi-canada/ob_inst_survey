"""Trilateration survey of ocean bottom instrument from ship positions and ranges."""
import sys

from argparse import ArgumentParser
from datetime import datetime, timedelta
from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer
from pyproj.crs import ProjectedCRS
from pyproj.crs.coordinate_operation import TransverseMercatorConversion

import ob_inst_survey as obsurv

DFLT_PREFIX = "RANGINGSURVEY"
DFLT_PATH = Path.cwd() / "results/"
DFLT_TIMEZONE = +13


def main():
    # Retrieve CLI arguments.
    helpdesc: str = (
        "Calculate the trilaterated instrument position from an observation file."
        "The observation file must be in CSV format with a header row containing "
        "the following values at a minimum:"
        "'range','lonDec', 'latDec', 'htAmsl'. \n"
        "If an optional start/deployed coordinate is not specified then a mean of "
        "all observation coordinates and depth of 1000m will be used as a start "
        "location"
    )
    parser = ArgumentParser(
        parents=[
            obsurv.obsfile_parser(),
            obsurv.apriori_coord_parser(),
            obsurv.out_filepath_parser(DFLT_PATH),
            obsurv.out_fileprefix_parser(DFLT_PREFIX),
            obsurv.options_parser(),
        ],
        description=helpdesc,
    )
    args = parser.parse_args()

    obsvn_in_filename = Path(args.obsfile)

    if args.startcoord:
        apriori_coord = pd.Series(args.startcoord, ("lonDec", "latDec", "htAmsl"))
        apriori_coord["htAmsl"] = -apriori_coord["htAmsl"]
    else:
        apriori_coord = pd.Series(dtype=float)

    if args.utc:
        tz_offset = 0
    elif args.tz_offset is not None:
        tz_offset = args.tz_offset
    else:
        tz_offset = DFLT_TIMEZONE
    timestamp_start = timestamp_from_file(str(obsvn_in_filename), tz_offset)
    if timestamp_start:
        timestamp_start = f"{timestamp_start}"

    outfile_path: Path = args.outfilepath
    outfile_name = f"{args.outfileprefix}_{timestamp_start}"
    rsltfile_name = outfile_path / f"{outfile_name}_RESULT.csv"
    obsvn_out_filename = outfile_path / f"{obsvn_in_filename.stem}_OUT.csv"

    # Organize other arguments
    calc_kwargs = {}
    if args.maxrange:
        calc_kwargs.update({'maxrange': args.maxrange})
    if args.outlier_resid:
        calc_kwargs.update({'max_resid': args.outlier_resid})
    if args.tz_offset is not None:
        calc_kwargs.update({'tz_offset': args.tz_offset})
    if args.tat:
        calc_kwargs.update({'tat': args.tat})
    if args.disco:
        calc_kwargs.update({'disco': args.disco})
    if args.start:
        calc_kwargs.update({'starttime': obsurv.parse_cli_datetime(args.start)})
    if args.end:
        calc_kwargs.update({'endtime': obsurv.parse_cli_datetime(args.end)})

    plot_kwargs = {}
    if args.flexaxis:
        plot_kwargs.update({'flex_lims': args.flexaxis})
    if args.plotmax is not None:
        plot_kwargs.update({'ax_max': args.plotmax})

    # Create directories for results.
    outfile_path.mkdir(parents=True, exist_ok=True)
    print(f"Results will be saved to {obsvn_out_filename}")

    all_obs_df = load_survey_data(obsvn_in_filename, **calc_kwargs)
    # TODO: Calculate range from travel-time if not included (require TAT CLI parameter)

    final_coord, apriori_coord_returned, all_obs_df = obsurv.trilateration(all_obs_df, apriori_coord, **calc_kwargs)
    if apriori_coord.empty:
        apriori_coord = apriori_coord_returned

    # Log details to console
    # print(f"Observations used in determining surveyed coord:\n{all_obs_df}")
    # print(f"Final coordinate Series:\n{final_coord}")

    # Plot the result figure.
    fig = obsurv.init_plot_trilateration()

    # Transform to Transverse Mercator
    local_tm = TransverseMercatorConversion(
        latitude_natural_origin=apriori_coord["latDec"],
        longitude_natural_origin=apriori_coord["lonDec"],
        false_easting=0.0,
        false_northing=0.0,
        scale_factor_natural_origin=1.0,
    )

    proj_local_tm = ProjectedCRS(
        conversion=local_tm,
        geodetic_crs="EPSG:4979",
    )
    trans_geod_to_tm = Transformer.from_crs(
        "EPSG:4979", proj_local_tm, always_xy=True
    )

    (
        all_obs_df["mE"],
        all_obs_df["mN"],
    ) = trans_geod_to_tm.transform(
        xx=all_obs_df.lonDec, yy=all_obs_df.latDec
    )

    (
        final_coord["mE"],
        final_coord["mN"],
    ) = trans_geod_to_tm.transform(
        xx=final_coord.lonDec, yy=final_coord.latDec
    )

    (
        apriori_coord["mE"],
        apriori_coord["mN"],
    ) = trans_geod_to_tm.transform(
        xx=apriori_coord.lonDec, yy=apriori_coord.latDec
    )

    final_coord["aprLon"] = apriori_coord["lonDec"]
    final_coord["aprLat"] = apriori_coord["latDec"]
    final_coord["aprHt"] = apriori_coord["htAmsl"]
    final_coord["driftDist"], final_coord["driftBrg"] = rect2pol(
        final_coord["mN"] - apriori_coord["mN"],
        final_coord["mE"] - apriori_coord["mE"],
    )
    final_coord.to_frame().T.to_csv(rsltfile_name, index=False)

    obsurv.plot_trilateration(
        fig=fig,
        apriori_coord=apriori_coord,
        final_coord=final_coord,
        observations=all_obs_df,
        plotfile_path=outfile_path,
        plotfile_name=outfile_name,
        title=f"{args.outfileprefix} {timestamp_start}",
        **plot_kwargs
    )

    all_obs_df.to_csv(obsvn_out_filename, index=False)

    if not args.hidefig:
        plt.show()


def load_survey_data(filename, **kwargs):
    data_file = filename
    disco_fmt = kwargs.pop('disco', False)
    try:
        if disco_fmt:
            input_df = read_obs_locator_log(data_file)
        else:
            input_df = pd.read_csv(data_file)
    except FileNotFoundError:
        sys.exit(f"File '{data_file}' does not exist!")

    # Ensure decimal latitude and longitude values have correct sign.
    if "lat" in input_df:
        input_df["latDec"] = np.where(
            input_df["lat"].str[-1].isin(("S", "s")),
            -1 * input_df["latDec"].abs(),
            input_df["latDec"].abs(),
        )

    if "lon" in input_df:
        input_df["lonDec"] = np.where(
            input_df["lon"].str[-1].isin(("W", "w")),
            -1 * input_df["lonDec"].abs(),
            input_df["lonDec"].abs(),
        )

    # Find depth column if 'htAmsl' not present
    if 'htAmsl' not in input_df:
        depth_keys = [
            ['depth', -1],
            ['Depth', -1],
            ['elev', 1],
            ['Elevation', 1],
            ['elevation', 1],
        ]
        z = False
        while (len(depth_keys) > 0) and not z:
            key_info = depth_keys.pop(0)
            if key_info[0] in input_df:
                input_df['htAmsl'] = key_info[1] * input_df[key_info[0]]
                z = True

        # Default depth of '0' if no depth data present
        if not z:
            input_df['htAmsl'] = 0

    # Filter input data to time range of interest (if specified)
    if 'datetime' in input_df:
        if 'starttime' in kwargs:
            input_df = input_df[input_df['datetime'] >= kwargs['starttime']]
        if 'endtime' in kwargs:
            input_df = input_df[input_df['datetime'] <= kwargs['endtime']]

    return input_df


def read_obs_locator_log(filename):
    """Read log file created by OBS Locator widget in Guralp Discovery software"""
    from datetime import datetime
    import re

    formats = [int, 'date', 'time', float, float, int, float, float, float]

    f = open(filename)
    head = None
    while head is None:
        temp = f.readline()
        if temp[0] != '#' and temp.strip():
            head = re.split(r',|\s', temp.lower())
    head.append('datetime')

    range_data = []
    for line in f.readlines():
        if line[0] == '#':
            continue

        parts = re.split(r',|\s', line)
        values = []
        for i in range(len(parts)):
            if isinstance(formats[i], type):
                values.append(formats[i](parts[i]))
            elif formats[i] == 'date':
                values.append(datetime.strptime(parts[i], '%d-%m-%Y').date())
            elif formats[i] == 'time':
                values.append(datetime.strptime(parts[i], '%H:%M:%S').time())
            else:
                values.append(parts[i])
        values.append(datetime.combine(values[1], values[2]))
        range_data.append(values)

    data = pd.DataFrame(range_data, columns=head)
    # Ensure required columns are present
    data['latDec'] = data['lat']
    data['lonDec'] = data['lon']
    data['htAmsl'] = 0
    return data


def timestamp_from_file(filename, tz_offset=None):
    # An empty string will be returned if no valid timestamp found.
    timestamp = ""
    timestamp_pattern = r"\d{4}[:_-]\d{2}[:_-]\d{2}[Tt :_-]\d{2}[:_-]\d{2}"
    try:
        # Look for timestamp in the filename.
        timestamp = re.search(timestamp_pattern, filename).group()
    except AttributeError:
        # If no valid timestamp in filename look inside file.
        with open(filename, mode="r", encoding="utf-8") as file:
            file_lines = file.readlines()
        for line in file_lines:
            try:
                # Find first occurrence of a timestamp in a line of the file.
                timestamp = re.search(timestamp_pattern, line).group()
                break
            except AttributeError:
                # If no valid timestamp continue with next line.
                pass
    if timestamp:
        # Time zone offset
        if tz_offset is not None:
            tzo = tz_offset
        else:
            tzo = DFLT_TIMEZONE
        # Standardise timestamp format
        timestamp = re.sub(r"[Tt :_-]", r"_", timestamp)
        timestamp = datetime.strptime(timestamp, r"%Y_%m_%d_%H_%M")
        timestamp = (
            timestamp
            - timedelta(hours=tzo)
        )
        timestamp = timestamp.strftime("%Y-%m-%d_%H-%M")

    return timestamp


def rect2pol(x_coord, y_coord):
    distance = np.sqrt(x_coord**2 + y_coord**2)
    bearing = np.degrees(np.arctan2(y_coord, x_coord))
    if bearing < 0:
        bearing += 360
    return distance, bearing


if __name__ == "__main__":
    main()
