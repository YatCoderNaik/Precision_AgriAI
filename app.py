import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from poc_recommender import init_earth_engine, get_alpha_earth_embedding, interpret_and_recommend

# Page Config
st.set_page_config(page_title="AlphaEarth Agri Recommendation", layout="wide")

st.title("🌱 Precision AgriAI: AlphaEarth-Aware Recommendations")
st.markdown("""
This POC demonstrates how **AlphaEarth Satellite Embeddings** can informs AI-driven crop recommendations.
Enter coordinates below to fetch the latent signature of a plot.
""")

# Sidebar for Inputs
st.sidebar.header("Plot Configuration")
lat = st.sidebar.number_input("Latitude", value=42.0660, format="%.6f")
lon = st.sidebar.number_input("Longitude", value=-93.6330, format="%.6f")
crop = st.sidebar.selectbox("Crop Type", ["Corn", "Wheat", "Almonds", "Soybeans", "Rice"])
year = st.sidebar.slider("Data Year", 2017, 2024, 2022)

if st.sidebar.button("Generate Recommendation"):
    with st.spinner("Initializing Earth Engine and Fetching Embeddings..."):
        # Initialize (safe to call multiple times if handled in poc_recommender)
        init_earth_engine()
        
        # Fetch Data
        vector = get_alpha_earth_embedding(lat, lon, year=year)
        
        if vector:
            st.success(f"Successfully retrieved 64-dimensional embedding for ({lat}, {lon})")
            
            # Create Columns for Layout
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📊 AlphaEarth Signature (Latent Vector)")
                # Visualization of Embeddings
                df_vector = pd.DataFrame({
                    'Dimension': [f"D{i:02d}" for i in range(64)],
                    'Value': vector
                })
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_vector['Dimension'], 
                    y=df_vector['Value'],
                    mode='lines+markers',
                    name='Embedding Signal',
                    line=dict(color='#2E7D32', width=2),
                    marker=dict(size=6, color='#1B5E20')
                ))
                
                fig.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=400,
                    xaxis_title="Latent Dimensions (64-dim)",
                    yaxis_title="Signal Strength",
                    template="plotly_white"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.info("The chart above shows the 64-dimensional 'signature' of this 10m pixel. These vectors encode annual temporal dynamics, soil moisture, and biomass.")

            with col2:
                st.subheader("🤖 AI Recommendation")
                # Generate Recommendation
                recommendation = interpret_and_recommend(vector, crop, f"Plot at {lat}, {lon}")
                st.markdown(recommendation)
                
                with st.expander("View Raw Vector Data"):
                    st.write(vector)
                    
        else:
            st.error("Failed to retrieve embeddings. Ensure the location is on land and within the AlphaEarth coverage area.")

# Footer
st.divider()
st.caption("Precision AgriAI POC | Powered by AlphaEarth Foundations & Google Earth Engine")
