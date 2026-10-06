import numpy as np

from etc_model import SOUTHPOL_FILTERS, calculate_exposure


def test_spreadsheet_v12_300s_case():
    result = calculate_exposure(magnitude=12.0,
    							exposure_time=300.0,
    							seeing=1.2,
    							instrument=SOUTHPOL_FILTERS["V"],
    							band="V",
    							)
    row = result.iloc[0]

    assert np.isclose(row["npix"], 18.367347, rtol=1e-6)
    assert np.isclose(row["stellar_rate_e_per_s"], 19304.78414, rtol=1e-5)
    assert np.isclose(row["sky_rate_e_per_s_per_pix"],  0.674545, rtol=1e-6)
    assert np.isclose(row["snr"], 2404.806674, rtol=1e-6)
    assert np.isclose(row["sigma_P_percent"], 0.014701946, rtol=1e-8)
