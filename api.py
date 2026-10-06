from typing import Literal

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from etc_model import SOUTHPOL_FILTERS, calculate_exposure


app = FastAPI(title="SouthPol Exposure-Time Calculator API",
              description="API for calculating SouthPol count rates, S/N, polarization precision, peak counts, and detector warnings. This is an adaptation of the SouthPol exposure-time calculator (ETC) developed by Prof. Antonio Mario Magalhaes (Copyright: April 2026) into a Python routine. The original ETC calculates the compact photon-counting model for the SouthPol half-wave plate polarimeter. The f/5 focal reducer has been assumed.",
              version="0.1.0",
              )

class ETCRequest(BaseModel):
    """Input parameters for one SouthPol ETC calculation."""

    band: str = Field(default="V", description="Photometric band/filter name.")

    magnitude: float = Field(..., ge=-5.0, le=35.0, 
                             description="Apparent stellar magnitude in the selected band.")

    exposure_time_s: float = Field(..., gt=0.0, le=7200.0,
                                   description="Individual exposure time in seconds.")

    seeing_arcsec: float = Field(default=1.2, gt=0.0, le=10.0,
                                 description="Seeing FWHM in arcsec.")

    n_exposures: int = Field(default=1, ge=1, le=1000,
                             description="Number of individual exposures to combine.")

def make_json_safe(value):
    """
    Convert NumPy values and NaN values into JSON-compatible Python values.
    """
    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, float) and not np.isfinite(value):
        return None

    return value

@app.get("/")
def root():
    """Basic API status endpoint."""
    return {"name": "SouthPol Exposure-Time Calculator API",
            "status": "running",
            "documentation": "/docs",
            }

@app.get("/api/filters")
def list_filters():
    """Return the filters available in the ETC."""
    return {"filters": {name: {"name": instrument.name,
                               "throughput": instrument.throughput,
                               "pixel_scale_arcsec_per_pixel": instrument.pixel_scale,
                               "read_noise_electrons": instrument.read_noise,
                               "sky_brightness_mag_per_arcsec2": instrument.sky_mag,
                               "filter_width_angstrom": instrument.filter_width,
                               "n_plate_positions": instrument.n_plate,
                               }
                        for name, instrument in SOUTHPOL_FILTERS.items()
                        }
            }

@app.post("/api/calculate")
def calculate_etc(request: ETCRequest):
    """
    Run one SouthPol ETC calculation.

    The input exposure time is the duration of one individual exposure.
    Peak-count and saturation quantities therefore refer to one frame.
    """
    if request.band not in SOUTHPOL_FILTERS:
        valid_filters = ", ".join(SOUTHPOL_FILTERS.keys())
        raise HTTPException(status_code=400, detail=(f"Unknown band '{request.band}'. Available bands: {valid_filters}."))

    instrument = SOUTHPOL_FILTERS[request.band]

    try:
        result = calculate_exposure(magnitude=request.magnitude,
                                    exposure_time=request.exposure_time_s,
                                    seeing=request.seeing_arcsec,
                                    instrument=instrument,
                                    band=request.band,
                                    n_exposures=request.n_exposures,
                                    )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    row = result.iloc[0].to_dict()
    return {key: make_json_safe(value) for key, value in row.items()}
