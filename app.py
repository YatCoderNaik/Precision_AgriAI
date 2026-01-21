import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from fusion_engine import fuse_signals
from poc_recommender import interpret_and_recommend

# Page Config
st.set_page_config(page_title="Precision AgriAI: Analytics", layout="wide")

st.title("🌐 Precision AgriAI: Analytics Dashboard")
st.markdown("""
**POC-3: Semantic Interpretation & Data Fusion.** 
This system projects AlphaEarth latent embeddings onto structural metrics to derive semantic agronomist context.
""")

# Sidebar
st.sidebar.header("Plot Configuration")
lat = st.sidebar.number_input("Latitude", value=42.0660, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=-93.6330, format="%.6f")
crop = st.sidebar.selectbox("Target Crop", ["Corn", "Wheat", "Almonds", "Soybeans", "Rice"])
year = st.sidebar.slider("Data Year (Historical)", 2017, 2024, 2022)

if st.sidebar.button("🚀 Run Analysis"):
    with st.spinner("Executing Data Fusion & Structural Analysis..."):
        context, raw_data = fuse_signals(lat, lon, crop, year)
        
        # 1. AI Recommendation (Primary Output)
        st.subheader("🤖 AI Fused Recommendation")
        rec = interpret_and_recommend(raw_data['AlphaEarth'], crop, f"Plot ({lat}, {lon})")
        
        # Enrich recommendation with structural tokens
        if raw_data.get('AlphaEarth_Summary'):
            tokens_str = ", ".join(raw_data['AlphaEarth_Summary']['tokens'])
            final_rec = f"### [AI FUSED REPORT: {crop}]\n\n"
            final_rec += f"**Structural Interpretation**: {tokens_str}.\n\n"
            final_rec += rec.split(']', 1)[-1] if ']' in rec else rec
            st.success(final_rec)
        else:
            st.success(rec)

        st.divider()

        # 2. Data Sources (Expanders for Stability)
        with st.expander("🛰️ AlphaEarth Structural Analysis", expanded=True):
            if raw_data.get('AlphaEarth'):
                c1, c2 = st.columns([1, 2])
                with c1:
                    ae_summary = raw_data['AlphaEarth_Summary']
                    st.metric("Mean Signal", ae_summary['mean'])
                    st.metric("Variance", ae_summary['variance'])
                    st.metric("Structural Flux", ae_summary['flux'])
                    st.markdown("**Decoded Tokens:**")
                    for t in ae_summary['tokens']:
                        st.markdown(f"- `{t}`")
                with c2:
                    st.line_chart(raw_data['AlphaEarth'], height=250)
            else:
                st.warning("AlphaEarth data unavailable.")

        with st.expander("🛰️ Sentinel-2 & MODIS"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Sentinel-2 (Copernicus)**")
                st.json(raw_data['Sentinel2'])
            with c2:
                st.markdown("**MODIS Vegetation**")
                st.json(raw_data['MODIS'])

        with st.expander("🧪 Soil & Weather"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**SoilProfile (SoilGrid)**")
                st.json(raw_data['Soil'])
            with c2:
                st.markdown("**Local Weather (Open-Meteo)**")
                st.json(raw_data['Weather'])

        with st.expander("📝 Fused Signal Context (Raw Prompt Input)"):
            st.code(context, language="markdown")

st.divider()
st.caption("Precision AgriAI POC | Environment: Conda 'agriai' | Sources: AlphaEarth, GEE, ISRIC, Open-Meteo")
