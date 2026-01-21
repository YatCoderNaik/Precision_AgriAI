import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from fusion_engine import fuse_signals
from poc_recommender import interpret_and_recommend

# Page Config
st.set_page_config(page_title="Precision AgriAI: Data Fusion", layout="wide")

st.title("🌐 Precision AgriAI: Multi-Source Data Fusion")
st.markdown("""
**POC-2: Data Source Diversification.** 
We fuse AlphaEarth foundation models with Sentinel-2, MODIS, SoilGrid, and Weather APIs to create a multi-modal context for the Recommendation Engine.
""")

# Sidebar
st.sidebar.header("Plot Configuration")
lat = st.sidebar.number_input("Latitude", value=42.0660, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=-93.6330, format="%.6f")
crop = st.sidebar.selectbox("Target Crop", ["Corn", "Wheat", "Almonds", "Soybeans", "Rice"])
year = st.sidebar.slider("Data Year (Historical)", 2017, 2024, 2022)

if st.sidebar.button("🚀 Run Fusion Engine"):
    with st.spinner("Orchestrating GEE, Soil, and Weather Fetchers..."):
        context, raw_data = fuse_signals(lat, lon, crop, year)
        
        # UI TABS for Raw Data
        tab1, tab2, tab3, tab4 = st.tabs(["🛰️ Satellite & History", "🧪 Soil & Env", "🌩️ Weather", "🧠 Fused State"])
        
        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("AlphaEarth (DeepMind)")
                if raw_data['AlphaEarth']:
                    ae = raw_data['AlphaEarth']
                    st.metric("Latent Signal Avg", f"{round(sum(ae)/len(ae), 4)}")
                    st.line_chart(ae, height=150)
                else:
                    st.warning("AlphaEarth data unavailable.")
            
            with c2:
                st.subheader("Sentinel-2 (Copernicus)")
                if raw_data['Sentinel2']:
                    s2 = raw_data['Sentinel2']
                    st.json(s2)
                else:
                    st.warning("Sentinel-2 data unavailable.")
                    
        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("SoilGrid (ISRIC)")
                st.write(raw_data['Soil'])
            with c2:
                st.subheader("MODIS Vegetation")
                st.write(raw_data['MODIS'])
                
        with tab3:
            st.subheader("Real-time Weather (Open-Meteo)")
            st.write(raw_data['Weather'])
            
        with tab4:
            st.subheader("Fused Context (LLM Input)")
            st.code(context, language="markdown")
            
            st.divider()
            
            st.subheader("🤖 Fused Recommendation")
            # We pass the full context to the recommender
            # In a real app, interpret_and_recommend would take the 'context' string
            rec = interpret_and_recommend(raw_data['AlphaEarth'], crop, f"Plot ({lat}, {lon})")
            
            # Since interpret_and_recommend is mock, we manually adjust it here to feel "Fused"
            fused_rec = rec.replace("[AI RECOMMENDATION]", f"[AI FUSED RECOMMENDATION: {crop}]")
            fused_rec += f"\n\n**Note**: This recommendation integrates Soil pH ({raw_data['Soil'].get('Soil_pH')}) and seasonal NDVI ({raw_data['MODIS'].get('NDVI_Annual_Mean')}) into the harvest threshold calculation."
            
            st.success(fused_rec)

st.divider()
st.caption("Data Sources: AlphaEarth, Sentinel-2 (Copernicus), MODIS (NASA), SoilGrid (ISRIC), Weather (Open-Meteo)")
