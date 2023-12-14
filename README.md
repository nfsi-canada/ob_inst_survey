# Ocean Bottom (OB) Instrument Surveying

This is a package that provides functionality for using acoustic ranging and
NMEA GNSS feeds to survey in the locations of ocean bottom instruments.

The latest version is available on Github <www.github.com/NevPalmer/ob_inst_survey>.

## Dependencies

- Python 3.9+
- cartopy
- pyproj
- Pandas

### Default Outlier Rejection Criteria

- Range less than 50m
- Range less than a priori water depth
- Range greater than 1.6x a priori water depth (offset angle >51&deg;)
- Residual greater than 3x standard error at any iteration of trilateration calculation
