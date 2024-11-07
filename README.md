# Ocean Bottom (OB) Instrument Surveying

This is a package that provides functionality for using acoustic ranging and NMEA GNSS feeds to survey in the locations of ocean bottom instruments.

The latest official version is available on GitHub: [NevPalmer/ob_inst_survey](https://github.com/NevPalmer/ob_inst_survey).

NFSI staff have made various modifications to this package which have not yet been incorporated in the official release. Our version can be found here: [nfsi-canada/ob_inst_survey](https://github.com/nfsi-canada/ob_inst_survey)

## Dependencies

- Python 3.9+
- matplotlib
- numpy
- scipy
- pandas
- cartopy
- pyproj

## Default Outlier Rejection Criteria

- Range less than 50m
- Range less than a priori water depth
- Range greater than 1.6x a priori water depth (offset angle >51&deg;)
- Residual greater than 3x standard error at any iteration of trilateration calculation
