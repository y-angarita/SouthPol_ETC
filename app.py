import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

from etc_model import SOUTHPOL_FILTERS, calculate_exposure


st.set_page_config(page_title="SouthPol ETC",
                   page_icon="🔭", layout="wide")

st.title("SouthPol Exposure-Time Calculator")
st.caption("This is an adaptation of the SouthPol exposure-time calculator (ETC) developed by Prof. Antonio Mario Magalhaes (Copyright: April 2026) into a Python routine. The original ETC calculates the compact photon-counting model for the SouthPol half-wave plate polarimeter. The f/5 focal reducer has been assumed.")

with st.sidebar:
    st.header("Observation")

    band = st.selectbox("Band / filter", options=list(SOUTHPOL_FILTERS), index=0)

    magnitude = st.number_input(f"{band} magnitude", min_value=-5.0, max_value=35.0,
                                value=12.0, step=0.1)

    exposure_time = st.number_input("Individual exposure time [s]", min_value=0.1,
                                    max_value=7200.0, value=300.0, step=10.0)

    n_exposures = st.number_input("Number of exposures", min_value=1, max_value=1000,
                                  value=1, step=1)

    seeing = st.number_input("Seeing FWHM [arcsec]", min_value=0.1, max_value=10.0,
                             value=1.2, step=0.1)

    st.header("Sky and detector")

    instrument = SOUTHPOL_FILTERS[band]

    sky_mag = st.number_input("Sky brightness [mag arcsec⁻²]", min_value=10.0,
                              max_value=30.0, value=float(instrument.sky_mag),
                              step=0.05)
    gain_e_per_adu = st.number_input("Gain [e⁻ adu⁻¹]", min_value=0.0, max_value=10.0,
    								 value=float(instrument.gain_e_per_adu), step=0.01)
    						
    st.caption(f"Pixel scale: {instrument.pixel_scale:.4f} arcsec pixel⁻¹")
    st.caption(f"Read noise: {instrument.read_noise:.2f} e⁻ pixel⁻¹")

result = calculate_exposure(magnitude=magnitude,
                            exposure_time=exposure_time,
                            seeing=seeing,
                            instrument=instrument,
                            band=band,
                            n_exposures=n_exposures,
                           )

row = result.iloc[0]

st.header("Result")

warning = row["saturation_warning"]

if warning == "OK":
    st.success("Detector check: OK")
elif "SATURATION" in warning:
    st.error(warning)
else:
    st.warning(warning)

metric_1, metric_2, metric_3, metric_4 = st.columns(4)

metric_1.metric("S/N per sequence", f"{row['snr']:,.1f}")
metric_2.metric("σP per sequence", f"{row['sigma_P_percent']:.4f} %")
metric_3.metric("Peak level", f"{row['peak_total_electrons']:,.0f} e⁻ pixel⁻¹")

if np.isfinite(row["peak_total_adu"]):
    metric_4.metric("Peak counts", f"{row['peak_total_adu']:,.0f} ADU pixel⁻¹")
else:
    metric_4.metric("Peak counts", "Gain not set")

st.subheader("Observation summary")

summary = {"Band": row["band"],
           "Stellar magnitude": f"{row['magnitude']:.2f} mag",
           "Exposure time": f"{row['exposure_time_s']:.1f} s",
           # "Number of exposures": f"{int(row['n_exposures'])}",
           "Seeing": f"{row['seeing_arcsec']:.2f} arcsec",
           "Aperture size": f"{row['npix']:.2f} pixel",
           "Stellar count rate": f"{row['stellar_rate_e_per_s']:,.2f} e⁻ s⁻¹",
           "Sky count rate": f"{row['sky_rate_e_per_s_per_pix']:,.4f} e⁻ s⁻¹ pixel⁻¹",
           "Integrated stellar signal": f"{row['stellar_electrons']:,.0f} e⁻",
           "Peak stellar signal": f"{row['peak_stellar_electrons']:,.0f} e⁻ pixel⁻¹",
           "Peak object + sky": f"{row['peak_total_electrons']:,.0f} e⁻ pixel⁻¹",
           "Full-well fraction (i.e., minimum number of exposures)": f"{row['full_well_fraction']:.1f} ({row['full_well_fraction']:.0f})",
           "SNR one image": f"{row['snr']:,.1f}",
           "SNR, all HWPPs combined": f"{row['snr_combined']:,.1f}",
           "σP": f"{row['sigma_P_percent']:.4f} %",
           "Detector status": row["saturation_warning"],
}

st.dataframe({"Quantity": list(summary.keys()),
              "Value": list(summary.values()),
              }, hide_index=True, use_container_width=True,
            )

st.header("Performance curves")

plot_col_1, plot_col_2, plot_col_3 = st.columns(3)

exposure_grid = np.geomspace(1.0, 3600.0, 300)
magnitude_grid = np.linspace(8.0, 22.0, 300)

with plot_col_1:
    curve = calculate_exposure(magnitude=magnitude,
                               exposure_time=exposure_grid,
                               seeing=seeing,
                               instrument=instrument,
                               band=band,
                               )

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(curve["exposure_time_s"], curve["snr"], color="tab:blue", lw=2)
    ax.axvline(exposure_time, color="black", ls="--", alpha=0.7)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Individual exposure time [s]")
    ax.set_ylabel("S/N")
    ax.set_title("S/N versus exposure time")
    ax.grid(alpha=0.3, which="both")
    st.pyplot(fig)

with plot_col_2:
    curve = calculate_exposure(magnitude=magnitude_grid,
                               exposure_time=exposure_time,
                               seeing=seeing,
                               instrument=instrument,
                               band=band,
                               )

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(curve["magnitude"], curve["snr"], color="tab:green", lw=2)
    ax.axvline(magnitude, color="black", ls="--", alpha=0.7)
    ax.set_yscale("log")
    ax.set_xlabel(f"{band} magnitude [mag]")
    ax.set_ylabel("S/N")
    ax.set_title("S/N versus magnitude")
    ax.grid(alpha=0.3, which="both")
    st.pyplot(fig)

with plot_col_3:
    curve = calculate_exposure(magnitude=magnitude,
                               exposure_time=exposure_grid,
                               seeing=seeing,
                               instrument=instrument,
                               band=band,
                               )

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(curve["exposure_time_s"], curve["peak_total_electrons"], color="tab:red", lw=2)

    if instrument.full_well_e is not None:
        ax.axhline(instrument.full_well_e, color="black", ls="--", label="Full-well limit")

    ax.axvline(exposure_time, color="black", ls=":", alpha=0.7)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Individual exposure time [s]")
    ax.set_ylabel("Peak object + sky [e⁻ pixel⁻¹]")
    ax.set_title("Peak level versus exposure time")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    st.pyplot(fig)

st.divider()

st.subheader("Model notes")
st.markdown("""
- The S/N and (sigma_P) calculations reproduce the spreadsheet model.
- Peak counts are estimated from a Gaussian PSF using the input seeing.
- Saturation is assessed for each individual frame, not the total time across multiple frames.
- Detector gain, full well, and linearity limits must be replaced by verified SouthPol detector values before operational use.
"""
)
