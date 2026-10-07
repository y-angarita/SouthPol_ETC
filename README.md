# SouthPol Exposure-Time Calculator

A Python-based exposure-time calculator (ETC) for **SouthPol** optical polarimetric observations. The routine is based on the ETC developed by Prof. Antonio Mario Magalhaes (Copyright April 2026).

**Live app:** https://y-angarita-southpol-etc-app-tegc7o.streamlit.app/

The calculator estimates:

- Stellar photoelectron rate
- Sky-background rate per pixel
- Total detected stellar electrons
- Signal-to-noise ratio (SNR)
- Polarimetric precision, $$\sigma_P$$
- Gaussian-PSF peak pixel level
- Peak object-plus-sky electrons and ADU
- Detector full-well and linearity fractions
- Warnings when an individual exposure may be close to or above detector limits

The numerical SNR and polarimetric-precision calculation is based on the supplied SouthPol spreadsheet for half-wave-plate polarimetry. The code is intended to make that calculation reproducible, testable, and usable interactively in notebooks or through a web interface.

> **Important:** This tool is an observing-planning calculator. Its predictions depend on throughput, sky brightness, seeing, detector gain, full well, linearity, and calibration assumptions. Validate the adopted parameters against the current instrument configuration before operational use.

---

## Features

- Supports scalar values or NumPy arrays for magnitude, exposure time, and seeing.
- Returns a `pandas.DataFrame`, making it convenient to inspect, export, plot, or use in notebooks.
- Computes the SouthPol SNR and sigma_P.
- Estimates peak counts using a 2D circular Gaussian PSF.
- Evaluates saturation for an **individual exposure**, rather than only for the total observing time.
- Includes plotting support for:
  - SNR vs. exposure time
  - SNR vs. magnitude
  - Peak detector level vs. exposure time
- Can be used as the numerical backend for a Streamlit web application.

---

## Repository layout

```text
southpol_etc/
├── etc_model.py          # Scientific calculation and instrument model
├── app.py                # Optional Streamlit web interface
├── requirements.txt      # Required Python packages
├── README.md             # This file
└── tests/
    └── test_model.py     # Regression tests against spreadsheet values
```

---

## Installation

### 1. Clone or download the project

```bash
git clone <your-repository-url>

cd SouthPol_ETC
```

### 2. Create a Python environment

Using `venv`:

```bash
python -m venv southpol-etc-env
source southpol-etc-env/bin/activate
```

On Windows:

```bash
southpol-etc-env\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

A minimal `requirements.txt` is:

```text
numpy
pandas
matplotlib
streamlit
pytest
fastapi
uvicorn[standard]
```

---

## Quick start

Import an instrument configuration and run one ETC calculation:

```python
from etc_model import SOUTHPOL_FILTERS, calculate_southpol

result = calculate_southpol(magnitude=12.0,
							exposure_time=300.0,
							seeing=1.2,
							instrument=SOUTHPOL_FILTERS["V"],
							band="V",
							n_exposures=1,
							)

print(result)
```

Extract the single result row:

```python
row = result.iloc

print(f"SNR, one image: {row['snr']:.1f}")
print(f"SNR, all half-wave plate rotations combined: {row['snr_combined']:.1f}")
print(f"Sigma P: {row['sigma_P_percent']:.4f} %")
print(f"Peak detector level: {row['peak_total_electrons']:.0f} e- / pixel")
print(f"Detector warning: {row['saturation_warning']}")
```

---

## Example formatted output

```python
import numpy as np


def print_etc_summary(result):
    """Print a readable summary for a single-row SouthPol ETC result."""
    if len(result) != 1:
        raise ValueError("print_etc_summary expects a DataFrame containing one row.")

    row = result.iloc

    print("SouthPol Exposure-Time Calculator")
    print("=" * 52)

    print("\nObservation")
    print(f"Band:                      {row['band']}")
    print(f"Stellar magnitude:         {row['magnitude']:.2f} mag")
    print(f"Exposure time:             {row['exposure_time_s']:.1f} s")
    print(f"Seeing:                    {row['seeing_arcsec']:.2f} arcsec")
    print(f"Number of exposures:       {int(row['n_exposures'])}")

    print("\nSignal and background")
    print(f"Aperture size:             {row['npix']:.2f} pixel")
    print(f"Stellar count rate:        {row['stellar_rate_e_per_s']:,.2f} e- s^-1")
    print(f"Sky count rate:            {row['sky_rate_e_per_s_per_pix']:,.4f} e- s^-1 pixel^-1")
    print(f"Integrated stellar signal: {row['object_electrons']:,.0f} e-")

    print("\nPeak level per exposure")
    print(f"Peak stellar signal:       {row['peak_stellar_electrons']:,.0f} e- pixel^-1")
    print(f"Peak object + sky:         {row['peak_total_electrons']:,.0f} e- pixel^-1")

    if np.isfinite(row["peak_total_adu"]):
        print(f"Peak object + sky:         {row['peak_total_adu']:,.0f} ADU pixel^-1")

    print("\nPolarimetric performance")
    print(f"SNR, one image:            {row['snr']:,.1f}")
    print(f"SNR, all HWPP combined:    {row['snr_combined']:,.1f}")
    print(f"Polarization precision:    {row['sigma_P_percent']:.4f} %")

    print("\nDetector safety")

    if np.isfinite(row["full_well_fraction"]):
        print(f"Full-well fraction:        {row['full_well_fraction']:.1f}")

    if np.isfinite(row["linearity_fraction"]):
        print(f"Linearity-limit fraction:  {row['linearity_fraction']:.1f}")

    print(f"Detector status:           {row['saturation_warning']}")
    print("=" * 52)
```

Use it as follows:

```python
print_etc_summary(result)
```

---

## Input parameters

### Observation parameters

| Parameter | Description | Unit |
|---|---|---|
| `magnitude` | Apparent stellar magnitude in the selected band | mag |
| `exposure_time` | Duration of one individual detector exposure | s |
| `seeing` | FWHM of the point-spread function | arcsec |
| `band` | Filter label, such as `V` | — |
| `n_exposures` | Number of exposures to combine | — |
| `gain_e_per_adu` | Detector conversion gain | e^{-} ADU^{-1} |

### Instrument parameters

| Parameter | Description | Unit |
|---|---|---|
| `throughput` | Total system throughput or efficiency Q | dimensionless |
| `pixel_scale` | Plate scale | arcsec pixel^{-1} |
| `read_noise` | RMS readout noise per pixel | e^{-} pixel^{-1} |
| `sky_mag` | Sky brightness | mag arcsec^{-2} |
| `telescope_diameter` | Effective telescope diameter used in the model | cm |
| `filter_width` | Effective filter bandwidth | Angstrom |
| `n_plate` | Number of polarimetric plate positions | — |
| `full_well_e` | Approximate detector full-well capacity | e^{-} pixel^{-1} |
| `linear_limit_adu` | Detector linearity limit | ADU pixel^{-1} |

---

## SouthPol calculation

The model uses the same equations as the original SouthPol ETC from Prof. Antonio Mario Magalhaes (Copyright April 2026); See [notes PDF](https://github.com/y-angarita/SouthPol_ETC/blob/main/SouthPol_ETC.pdf).

### Number of pixels in the stellar aperture

The spreadsheet defines the number of pixels covered by the source as:

$$N_{\rm pix}=\left(\frac{\mathrm{seeing}}{\mathrm{pixel\ scale}}\right)^2.$$

### Stellar electron rate

The stellar count rate is:

$$
\frac{dN_\star}{dt}=Q\cdot10^{-0.4(m+39.39)}\cdot\frac{\pi}{4}\cdot D^2\cdot\Delta\lambda\cdot\frac{10^7}{3.6\times10^{-12}}\cdot\frac{1}{2}.$$

where:

- $$Q$$ is the total throughput;
- $$m$$ is stellar magnitude;
- $$D$$ is effective telescope diameter in cm;
- $$\Delta\lambda$$ is filter bandwidth in Angstrom;
- the factor $$1/2$$ is retained from the original SouthPol spreadsheet.

### Sky electron rate per pixel

$$\frac{dN_{\rm sky}}{dt\,{\rm pix}}=Q\cdot10^{-0.4(\mu_{\rm sky}+38.52)}\cdot\frac{\pi}{4}\cdot D^2\cdot\Delta\lambda\cdot\frac{10^7}{3.6\times10^{-12}}\cdot s^2,$$

where $$\mu_{\rm sky}$$ is the sky brightness in mag arcsec$$^{-2}$$, and $$s$$ is the pixel scale in arcsec pixel$$^{-1}$$.

### Signal-to-noise ratio

The SNR expression implemented from the spreadsheet is:

$$SNR=\frac{\left(dN_\star/dt\right)t}{\sqrt{\left(dN_\star/dt\right)t+2N_{\rm pix}\left[
\left(dN_{\rm sky}/dt/{\rm pix}\right)t+R^2\right]}}.$$

Here:

- $$t$$ is the individual exposure time;
- $$R$$ is read noise in e$$^{-}$$ pixel$$^{-1}$$;
- the factor of 2 is retained exactly from the original spreadsheet model.

### Polarization precision

For $$N_{\rm plate}$$ plate positions:

$$\sigma_P[\\%]=\frac{100}{\sqrt{N_{\rm plate}} SNR}.$$

For the default eight-position configuration:

$$\sigma_P[\\%]=\frac{100}{\sqrt{8} SNR}.$$

---

## Peak-count calculation

The original spreadsheet calculates integrated source signal, SNR, and $$\sigma_P$$, but it does not include a central-pixel peak calculation.

This ETC additionally estimates the peak count level from a circular two-dimensional Gaussian PSF.

The Gaussian width is:

$$\sigma_{\rm PSF}=\frac{\mathrm{FWHM}}{2.355}.$$

The fraction of the total stellar flux expected in the central pixel is approximated by:

$$f_{\rm peak}=\frac{s^2}{2\pi\sigma_{\rm PSF}^2},$$

where $$s$$ is the pixel scale in arcsec pixel$$^{-1}$$.

Thus:

$$N_{\rm peak,\star}=N_{\rm object}\cdot f_{\rm peak}.$$

The predicted peak object-plus-sky signal is:

$$N_{\rm peak,total}=N_{\rm peak,\star}+N_{\rm sky,pixel}.$$

If the detector gain is known:

$$N_{\rm peak,ADU}=\frac{N_{\rm peak,total}}{\mathrm{gain}}.$$

### Important limitations

The central-pixel calculation is an approximation. It assumes:

- A circular Gaussian PSF.
- Perfect centering of the star on the brightest pixel.
- Spatially uniform sky background.
- No charge diffusion, blooming, or detector non-linearity.
- No atmospheric scintillation, guiding drift, focus variation, or PSF asymmetry.

The predicted peak is therefore most useful as a conservative planning diagnostic. For saturation protection, evaluate the calculation using the best plausible seeing, rather than only median seeing.

---

## Detector warnings

The ETC checks two detector limits when they are configured:

1. **Full-well limit**
   - Defined in e$$^{-}$$ pixel$$^{-1}$$.
   - A warning is issued when the estimated peak object-plus-sky electrons approach or exceed the limit.

2. **Linearity limit**
   - Defined in ADU pixel$$^{-1}$$.
   - A warning is issued when the peak ADU approaches or exceeds the configured limit.

The default warning threshold is 90% of the selected limit:

$$f_{\rm warning} = 0.90.$$

A saturation warning refers to **one individual frame**. If a total observing sequence is divided into shorter exposures, the SNR of the combined sequence may be similar, but the peak level and saturation risk per frame are lower.

> Do not consider the saturation configuration operational until `gain_e_per_adu`, `full_well_e`, and `linear_limit_adu` have been replaced with verified SouthPol detector values.

---

## Filter configuration

Filter-dependent parameters are stored in `SOUTHPOL_FILTERS`.

Example:

```python
from etc_model import Instrument

southpol_v = Instrument(name="SouthPol V",
						throughput=0.81,
						pixel_scale=0.3713,
						read_noise=5.0,
						sky_mag=22.0,
						telescope_diameter=65.0,
						filter_width=786.0,
						n_plate=8,
						stellar_factor=0.5,

						# Replace with measured detector properties.
						gain_e_per_adu=0.50,
						full_well_e=100_000.0,
						linear_limit_adu=50_000.0,
						)
```

To support another filter, add a separate configuration:

```python
SOUTHPOL_FILTERS["R"] = Instrument(name="SouthPol R",
								   throughput=0.XX,
								   pixel_scale=0.3713,
								   read_noise=5.0,
								   sky_mag=XX.XX,
								   telescope_diameter=65.0,
								   filter_width=XXX.X,
								   n_plate=8,
  								   stellar_factor=0.5,
								   gain_e_per_adu=0.XX,
								   full_well_e=XXXXX.0,
								   linear_limit_adu=XXXXX.0,
								   )
```

The following values should be determined independently for each filter and observing mode:

- Total optical throughput
- Filter effective bandwidth
- Representative sky brightness
- Atmospheric extinction assumptions
- Detector gain
- Detector full-well capacity
- Detector linearity limit

---

## Plotting examples

### SNR versus exposure time

```python
import numpy as np
import matplotlib.pyplot as plt

from etc_model import SOUTHPOL_FILTERS, calculate_southpol

instrument = SOUTHPOL_FILTERS["V"]
times = np.geomspace(1.0, 3600.0, 300)

curve = calculate_southpol(magnitude=15.0,
						   exposure_time=times,
						   seeing=1.2,
						   instrument=instrument,
						   band="V",
						   )

plt.figure(figsize=(7, 5))
plt.plot(curve["exposure_time_s"], curve["snr"])
plt.xscale("log")
plt.yscale("log")
plt.xlabel("Individual exposure time [s]")
plt.ylabel("SNR")
plt.title("SouthPol SNR versus exposure time")
plt.grid(alpha=0.3, which="both")
plt.show()
```

### SNR versus stellar magnitude

```python
magnitudes = np.linspace(8.0, 22.0, 300)

curve = calculate_southpol(magnitude=magnitudes,
						   exposure_time=300.0,
						   seeing=1.2,
						   instrument=instrument,
						   band="V",
						   )

plt.figure(figsize=(7, 5))
plt.plot(curve["magnitude"], curve["snr"])
plt.yscale("log")
plt.xlabel("V magnitude [mag]")
plt.ylabel("SNR")
plt.title("SouthPol SNR versus magnitude")
plt.grid(alpha=0.3, which="both")
plt.show()
```

### Peak level versus exposure time

```python
curve = calculate_southpol(magnitude=15.0,
						   exposure_time=times,
						   seeing=1.2,
						   instrument=instrument,
						   band="V",
						   )

plt.figure(figsize=(7, 5))

plt.plot(curve["exposure_time_s"], curve["peak_total_electrons"], 
		 label="Peak object + sky")

if instrument.full_well_e is not None:
    plt.axhline(instrument.full_well_e, color="red", linestyle="--",
    			label="Configured full well")

plt.xscale("log")
plt.yscale("log")
plt.xlabel("Individual exposure time [s]")
plt.ylabel("Peak signal [e- pixel$^{-1}$]")
plt.title("SouthPol peak level versus exposure time")
plt.grid(alpha=0.3, which="both")
plt.legend()
plt.show()
```

---

## Validation

The numerical model should be tested against known values from the original SouthPol spreadsheet.

For the default V-band configuration, a source with:

```text
Magnitude:      V = 12.0 mag
Exposure time:  300 s
Seeing:         1.2 arcsec
```

should reproduce approximately:

| Quantity | Expected value |
|---|---:|
| $$N_{\rm pix}$$ | 10.44509979 |
| Stellar rate | 8156.271299 e$$^{-}$$ s$$^{-1}$$ |
| Sky rate per pixel | 0.501154411 e$$^{-}$$ s$$^{-1}$$ pixel$$^{-1}$$ |
| SNR | 1563.081522 |
| $$\sigma_P$$ | 0.022618999 % |

Run the tests with:

```bash
pytest -q
```

Example regression test:

```python
import numpy as np

from etc_model import SOUTHPOL_FILTERS, calculate_southpol


def test_v12_300s_spreadsheet_reference():
    result = calculate_southpol(magnitude=12.0,
    							exposure_time=300.0,
    							seeing=1.2,
    							instrument=SOUTHPOL_FILTERS["V"],
    							band="V",
    							)
    row = result.iloc
    
    assert np.isclose(row["npix"], 18.367347, rtol=1e-6)
    assert np.isclose(row["stellar_rate_e_per_s"], 19304.78414, rtol=1e-6)
    assert np.isclose(row["sky_rate_e_per_s_per_pix"],  0.674545, rtol=1e-6)
    assert np.isclose(row["snr"], 2404.806674, rtol=1e-6)
    assert np.isclose(row["sigma_P_percent"], 0.014701946, rtol=1e-8)
```

---

## Streamlit web interface

If `app.py` is included, start the browser-based ETC locally with:

```bash
streamlit run app.py
```

The app should provide controls for:

- Filter/band
- Stellar magnitude
- Individual exposure time
- Number of exposures
- Seeing
- Sky brightness
- Detector settings

The displayed results should include:

- SNR per sequence
- Combined SNR
- $$\sigma_P$$ per sequence
- Combined $$\sigma_P$$
- Integrated source electrons
- Peak source electrons per pixel
- Peak object-plus-sky electrons per pixel
- Peak ADU per pixel
- Full-well fraction
- Detector warning
- SNR, magnitude, and peak-count plots

---

## Units

| Quantity | Unit |
|---|---|
| Magnitude | mag |
| Sky brightness | mag arcsec$$^{-2}$$ |
| Exposure time | s |
| Seeing FWHM | arcsec |
| Pixel scale | arcsec pixel$$^{-1}$$ |
| Stellar count rate | e$$^{-}$$ s$$^{-1}$$ |
| Sky count rate | e$$^{-}$$ s$$^{-1}$$ pixel$$^{-1}$$ |
| Integrated object signal | e$$^{-}$$ |
| Peak signal | e$$^{-}$$ pixel$$^{-1}$$ |
| Peak counts | ADU pixel$$^{-1}$$ |
| Gain | e$$^{-}$$ ADU$$^{-1}$$ |
| Polarization precision | % |
| SNR | dimensionless |

---

## Known limitations

- The model currently uses a Gaussian approximation for the peak pixel.
- The reported sky brightness represents a selected observing condition, not an all-sky or time-dependent sky model.
- Airmass dependence is not yet explicitly included unless absorbed into the selected throughput.
- Galactic extinction is not included.
- Moon phase, Moon distance, twilight, cloud extinction, and scattered light are not included.
- Atmospheric transparency variations are not included.
- Cosmic-ray incidence and overheads are not included.
- The source is assumed to be point-like. Extended sources require surface-brightness and aperture treatment.
- The polarimetric model follows the supplied workbook assumptions and should be reviewed if the observing sequence, modulation scheme, or reduction strategy differs.
- Full-well, gain, and linearity values must be verified for the actual detector and readout mode.

---

## Recommended future developments

- Add verified SouthPol detector gain, full-well capacity, linearity curves, and readout modes.
- Add all available filters using measured effective throughput curves.
- Include airmass-dependent extinction.
- Include dark current if non-negligible.
- Include Moon and sky-brightness models.
- Permit user-selected aperture radii or encircled-energy fractions.
- Add a point-source versus extended-source option.
- Add an inverse ETC mode:
  - Required exposure time for a target SNR.
  - Required exposure time for a target $$\sigma_P$$.
  - Limiting magnitude for a specified SNR and exposure time.
- Add CSV export of results and figures.
- Add a version identifier and record all instrument parameters used for each calculation.
- Add automated tests for all spreadsheet reference cases.

---

## Citation and acknowledgement

If this calculator is used in observing proposals, exposure planning, publications, or technical documentation, cite the relevant SouthPol instrument documentation and state the ETC version and the parameter set used.

---

## License

Add the license appropriate to the project before distributing the code publicly.

For an internal-only project, consider adding:

```text
This software is intended for internal SouthPol observing preparation.
Redistribution requires permission from the project maintainers.
```

---

## Contact

For questions, calibration updates, or detector-parameter corrections, contact the SouthPol ETC maintainers.
