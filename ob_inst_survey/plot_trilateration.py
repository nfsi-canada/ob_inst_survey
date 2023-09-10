from pathlib import Path

import cartopy.crs as ccrs
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer
from pyproj.crs import ProjectedCRS
from pyproj.crs.coordinate_operation import TransverseMercatorConversion


def init_plot_trilateration(title: str = "Ranging Survey") -> plt.figure:
    plt.ion()
    plt.rcParams["font.family"] = "sans-serif"
    fig = plt.figure(
        layout="constrained",
    )
    fig.suptitle(title)
    return fig


def plot_trilateration(
    fig: plt.figure,
    final_coord: pd.Series,
    observations: pd.DataFrame,
    plotfile_path: Path = None,
    plotfile_name: str = None,
):
    plotfile: Path = None
    if plotfile_path and plotfile_name:
        plotfile = plotfile_path / f"{plotfile_name}.png"

    plt.clf()
    # Transform to Transverse Mercator
    local_tm = TransverseMercatorConversion(
        latitude_natural_origin=final_coord["latDec"],
        longitude_natural_origin=final_coord["lonDec"],
        false_easting=0.0,
        false_northing=0.0,
        scale_factor_natural_origin=1.0,
    )
    proj_local_tm = ProjectedCRS(
        conversion=local_tm,
        geodetic_crs="EPSG:4979",
    )
    trans_geod_to_tm = Transformer.from_crs("EPSG:4979", proj_local_tm, always_xy=True)

    (
        observations["mE"],
        observations["mN"],
    ) = trans_geod_to_tm.transform(xx=observations.lonDec, yy=observations.latDec)
    used_obs_df = observations.loc[~observations["outlier"]]
    excl_obs_df = observations.loc[observations["outlier"]]

    (
        final_coord["mE"],
        final_coord["mN"],
    ) = trans_geod_to_tm.transform(xx=final_coord.lonDec, yy=final_coord.latDec)

    # Generate plot
    local_tm = ccrs.TransverseMercator(
        central_longitude=final_coord["lonDec"],
        central_latitude=final_coord["latDec"],
        false_easting=0.0,
        false_northing=0.0,
        scale_factor=1.0,
    )
    ax1 = plt.axes(projection=local_tm)
    ax1.plot(
        observations["mE"],
        observations["mN"],
        marker="",
        color="blue",
        linestyle="--",
        linewidth=0.5,
        label="",
    )
    ax1.plot(
        used_obs_df["mE"],
        used_obs_df["mN"],
        marker="o",
        markersize=3,
        color="blue",
        linestyle="",
        label="Included",
    )
    ax1.plot(
        excl_obs_df["mE"],
        excl_obs_df["mN"],
        marker="x",
        markersize=3,
        color="red",
        linestyle="",
        label="Excluded",
    )
    ax1.plot(
        final_coord.mE,
        final_coord.mN,
        marker="x",
        markersize=5,
        color="green",
        linestyle="",
        label="Surveyed",
    )

    err_circle = plt.Circle(
        (final_coord.mE, final_coord.mN),
        final_coord["stdErr"] * 100,
        fill=False,
        edgecolor="green",
        linewidth=0.5,
        linestyle="--",
    )
    ax1.add_artist(err_circle)

    ax1.legend(loc="upper left")
    ax1.set_extent(
        [-2100, 2100, -2100, 2100],
        crs=local_tm,
    )
    ax1.set_xticks([-2000, -1000, 0, 1000, 2000])
    ax1.set_yticks([-2000, -1000, 0, 1000, 2000])
    plt.minorticks_on()
    plt.grid(which="major", color="grey", linestyle="-", linewidth=0.5)
    plt.grid(which="minor", color="grey", linestyle="--", linewidth=0.25)

    intvl_secs = 60
    intvl_mins = intvl_secs / 60
    intvl_degs = intvl_mins / 60
    lon_min = round_dn_minute(np.min(observations["lonDec"]), intvl_mins)
    lon_max = round_up_minute(np.max(observations["lonDec"]), intvl_mins)
    lat_min = round_dn_minute(np.min(observations["latDec"]), intvl_mins)
    lat_max = round_up_minute(np.max(observations["latDec"]), intvl_mins)

    grdlns = ax1.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        dms=True,
        x_inline=False,
        y_inline=False,
        color="#0000ff55",
        linestyle="--",
    )
    grdlns.xlines = True
    grdlns.ylines = True
    grdlns.bottom_labels = False
    grdlns.left_labels = False
    label_style = {"size": 8, "color": "blue", "rotation": 45}
    grdlns.xlabel_style = label_style
    grdlns.ylabel_style = label_style
    grdlns.xlocator = mpl.ticker.FixedLocator(
        np.arange(lon_min, lon_max + intvl_degs, intvl_degs)
    )
    grdlns.ylocator = mpl.ticker.FixedLocator(
        np.arange(lat_min, lat_max + intvl_degs, intvl_degs)
    )

    if plotfile:
        plt.savefig(plotfile, dpi=150, format="png")
    fig.canvas.draw()
    fig.canvas.flush_events()


def round_up_minute(dec_deg: float, minutes: int = 1):
    """
    Round decimal degrees up to the nearest specified number of minutes while
    retaining decimal degrees representation.
    """
    multiplier = 60 / minutes
    return np.ceil(dec_deg * multiplier) / multiplier


def round_dn_minute(dec_deg: float, minutes: int = 1):
    """
    Round decimal degrees down to the nearest specified number of minutes while
    retaining decimal degrees representation.
    """
    multiplier = 60 / minutes
    return np.floor(dec_deg * multiplier) / multiplier


def to_dms(dec_deg: float) -> str:
    """
    Convert decimal degrees to a string representation formatted as
    DDD°MM'SS.SSS"
    """
    deg = np.trunc(dec_deg)
    mins = np.trunc((dec_deg - deg) * 60)
    sec = (dec_deg - deg - mins / 60) * 3600
    return f"{deg: 04.0f}°{abs(mins):02.0f}'{abs(sec):2.3f}\""
