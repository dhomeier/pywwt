import numpy as np
import pytz
from astropy.io import fits
from astropy.coordinates import ICRS
from astropy.time import Time
from datetime import datetime
from reproject import reproject_interp
from reproject.mosaicking import find_optimal_celestial_wcs

__all__ = ["sanitize_image"]


def sanitize_image(image, output_file, overwrite=False, hdu_index=None, **kwargs):
    """
    Transform a FITS image so that it is in equatorial coordinates with a TAN
    projection and floating-point values, all of which are required to work
    correctly in WWT at the moment.

    Image can be a filename, an HDU, or a tuple of (array, WCS).
    """

    # In case of a FITS file with more than one HDU, we need to choose one
    if isinstance(image, str):
        with fits.open(image) as hdul:
            if hdu_index is not None:
                image = hdul[hdu_index]
            else:
                for hdu in hdul:
                    if (
                        hasattr(hdu, "shape")
                        and len(hdu.shape) > 1
                        and type(hdu) is not fits.hdu.table.BinTableHDU
                    ):
                        break
                image = hdu
            transform_to_wwt_supported_fits(image, output_file, overwrite)
    else:
        transform_to_wwt_supported_fits(image, output_file, overwrite)


def transform_to_wwt_supported_fits(image, output_file, overwrite):
    wcs, shape_out = find_optimal_celestial_wcs([image], frame=ICRS(), projection="TAN")
    array = reproject_interp(image, wcs, shape_out=shape_out, return_footprint=False)
    fits.writeto(
        output_file, array.astype(np.float32), wcs.to_header(), overwrite=overwrite
    )


def validate_traits(cls, traits):
    """
    Helper function to ensure user-provided trait names match those of the
    class they're being used to instantiate.
    """
    mismatch = [key for key in traits if key not in cls.trait_names()]
    if mismatch:
        raise KeyError(
            "Key{0} {1} do{2}n't match any layer trait name".format(
                "s" if len(mismatch) > 1 else "",
                mismatch,
                "" if len(mismatch) > 1 else "es",
            )
        )


def ensure_utc(tm, str_allowed):
    """
    Helper function to convert a time object (Time, datetime, or UTC string
    if str_allowed == True) into UTC before passing it to WWT.
    str_allowed is True for wwt.set_current_time (core.py) and False for TableLayer's 'time_att' implementation (layers.py).
    """

    if tm is None:
        utc_tm = datetime.utcnow().astimezone(pytz.UTC).isoformat()

    elif isinstance(tm, datetime):
        if tm.tzinfo is None:
            utc_tm = pytz.utc.localize(tm).isoformat()
        elif tm.tzinfo == pytz.UTC:
            utc_tm = tm.isoformat()
        else:  # has a non-UTC time zone
            utc_tm = tm.astimezone(pytz.UTC).isoformat()

    elif isinstance(tm, Time):
        utc_tm = tm.to_datetime(pytz.UTC).isoformat()

    else:
        if str_allowed:  # is an ISOT string
            dt = Time(tm, format="isot").to_datetime(pytz.UTC)
            utc_tm = dt.isoformat()
        else:
            raise ValueError("Time must be a datetime or astropy.Time object")

    return utc_tm
