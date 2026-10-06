from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import pandas as pd

@dataclass(frozen=True)
class Instrument:
    """
    Parameters matching the supplied spreadsheet.

    Units:
        throughput:         dimensionless
        pixel_scale:        arcsec / pixel
        read_noise:         electrons / pixel / read
        sky_mag:            mag / arcsec^2
        telescope_diameter: cm
        filter_width:       Angstrom
        n_plate:            number of polarimetric plate positions/sub-images
        stellar_factor:     spreadsheet factor applied only to the stellar rate
        gain_e_per_adu:     Detector gain in electrons per ADU.
        full_well_e:        Approximate detector full well in electrons/pixel.
        linear_limit_adu:   Approximate upper linearity limit in ADU/pixel.
        saturation_margin:  Fraction of the specified limit at which to issue a warning.
    """
    name: str
    throughput: float 
    pixel_scale: float 
    read_noise: float 
    sky_mag: float 
    telescope_diameter: float 
    filter_width: float 
    n_plate: int = 8
    stellar_factor: float = 0.5
    
    gain_e_per_adu: Optional[float] = None
    full_well_e: Optional[float] = None
    linear_limit_adu: Optional[float] = None
    saturation_margin: float = 0.90

SOUTHPOL_FILTERS = {"V": Instrument(name="SouthPol V",
									throughput=0.81,
									# pixel_scale=0.3713,
									pixel_scale=0.28,
									read_noise=5.0,
									sky_mag=22.0,
									telescope_diameter=100.0,
									filter_width=786.0,
									n_plate=8,
									
									# Replace only after confirming the actual CCD values.
									gain_e_per_adu=0.50,
									full_well_e=100_000.0,
									linear_limit_adu=50_000.0,
									),
					}
    
def _as_array(x):
    """Convert scalar or array-like input to a NumPy array."""
    return np.asarray(x, dtype=float)


def calculate_exposure(magnitude,
                       exposure_time,
                       *,
                       seeing=1.2,
                       instrument: Instrument,
                       band: str = "V",
                       n_exposures: int = 1,
                      ):
    """
    SouthPol ETC calculation.
    
    `exposure_time` is the duration of one individual frame.

    Parameters
    ----------
    magnitude : float or array-like
        Stellar magnitude in the selected band.
    exposure_time : float or array-like
        Exposure/integration time in seconds.
    seeing : float or array-like
        Seeing FWHM in arcsec.
    instrument : Instrument
        Instrument and observing parameters.
    band : str
        Label for the filter. The default is "V".
    n_exposures : int
        Number of individual exposures. This affects total SNR if the
        exposures are combined, but not the peak in one exposure.

    Returns
    -------
    pandas.DataFrame
        One row per broadcast combination of magnitude, exposure time,
        and seeing, containing the intermediate quantities and outputs.

    Notes
    -----
    The filter dependence is represented by Q and Dlambda.Therefore, 
    changing `band` alone does not change the numerical result. For another 
    filter, supply an Instrument instance with the appropriate throughput, 
    sky magnitude, and bandwidth.
    """
    if band is None:
        band = "unknown"

    mag = _as_array(magnitude)
    time = _as_array(exposure_time)
    fwhm = _as_array(seeing)

    if np.any(time <= 0):
        raise ValueError("exposure_time must be positive.")
    if np.any(fwhm <= 0):
        raise ValueError("seeing must be positive.")
    if np.any(mag >= 100):
        raise ValueError("Magnitude values are unrealistically large.")
    if instrument.pixel_scale <= 0:
        raise ValueError("pixel_scale must be positive.")
    if instrument.telescope_diameter <= 0:
        raise ValueError("telescope_diameter must be positive.")
    if instrument.filter_width <= 0:
        raise ValueError("filter_width must be positive.")
    if instrument.n_plate <= 0:
        raise ValueError("n_plate must be positive.")

    mag, time, fwhm = np.broadcast_arrays(mag, time, fwhm)

    q = instrument.throughput
    scale = instrument.pixel_scale
    rn = instrument.read_noise
    sky_mag = instrument.sky_mag
    diameter = instrument.telescope_diameter
    dlambda = instrument.filter_width
    n_plate = instrument.n_plate

    # Spreadsheet: npix = (Q / Scale)^2
    npix = (fwhm / scale) ** 2

    # Spreadsheet stellar rate:
    # Q*10^(-0.4*(m+39.39))*PI()/4*D^2*Dlambda*
    # 10000000/3.6E-12/2
    stellar_rate = (q * 10.0 ** (-0.4 * (mag + 39.39))
                    * np.pi / 4.0 * diameter**2 * dlambda
                    * 1.0e7 / 3.6e-12 * instrument.stellar_factor)

    # Spreadsheet sky rate per pixel:
    # Q*10^(-0.4*(Sky+38.52))*PI()/4*D^2*Dlambda*
    # 10000000/3.6E-12*Scale^2
    sky_rate_per_pixel = (q * 10.0 ** (-0.4 * (sky_mag + 38.52))
                          * np.pi / 4.0 * diameter**2 * dlambda
                          * 1.0e7 / 3.6e-12 * scale**2)

    #--- Signal in one exposure.
    # ---------------------------------------------------------------------------
    stellar_electrons = stellar_rate * time
    sky_electrons_per_pixel = sky_rate_per_pixel * time

    # Exact spreadsheet SNR equation.
    variance = stellar_electrons + 2.0 * npix * (sky_electrons_per_pixel + rn**2)
    
    snr = stellar_electrons / np.sqrt(variance)

    # If n_exposures are combined, the independent signal and noise scale
    # according to sqrt(n_exposures).
    # snr_combined = snr * np.sqrt(n_exposures)
    
    # If n_plate are combined, the independent signal and noise scale
    # according to sqrt(n_plate).
    snr_combined = snr * np.sqrt(n_plate)
    
    # Exact spreadsheet Sigma P equation, expressed in percent.
    sigma_p_percent = 100.0 / (np.sqrt(n_plate) * snr)

    #--- Gaussian PSF
    # ---------------------------------------------------------------------------
    # sigma_PSF = FWHM / 2.355
    # central pixel value approximately:
    # total flux * pixel_area / (2*pi*sigma_PSF^2)
    sigma_psf = fwhm / 2.355
    pixel_area_arcsec2 = scale**2

    gaussian_peak_fraction = pixel_area_arcsec2 / (2.0 * np.pi * sigma_psf**2)

    peak_stellar_electrons = stellar_electrons * gaussian_peak_fraction
    peak_total_electrons = peak_stellar_electrons + sky_electrons_per_pixel
    # peak_total_electrons = peak_stellar_electrons 

    # Counts in ADU require a detector gain.
    if instrument.gain_e_per_adu is None:
        peak_total_adu = np.full_like(peak_total_electrons, np.nan)
    else:
        peak_total_adu = peak_total_electrons / instrument.gain_e_per_adu

    # Detector diagnostics.
    if instrument.full_well_e is None:
        full_well_fraction = np.full_like(peak_total_electrons, np.nan)
        full_well_warning = np.full(peak_total_electrons.shape, 
                                    "not evaluated: full_well_e is undefined", dtype=object)
    else:
        full_well_fraction = peak_total_electrons / instrument.full_well_e
        full_well_warning = np.where(peak_total_electrons >= instrument.full_well_e,
                                     "SATURATION: peak exceeds full well",
                                     np.where(peak_total_electrons >= instrument.saturation_margin * instrument.full_well_e,
                                              "WARNING: close to full well", "OK")
                                     )

    if instrument.linear_limit_adu is None:
        linearity_fraction = np.full_like(peak_total_electrons, np.nan)
        linearity_warning = np.full(peak_total_electrons.shape,
                                    "not evaluated: linear_limit_adu is undefined", dtype=object)
    else:
        if instrument.gain_e_per_adu is None:
            linearity_fraction = np.full_like(peak_total_electrons, np.nan)
            linearity_warning = np.full(peak_total_electrons.shape,
                                        "not evaluated: gain_e_per_adu is undefined", dtype=object)
        else:
            linearity_fraction = peak_total_adu / instrument.linear_limit_adu
            linearity_warning = np.where(peak_total_adu >= instrument.linear_limit_adu,
                                         "WARNING: above linearity limit",
                                         np.where(peak_total_adu >= instrument.saturation_margin * instrument.linear_limit_adu,
                                                  "WARNING: close to linearity limit", "OK"),
                                         )
            
    saturation_warning = np.where(full_well_warning != "OK", full_well_warning,
                                  np.where(linearity_warning != "OK", linearity_warning, "OK"))
    
    return pd.DataFrame({"band": np.broadcast_to(band, mag.shape).ravel(),
                         "magnitude": mag.ravel(),
                         "exposure_time_s": time.ravel(),
                         "seeing_arcsec": fwhm.ravel(),
                         "n_exposures": np.full(mag.size, n_exposures),
                         "npix": npix.ravel(),
                         "stellar_rate_e_per_s": stellar_rate.ravel(),
                         "sky_rate_e_per_s_per_pix": np.full(mag.size, sky_rate_per_pixel),
                         "stellar_electrons": stellar_electrons.ravel(),
                         "sky_electrons_per_pixel": sky_electrons_per_pixel.ravel(),
                         "snr": snr.ravel(),
                         "snr_combined": snr_combined.ravel(),
                         "sigma_P_percent": sigma_p_percent.ravel(),
                         "psf_sigma_arcsec": sigma_psf.ravel(),
                         "peak_stellar_electrons": peak_stellar_electrons.ravel(),
                         "peak_total_electrons": peak_total_electrons.ravel(),
                         "gain_e_per_adu": np.full(mag.size, np.nan if instrument.gain_e_per_adu is None else instrument.gain_e_per_adu),
                         "peak_total_adu": peak_total_adu.ravel(),
                         "full_well_fraction": full_well_fraction.ravel(),
                         "linearity_fraction": linearity_fraction.ravel(),
                         "full_well_warning": full_well_warning.ravel(),
                         "linearity_warning": linearity_warning.ravel(),
                         "saturation_warning": saturation_warning.ravel(),
                         })
