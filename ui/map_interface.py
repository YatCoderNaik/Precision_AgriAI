"""
Map Interface Module for Streamlit Integration

Provides interactive map components for the Precision AgriAI Streamlit application.
Handles coordinate capture, plot marker management, and GPS location services.
"""

import streamlit as st
from streamlit_folium import st_folium
from typing import Optional, Tuple, Dict, Any, List
import folium
from services.map_service import MapService
import logging

logger = logging.getLogger(__name__)


class MapInterface:
    """Interactive map interface for Streamlit"""
    
    def __init__(self, map_service: MapService):
        """
        Initialize MapInterface
        
        Args:
            map_service: MapService instance for geospatial operations
        """
        self.map_service = map_service
    
    def render_interactive_map(
        self,
        center_lat: float = 12.9716,
        center_lon: float = 77.5946,
        zoom: int = 10,
        plots: Optional[List[Dict[str, Any]]] = None,
        enable_click_capture: bool = True,
        enable_gps: bool = True,
        key: str = "map"
    ) -> Dict[str, Any]:
        """
        Render interactive map with coordinate capture
        
        Args:
            center_lat: Map center latitude (default: Bangalore)
            center_lon: Map center longitude
            zoom: Initial zoom level
            plots: Optional list of plots to display
            enable_click_capture: Enable click coordinate capture
            enable_gps: Enable GPS location button
            key: Unique key for Streamlit component
            
        Returns:
            Dictionary with map interaction data including clicked coordinates
        """
        # Create interactive map
        m = self.map_service.create_interactive_map(
            center_lat=center_lat,
            center_lon=center_lon,
            zoom=zoom,
            add_bhuvan_layer=True,
            enable_draw=False,
            enable_locate=enable_gps
        )
        
        # Add existing plots if provided
        if plots:
            self.map_service.add_clustered_markers(m, plots)
        
        # Render map with streamlit-folium
        map_data = st_folium(
            m,
            width=None,  # Use full width
            height=500,
            returned_objects=["last_clicked", "center", "zoom", "bounds"],
            key=key
        )
        
        return map_data
    
    def render_coordinate_capture_ui(
        self,
        map_data: Dict[str, Any],
        session_key: str = "captured_coordinates"
    ) -> Optional[Tuple[float, float]]:
        """
        Render UI for captured coordinates with validation
        
        Args:
            map_data: Map interaction data from st_folium
            session_key: Session state key for storing coordinates
            
        Returns:
            Tuple of (lat, lon) if valid coordinates captured, None otherwise
        """
        # Check if map was clicked
        if map_data and map_data.get("last_clicked"):
            clicked = map_data["last_clicked"]
            lat = clicked.get("lat")
            lon = clicked.get("lng")
            
            if lat is not None and lon is not None:
                # Store in session state
                st.session_state[session_key] = (lat, lon)
                
                # Display captured coordinates
                st.success(f"📍 Coordinates captured: {lat:.6f}, {lon:.6f}")
                
                # Validate coordinates
                validation = self.map_service.validate_coordinates(lat, lon)
                
                if validation.is_valid:
                    st.info(f"✅ Valid coordinates in {validation.state}, {validation.district}")
                    if validation.hobli_name:
                        st.info(f"📍 Hobli: {validation.hobli_name}")
                    return (lat, lon)
                else:
                    st.error(f"❌ Invalid coordinates: {validation.error}")
                    return None
        
        # Display previously captured coordinates if available
        if session_key in st.session_state and st.session_state[session_key] is not None:
            lat, lon = st.session_state[session_key]
            st.info(f"📍 Current coordinates: {lat:.6f}, {lon:.6f}")
            return (lat, lon)
        
        return None
    
    def render_gps_location_ui(
        self,
        session_key: str = "gps_coordinates"
    ) -> Optional[Tuple[float, float]]:
        """
        Render GPS location capture UI with privacy controls
        
        Args:
            session_key: Session state key for storing GPS coordinates
            
        Returns:
            Tuple of (lat, lon) if GPS location captured, None otherwise
        """
        st.subheader("📍 GPS Location Services")
        
        # Privacy notice
        with st.expander("🔒 Privacy Information", expanded=False):
            st.markdown("""
            **GPS Location Privacy:**
            - Location data is used only for plot registration
            - Your location is not stored permanently without your consent
            - You can clear location data at any time
            - Location access requires your explicit permission
            """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📍 Use My Location", type="primary", use_container_width=True):
                st.info("""
                **Browser GPS Access:**
                
                To use your current location:
                1. Click on the GPS button (🎯) on the map
                2. Allow location access when prompted by your browser
                3. The map will center on your location
                4. Click on the map to capture the exact coordinates
                
                Note: GPS accuracy depends on your device and environment.
                """)
        
        with col2:
            if st.button("🗑️ Clear Location", use_container_width=True):
                if session_key in st.session_state:
                    del st.session_state[session_key]
                    st.success("Location data cleared")
                else:
                    st.info("No location data to clear")
        
        # Display GPS coordinates if available
        if session_key in st.session_state and st.session_state[session_key] is not None:
            lat, lon = st.session_state[session_key]
            st.success(f"📍 GPS Location: {lat:.6f}, {lon:.6f}")
            return (lat, lon)
        
        return None
    
    def render_plot_marker_manager(
        self,
        plots: List[Dict[str, Any]],
        selected_plot_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Render plot marker management UI
        
        Args:
            plots: List of plot dictionaries
            selected_plot_id: Currently selected plot ID
            
        Returns:
            Selected plot ID or None
        """
        st.subheader("📌 Plot Markers")
        
        if not plots:
            st.info("No plots registered yet. Click on the map to add a plot.")
            return None
        
        # Display plot count by status
        status_counts = {}
        for plot in plots:
            status = plot.get("status", "active")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        cols = st.columns(len(status_counts))
        for idx, (status, count) in enumerate(status_counts.items()):
            with cols[idx]:
                st.metric(status.title(), count)
        
        # Plot selection
        plot_options = [f"{p['plot_id']} - {p.get('crop', 'Unknown')}" for p in plots]
        
        if plot_options:
            selected = st.selectbox(
                "Select Plot",
                options=plot_options,
                index=0 if selected_plot_id is None else next(
                    (i for i, p in enumerate(plots) if p['plot_id'] == selected_plot_id),
                    0
                ),
                help="Select a plot to view details or update"
            )
            
            if selected:
                plot_id = selected.split(" - ")[0]
                return plot_id
        
        return None
    
    def render_jurisdiction_heatmap(
        self,
        hobli_id: str,
        plots: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]],
        center_lat: float = 12.9716,
        center_lon: float = 77.5946,
        key: str = "jurisdiction_map"
    ) -> Dict[str, Any]:
        """
        Render jurisdiction heatmap for Extension Officers
        
        Args:
            hobli_id: Hobli jurisdiction identifier
            plots: List of plots in jurisdiction
            alerts: List of alerts in jurisdiction
            center_lat: Map center latitude
            center_lon: Map center longitude
            key: Unique key for Streamlit component
            
        Returns:
            Dictionary with map interaction data
        """
        # Create base map
        m = self.map_service.create_interactive_map(
            center_lat=center_lat,
            center_lon=center_lon,
            zoom=11,
            add_bhuvan_layer=True,
            enable_draw=False,
            enable_locate=False
        )
        
        # Add plot markers
        if plots:
            self.map_service.add_clustered_markers(m, plots, cluster_radius=60)
        
        # Add alert heatmap
        if alerts:
            self.map_service.add_heatmap_layer(m, alerts, radius=20, blur=30)
        
        # Render map
        map_data = st_folium(
            m,
            width=None,
            height=600,
            returned_objects=["center", "zoom", "bounds"],
            key=key
        )
        
        return map_data
    
    def render_coordinate_input_form(
        self,
        default_lat: Optional[float] = None,
        default_lon: Optional[float] = None
    ) -> Optional[Tuple[float, float]]:
        """
        Render manual coordinate input form
        
        Args:
            default_lat: Default latitude value
            default_lon: Default longitude value
            
        Returns:
            Tuple of (lat, lon) if valid input, None otherwise
        """
        st.subheader("⌨️ Manual Coordinate Entry")
        
        col1, col2 = st.columns(2)
        
        with col1:
            lat = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=default_lat if default_lat else 12.9716,
                step=0.0001,
                format="%.6f",
                help="Enter latitude with at least 4 decimal places"
            )
        
        with col2:
            lon = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=default_lon if default_lon else 77.5946,
                step=0.0001,
                format="%.6f",
                help="Enter longitude with at least 4 decimal places"
            )
        
        if st.button("Validate Coordinates", type="primary"):
            validation = self.map_service.validate_coordinates(lat, lon)
            
            if validation.is_valid:
                st.success(f"✅ Valid coordinates in {validation.state}, {validation.district}")
                if validation.hobli_name:
                    st.info(f"📍 Hobli: {validation.hobli_name}")
                return (lat, lon)
            else:
                st.error(f"❌ {validation.error}")
                return None
        
        return None
