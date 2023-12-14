from pathlib import Path

import cartopy.crs as ccrs
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj.crs.coordinate_operation import TransverseMercatorConversion


def init_plot_trilateration() -> plt.figure:
    plt.rcParams["font.family"] = "sans-serif"
    fig = plt.figure(
        figsize=(8, 8),
        layout="constrained",
    )
    return fig


def plot_trilateration(
    fig: plt.figure,
    final_coord: pd.Series,
    apriori_coord: pd.Series,
    observations: pd.DataFrame,
    plotfile_path: Path = None,
    plotfile_name: str = None,
    title: str = "Ranging Survey",
    ax_max: float = None,
    flex_lims: bool = False,
):
    plotfile: Path = None
    if plotfile_path and plotfile_name:
        plotfile = plotfile_path / f"{plotfile_name}.png"

    plt.clf()
    # Define Transverse Mercator
    local_tm = TransverseMercatorConversion(
        latitude_natural_origin=apriori_coord["latDec"],
        longitude_natural_origin=apriori_coord["lonDec"],
        false_easting=0.0,
        false_northing=0.0,
        scale_factor_natural_origin=1.0,
    )

    used_obs_df = observations.loc[~observations["outlier"]]
    excl_obs_df = observations.loc[observations["outlier"]]

    # Generate plot
    local_tm = ccrs.TransverseMercator(
        central_longitude=apriori_coord["lonDec"],
        central_latitude=apriori_coord["latDec"],
        false_easting=0.0,
        false_northing=0.0,
        scale_factor=1.0,
    )
    ax1 = plt.axes(projection=local_tm)
    ax1.set_title(title, fontweight="bold")
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

    err_circle_plot_scale = 100
    err_circle = plt.Circle(
        (final_coord.mE, final_coord.mN),
        final_coord["stdErr"] * err_circle_plot_scale,
        fill=False,
        edgecolor="green",
        linewidth=0.5,
        linestyle="--",
    )
    ax1.add_artist(err_circle)

    ax1.plot(
        apriori_coord.mE,
        apriori_coord.mN,
        marker="x",
        markersize=5,
        color="magenta",
        linestyle="",
        label="Apriori",
    )

    drift_text = (
        f"Drift:\n"
        f"{final_coord['driftBrg']:03.0f}°\n"
        f"{final_coord['driftDist']:3.1f}m"
    )
    if final_coord["driftBrg"] <= 180:
        txt_brg = final_coord["driftBrg"]
        txt_align = "right"
    else:
        txt_brg = final_coord["driftBrg"] - 180
        txt_align = "left"
    txt_angle = 90 - txt_brg
    offset_angle = 270 - final_coord["driftBrg"]
    ax1.annotate(
        drift_text,
        xy=(apriori_coord.mE, apriori_coord.mN),
        xycoords="data",
        horizontalalignment=txt_align,
        verticalalignment="center",
        multialignment=txt_align,
        textcoords="offset points",
        xytext=(pol2rect(5, offset_angle)),
        rotation_mode="anchor",
        rotation=txt_angle,
        fontfamily="monospace",
        fontsize="small",
    )

    result_text = (
        f"Surveyed Location:\n"
        f"Lat:  {to_degmin(final_coord['latDec'])}\n"
        f"Lon:  {to_degmin(final_coord['lonDec'])}\n"
        f"Depth: {-final_coord['htAmsl']:3.1f}m\n"
        f"Error: {final_coord['stdErr']:3.1f}m\n"
        f"Error circle plotted x{err_circle_plot_scale:d}"
    )
    ax1.text(
        (100./4200),
        (100./4200),
        result_text,
        horizontalalignment="left",
        multialignment="left",
        fontfamily="monospace",
        fontsize="small",
        transform=ax1.transAxes,
    )

    apriori_text = (
        f"Apriori Location:\n"
        f"Lat:  {to_degmin(apriori_coord['latDec'])}\n"
        f"Lon:  {to_degmin(apriori_coord['lonDec'])}\n"
        f"Depth: {-apriori_coord['htAmsl']:3.1f}m"
    )
    ax1.text(
        (4100./4200),
        (100./4200),
        apriori_text,
        horizontalalignment="right",
        multialignment="left",
        fontfamily="monospace",
        fontsize="small",
        transform=ax1.transAxes,
    )

    ax1.legend(loc="upper left")
    if ax_max is None and flex_lims:
        # TODO: Existing axis limits don't seem to account for error circle...
        curr_ax_lims = [ax1.get_xlim(), ax1.get_ylim()]
        flat_lims = [abs(item) for sublist in curr_ax_lims for item in sublist]
        amx = max(flat_lims)
        if amx < 500:
            ax_max = 550
        elif amx < 1000:
            ax_max = 1100
        else:
            ax_max = 1000 * np.ceil(amx / 1000) + 100

    if ax_max is not None:
        ax1.set_extent([-ax_max, ax_max, -ax_max, ax_max], crs=local_tm)
        if ax_max < 600:
            interval = 100
        elif ax_max < 1000:
            interval = 200
        elif ax_max < 2000:
            interval = 500
        else:
            interval = 1000
        max_tick = interval * (ax_max // interval)
    else:
        ax1.set_extent(
            [-2100, 2100, -2100, 2100],
            crs=local_tm,
        )
        max_tick = 2000
        interval = 1000
    major_ticks = define_tick_marks(max_tick, interval)
    ax1.set_xticks(major_ticks)
    ax1.set_yticks(major_ticks)
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


def to_degmin(dec_deg: float) -> str:
    """
    Convert decimal degrees to a string representation formatted as
    DDD°MM.MMM'
    """
    deg = np.trunc(dec_deg)
    mins = (dec_deg - deg) * 60
    return f"{deg: 4.0f}°{abs(mins):06.3f}'"


def pol2rect(distance, bearing):
    x = distance * np.cos(np.radians(bearing))
    y = distance * np.sin(np.radians(bearing))
    return (x, y)


def rect2pol(x, y):
    distance = np.sqrt(x**2 + y**2)
    bearing = np.degrees(np.arctan2(y, x))
    if bearing < 0:
        bearing += 360
    return (distance, bearing)


def define_tick_marks(maximum, interval):
    max_tick = interval * (maximum // interval)
    ticks = np.arange(-max_tick, max_tick + 1, interval)
    return ticks
