"""Functions for providing args/parameters to modules."""

from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime
from pathlib import Path
import re

import ob_inst_survey as obsurv

DFLT_PATH = Path.cwd() / "out/"
DFLT_INFILE = None


def obsfile_parser():
    """Returns parser for full path and filename for input file."""
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        "--obsfile",
        help=(f"Full path and filename for input observations file location."),
        type=Path,
    )
    return parser


def replay2files_parser(
    dflt_nmeareplayfile: Path = DFLT_INFILE,
    dflt_rngreplayfile: Path = DFLT_INFILE,
):
    """Returns parser for full path and filename for input files."""
    parser = ArgumentParser(add_help=False)
    infile_group = parser.add_argument_group(
        title=(
            "Input File Parameters:\n"
            "(Only provide these parameters if replaying previously recorded "
            "files instead of using live NMEA and Ranging data.)"
        )
    )
    infile_group.add_argument(
        "--replaynmea",
        help=(
            f"Full path and filename for NMEA input file. Default: {dflt_nmeareplayfile}"
        ),
        default=dflt_nmeareplayfile,
        type=Path,
    )
    infile_group.add_argument(
        "--replayrange",
        help=(
            f"Full path and filename for Ranging input file. Default: {dflt_rngreplayfile}"
        ),
        default=dflt_rngreplayfile,
        type=Path,
    )
    infile_group.add_argument(
        "--timestampoffset",
        help=(
            "If NMEA and Range files are not time synced, specify number of "
            "seconds to offset the ranging timestamp to bring in sync with NMEA. "
            "(If Ranging timestamp is ahead of NMEA timestamp value should "
            "be negative, otherwise positive.) Default: 0.0"
        ),
        default=0.0,
        type=float,
    )
    infile_group.add_argument(
        "--replaystart",
        help=(
            "Starting time (UTC) of the file to be replayed. "
            "If not specified then assumed to be time of first "
            "record in the file. Format: 'yyyy-mm-dd_HH:MM:SS', "
            "Default: None"
        ),
        default=None,
        type=timestamp_type,
    )
    infile_group.add_argument(
        "--replayspeed",
        help=("Speed multiplier for replaying file. Default: 1"),
        default=1,
        type=float,
    )
    return parser


def replayfile_parser(dflt_replayfile: Path = DFLT_INFILE):
    """Returns parser for full path and filename for input file."""
    parser = ArgumentParser(add_help=False)
    infile_group = parser.add_argument_group(title="Input File Parameters:")
    infile_group.add_argument(
        "--replayfile",
        help=(f"Full path and filename for input file. Default: {dflt_replayfile}"),
        default=dflt_replayfile,
        type=Path,
    )
    infile_group.add_argument(
        "--replaystart",
        help=(
            "Starting time (UTC) of the file to be replayed. "
            "If not specified then assumed to be time of first "
            "record in the file. Format: 'yyyy-mm-dd_HH:MM:SS', "
            "Default: None"
        ),
        default=None,
        type=timestamp_type,
    )
    infile_group.add_argument(
        "--replayspeed",
        help=("Speed multiplier for replaying file. Default: 1"),
        default=1,
        type=float,
    )
    return parser


def out_filepath_parser(dflt_filepath: Path = DFLT_PATH):
    """Returns parser for file directory location"""
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        "--outfilepath",
        help=(f"Full directory path for file location. Default: {dflt_filepath}"),
        default=dflt_filepath,
        type=Path,
    )
    return parser


def out_fileprefix_parser(dflt_fileprefix: str):
    """Returns parser for file prefix string"""
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        "--outfileprefix",
        help=(
            f"Filename prefix where the full filename will be "
            f"'<fileprefix>_YYYY-MM-DD_HH-MM.txt'. "
            f"The timestamp used will be the time when logging starts. "
            f"Default: {dflt_fileprefix}"
        ),
        default=dflt_fileprefix,
        type=str,
    )
    return parser


def lograw_parser():
    """Returns parser for lograw switch"""
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        "--lograw",
        help=(
            "Option to additionally log raw NMEA and Range data to files in "
            "subdirectories of the provided <outfile_path>."
        ),
        action="store_true",
        default=False,
    )
    return parser


def ip_arg_parser(nmea_conn: obsurv.IpParam):
    """
    Returns parser for Internet Protocol (IP) connection parameters.
    """
    parser = ArgumentParser(add_help=False)
    ip_group = parser.add_argument_group(title="NMEA stream IP Parameters:")
    ip_group.add_argument(
        "--ipaddr",
        help=f"IP address for UDP or TCP connection. Default: {nmea_conn.addr}",
        default=nmea_conn.addr,
    )
    ip_group.add_argument(
        "--ipport",
        type=int,
        help=f"IP Port for UDP or TCP connection. Default: {nmea_conn.port}",
        default=nmea_conn.port,
    )
    ip_group.add_argument(
        "--ipprot",
        help=f"Proticol for IP connection (TCP/UDP). Default: {nmea_conn.prot}",
        default=nmea_conn.prot,
    )
    ip_group.add_argument(
        "--ipbuffer",
        help=f"Buffer size (bytes) for IP connection. Default: {nmea_conn.buffer}",
        default=nmea_conn.buffer,
    )

    return parser


def ser_arg_parser(ser_conn: obsurv.SerParam):
    """
    Returns parser for IP connection parameters.
    """
    parser = ArgumentParser(add_help=False)
    ser_group = parser.add_argument_group(title="Edgetech stream Serial Parameters:")
    ser_group.add_argument(
        "--serport",
        help=f'Serial port name. Default: "{ser_conn.port}"',
        default=ser_conn.port,
    )
    ser_group.add_argument(
        "--serbaud",
        type=int,
        help=f"Serial baud rate. Default: {ser_conn.baud}",
        default=ser_conn.baud,
    )
    ser_group.add_argument(
        "--serparity",
        help=f'Serial parity. Default: "{ser_conn.parity}"',
        default=ser_conn.parity,
    )
    ser_group.add_argument(
        "--serstop",
        type=int,
        help=f"Serial stop bit. Default: {ser_conn.stop}",
        default=ser_conn.stop,
    )
    ser_group.add_argument(
        "--serbytesize",
        type=int,
        help=f"Serial byte size. Default: {ser_conn.bytesize}",
        default=ser_conn.bytesize,
    )
    return parser


def edgetech_arg_parser(
    etech_conn: obsurv.EtechParam,
):
    """
    Returns parser for EdgeTech 8011M deckbox parameters.
    """
    parser = ArgumentParser(
        parents=[ser_arg_parser(etech_conn)],
        add_help=False,
    )
    rng_group = parser.add_argument_group(title="Edgetech Ranging Parameters:")
    rng_group.add_argument(
        "--acouturn",
        type=float,
        help=f"Delay in ms for reply from BPR transducer. Default: {etech_conn.turn_time}",
        default=etech_conn.turn_time,
    )
    rng_group.add_argument(
        "--acouspd",
        type=int,
        help=f"Speed of sound in water (typical 1450 to 1570 m/sec). Default: {etech_conn.snd_spd}",
        default=etech_conn.snd_spd,
    )
    return parser


def apriori_coord_parser():
    """Returns parser for apriori coordinate"""
    parser = ArgumentParser(add_help=False)
    parser.add_argument(
        "--startcoord",
        help=(
            "Specify the start or apriori coordinate. Format is three space "
            "seperated floats <Lon> <Lat> <Depth> where Lat & Lon are decimal "
            "degrees, and Depth is metres below MSL."
        ),
        default=None,
        nargs=3,
        type=float,
    )
    return parser


def timestamp_type(timestamp: str) -> datetime:
    """Custom argparse type for user timestamp values given from the command line"""
    try:
        timestamp = re.sub(r"[-: _/tT]", "_", timestamp)
        return datetime.strptime(timestamp, "%Y_%m_%d_%H_%M_%S")
    except ValueError as exc:
        msg = (
            f"Specified timestamp ({timestamp}) is not valid! "
            f"Expected format, 'yyyy-mm-dd_HH:MM:SS'!"
        )
        raise ArgumentTypeError(msg) from exc


def options_parser():
    """Parser for various optional CLI arguments"""
    parser = ArgumentParser(add_help=False)
    parser.add_argument('--tz_offset', default=None, type=float, help="Time zone offset from UTC in hours.")
    parser.add_argument('--utc', action="store_true", help="Do not use time zone offset, all times in UTC.")
    parser.add_argument('--maxrange', default=1.6, type=float,
                        help="Maximum allowable range measurement to use in trilateration calculation, as a multiplier "
                             "of the a priori water depth. Ranges greater than this will be marked as outliers and "
                             "excluded. Default 1.6")
    parser.add_argument('--outlier_resid', default=3, type=float,
                        help="Outlier cutoff for range residual in trilateration calculation, as a number of standard "
                             "deviations. Default 3.")
    parser.add_argument('--hidefig', action="store_true",
                        help="Do not show figure window during calculation. Useful for batch processing.")
    parser.add_argument('--tat', type=int, default=320,
                        help="Delay time in microseconds for bottom-side acoustic modem, between receiving "
                             "transmission and sending response. Used for calculating range from total acoustic "
                             "traveltime.")
    return parser
