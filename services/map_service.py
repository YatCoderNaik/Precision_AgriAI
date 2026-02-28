"""
MapService - ISRO Bhuvan Integration

Handles all mapping and geospatial operations including:
- ISRO Bhuvan WMS integration (LISS III/Vector layers)
- Coordinate validation and normalization
- Hobli boundary detection from coordinates
- GPS location services integration
"""

from typing import Tuple, Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging
import httpx
from urllib.parse import urlencode
import folium
from shapely.geometry import Point
from shapely.ops import nearest_points
import geopandas as gpd
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Get configuration
settings = get_settings()


class CoordinateValidationResult(BaseModel):
    """Result of coordinate validation"""
    is_valid: bool
    error: Optional[str] = None
    normalized_coordinates: Optional[Tuple[float, float]] = None
    hobli_id: Optional[str] = None
    hobli_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None


class HobliInfo(BaseModel):
    """Hobli administrative information"""
    hobli_id: str
    hobli_name: str
    district: str
    state: str
    coordinates: Tuple[float, float]


class WMSCapabilities(BaseModel):
    """WMS service capabilities"""
    service_title: str
    service_abstract: Optional[str] = None
    available_layers: List[str]
    supported_formats: List[str]
    supported_crs: List[str]


class WMSLayerInfo(BaseModel):
    """WMS layer information"""
    name: str
    title: str
    abstract: Optional[str] = None
    bbox: Optional[Dict[str, float]] = None
    crs: List[str]


class MapService:
    """Service for ISRO Bhuvan integration and geospatial operations"""
    
    def __init__(self):
        """Initialize MapService with Bhuvan configuration"""
        self.bhuvan_base_url = settings.map_service.bhuvan_base_url
        self.default_layer = settings.map_service.bhuvan_default_layer
        self.india_lat_bounds = settings.map_service.india_lat_bounds
        self.india_lon_bounds = settings.map_service.india_lon_bounds
        self.coordinate_precision = settings.map_service.coordinate_precision
        
        # HTTP client for WMS requests
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Cache for Hobli boundary data (in production, this would be loaded from a database)
        self._hobli_cache: Optional[gpd.GeoDataFrame] = None
        
        logger.info(f"MapService initialized with Bhuvan URL: {self.bhuvan_base_url}")
    
    def validate_coordinates(self, lat: float, lon: float) -> CoordinateValidationResult:
        """
        Validate coordinates for Indian geographic regions
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            CoordinateValidationResult with validation status
        
        Validates:
        - Coordinate format and range
        - Decimal precision (minimum 4 decimal places)
        - Geographic bounds for India
        - Hobli boundary detection
        """
        logger.info(f"Validating coordinates: lat={lat}, lon={lon}")
        
        # Step 1: Validate basic coordinate range
        if not (-90 <= lat <= 90):
            return CoordinateValidationResult(
                is_valid=False,
                error=f"Latitude {lat} out of valid range (-90 to 90 degrees)"
            )
        
        if not (-180 <= lon <= 180):
            return CoordinateValidationResult(
                is_valid=False,
                error=f"Longitude {lon} out of valid range (-180 to 180 degrees)"
            )
        
        # Step 2: Check decimal precision (minimum 4 decimal places)
        lat_str = str(lat)
        lon_str = str(lon)
        
        lat_decimals = len(lat_str.split('.')[-1]) if '.' in lat_str else 0
        lon_decimals = len(lon_str.split('.')[-1]) if '.' in lon_str else 0
        
        if lat_decimals < self.coordinate_precision or lon_decimals < self.coordinate_precision:
            return CoordinateValidationResult(
                is_valid=False,
                error=f"Coordinates must have at least {self.coordinate_precision} decimal places for precision. "
                      f"Provided: lat={lat_decimals}, lon={lon_decimals} decimal places"
            )
        
        # Step 3: Validate geographic bounds for India
        lat_min, lat_max = self.india_lat_bounds
        lon_min, lon_max = self.india_lon_bounds
        
        if not (lat_min <= lat <= lat_max):
            return CoordinateValidationResult(
                is_valid=False,
                error=f"Latitude {lat} outside Indian geographic region ({lat_min}°N to {lat_max}°N). "
                      f"This system currently supports locations within India only."
            )
        
        if not (lon_min <= lon <= lon_max):
            return CoordinateValidationResult(
                is_valid=False,
                error=f"Longitude {lon} outside Indian geographic region ({lon_min}°E to {lon_max}°E). "
                      f"This system currently supports locations within India only."
            )
        
        # Step 4: Normalize coordinates (round to specified precision)
        normalized_lat = round(lat, self.coordinate_precision)
        normalized_lon = round(lon, self.coordinate_precision)
        
        # Step 5: Detect Hobli from coordinates
        hobli_info = self.get_hobli_from_coordinates(normalized_lat, normalized_lon)
        
        return CoordinateValidationResult(
            is_valid=True,
            normalized_coordinates=(normalized_lat, normalized_lon),
            hobli_id=hobli_info.get("hobli_id") if hobli_info else None,
            hobli_name=hobli_info.get("hobli_name") if hobli_info else None,
            district=hobli_info.get("district") if hobli_info else None,
            state=hobli_info.get("state") if hobli_info else None
        )
    
    async def get_wms_capabilities(self) -> WMSCapabilities:
        """
        Fetch WMS GetCapabilities from ISRO Bhuvan
        
        Returns:
            WMSCapabilities with service information
        """
        params = {
            "service": "WMS",
            "version": "1.3.0",
            "request": "GetCapabilities"
        }
        
        url = f"{self.bhuvan_base_url}?{urlencode(params)}"
        
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            # Parse XML response (simplified - in production, use proper XML parsing)
            # For now, return known Bhuvan layers
            return WMSCapabilities(
                service_title="ISRO Bhuvan WMS Service",
                service_abstract="Web Map Service providing satellite imagery and vector layers for India",
                available_layers=["LISS3", "LISS4", "CARTOSAT", "VECTOR", "ADMIN_BOUNDARY"],
                supported_formats=["image/png", "image/jpeg"],
                supported_crs=["EPSG:4326", "EPSG:3857"]
            )
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch WMS capabilities: {e}")
            # Return default capabilities
            return WMSCapabilities(
                service_title="ISRO Bhuvan WMS Service",
                service_abstract="Web Map Service providing satellite imagery and vector layers for India",
                available_layers=["LISS3", "LISS4", "CARTOSAT", "VECTOR", "ADMIN_BOUNDARY"],
                supported_formats=["image/png", "image/jpeg"],
                supported_crs=["EPSG:4326", "EPSG:3857"]
            )
    
    def get_wms_tile_url(
        self, 
        bbox: Tuple[float, float, float, float],
        width: int = 256,
        height: int = 256,
        layer: str = "LISS3",
        format: str = "image/png",
        crs: str = "EPSG:4326"
    ) -> str:
        """
        Generate ISRO Bhuvan WMS GetMap URL
        
        Args:
            bbox: Bounding box (minx, miny, maxx, maxy)
            width: Image width in pixels
            height: Image height in pixels
            layer: Bhuvan layer name
            format: Image format
            crs: Coordinate reference system
            
        Returns:
            WMS GetMap URL
        """
        params = {
            "service": "WMS",
            "version": "1.3.0",
            "request": "GetMap",
            "layers": layer,
            "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "width": width,
            "height": height,
            "format": format,
            "crs": crs,
            "styles": "",
            "transparent": "true"
        }
        
        return f"{self.bhuvan_base_url}?{urlencode(params)}"
    
    async def get_feature_info(
        self,
        lat: float,
        lon: float,
        layer: str = "ADMIN_BOUNDARY",
        info_format: str = "application/json"
    ) -> Optional[Dict[str, Any]]:
        """
        Get feature information at specific coordinates using WMS GetFeatureInfo
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            layer: WMS layer to query
            info_format: Response format
            
        Returns:
            Feature information dictionary or None
        """
        # Create a small bounding box around the point
        buffer = 0.01  # ~1km buffer
        bbox = (lon - buffer, lat - buffer, lon + buffer, lat + buffer)
        
        # Calculate pixel coordinates (center of 256x256 image)
        i = 128
        j = 128
        
        params = {
            "service": "WMS",
            "version": "1.3.0",
            "request": "GetFeatureInfo",
            "layers": layer,
            "query_layers": layer,
            "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "width": 256,
            "height": 256,
            "i": i,
            "j": j,
            "info_format": info_format,
            "crs": "EPSG:4326"
        }
        
        url = f"{self.bhuvan_base_url}?{urlencode(params)}"
        
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            if info_format == "application/json":
                return response.json()
            else:
                return {"raw_response": response.text}
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch feature info: {e}")
            return None
    
    def get_hobli_from_coordinates(self, lat: float, lon: float) -> Optional[Dict[str, str]]:
        """
        Detect Hobli (administrative subdivision) from coordinates
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            Dictionary with Hobli information or None if not found
        
        Note:
            In production, this would query a spatial database or use WMS GetFeatureInfo
            to retrieve actual Hobli boundary data from ISRO Bhuvan Vector layers.
            For now, returns a placeholder based on coordinate ranges.
        """
        logger.info(f"Detecting Hobli for coordinates: lat={lat}, lon={lon}")
        
        # Placeholder implementation using coordinate-based mapping
        # In production, this would use actual Hobli boundary data
        
        # Karnataka regions (example mapping)
        if 12.0 <= lat <= 13.5 and 77.0 <= lon <= 78.0:
            # Bangalore region
            return {
                "hobli_id": "KA_BLR_001",
                "hobli_name": "Bangalore North Hobli",
                "district": "Bangalore Urban",
                "state": "Karnataka"
            }
        elif 13.5 <= lat <= 15.0 and 76.0 <= lon <= 77.5:
            # Mysore region
            return {
                "hobli_id": "KA_MYS_001",
                "hobli_name": "Mysore Hobli",
                "district": "Mysore",
                "state": "Karnataka"
            }
        elif 15.0 <= lat <= 17.0 and 75.0 <= lon <= 76.5:
            # Belgaum region
            return {
                "hobli_id": "KA_BLG_001",
                "hobli_name": "Belgaum Hobli",
                "district": "Belgaum",
                "state": "Karnataka"
            }
        # Tamil Nadu regions
        elif 10.0 <= lat <= 11.5 and 78.5 <= lon <= 80.0:
            # Coimbatore region
            return {
                "hobli_id": "TN_CBE_001",
                "hobli_name": "Coimbatore Hobli",
                "district": "Coimbatore",
                "state": "Tamil Nadu"
            }
        elif 11.5 <= lat <= 13.5 and 79.5 <= lon <= 80.5:
            # Chennai region
            return {
                "hobli_id": "TN_CHN_001",
                "hobli_name": "Chennai Hobli",
                "district": "Chennai",
                "state": "Tamil Nadu"
            }
        # Andhra Pradesh regions
        elif 16.0 <= lat <= 17.5 and 80.0 <= lon <= 81.5:
            # Vijayawada region
            return {
                "hobli_id": "AP_VJA_001",
                "hobli_name": "Vijayawada Hobli",
                "district": "Krishna",
                "state": "Andhra Pradesh"
            }
        else:
            # Default fallback for other regions
            return {
                "hobli_id": "IN_UNK_001",
                "hobli_name": "Unknown Hobli",
                "district": "Unknown District",
                "state": "India"
            }
    
    def create_folium_map(
        self, 
        center_lat: float, 
        center_lon: float, 
        zoom: int = 10,
        add_bhuvan_layer: bool = True
    ) -> folium.Map:
        """
        Create Folium map with ISRO Bhuvan base layer
        
        Args:
            center_lat: Map center latitude
            center_lon: Map center longitude
            zoom: Initial zoom level
            add_bhuvan_layer: Whether to add Bhuvan WMS layer
            
        Returns:
            Folium Map object
        """
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles="OpenStreetMap",  # Default base layer
            attr="© OpenStreetMap contributors"
        )
        
        # Add ISRO Bhuvan WMS layer if requested
        if add_bhuvan_layer:
            # Note: Bhuvan WMS may require authentication or have CORS restrictions
            # For production, you may need to proxy requests through your backend
            bhuvan_wms = folium.WmsTileLayer(
                url=self.bhuvan_base_url,
                layers=self.default_layer,
                fmt="image/png",
                transparent=True,
                version="1.3.0",
                attr="© ISRO Bhuvan",
                name="ISRO Bhuvan LISS III",
                overlay=True,
                control=True
            )
            bhuvan_wms.add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        return m
    
    def add_plot_marker(
        self,
        map_obj: folium.Map,
        lat: float,
        lon: float,
        plot_id: str,
        popup_text: Optional[str] = None,
        color: str = "blue",
        draggable: bool = False
    ) -> folium.Marker:
        """
        Add a plot marker to the map
        
        Args:
            map_obj: Folium Map object
            lat: Marker latitude
            lon: Marker longitude
            plot_id: Unique plot identifier
            popup_text: Optional popup text
            color: Marker color
            draggable: Whether marker is draggable
            
        Returns:
            Folium Marker object
        """
        if popup_text is None:
            popup_text = f"Plot ID: {plot_id}<br>Coordinates: {lat:.6f}, {lon:.6f}"
        
        marker = folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"Plot {plot_id}",
            icon=folium.Icon(color=color, icon="info-sign"),
            draggable=draggable
        )
        
        marker.add_to(map_obj)
        return marker
    
    def add_jurisdiction_boundary(
        self,
        map_obj: folium.Map,
        hobli_id: str,
        boundary_coords: List[Tuple[float, float]],
        color: str = "blue",
        fill_opacity: float = 0.2
    ) -> folium.Polygon:
        """
        Add Hobli jurisdiction boundary to the map
        
        Args:
            map_obj: Folium Map object
            hobli_id: Hobli identifier
            boundary_coords: List of (lat, lon) coordinates defining the boundary
            color: Boundary color
            fill_opacity: Fill opacity
            
        Returns:
            Folium Polygon object
        """
        polygon = folium.Polygon(
            locations=boundary_coords,
            popup=f"Hobli: {hobli_id}",
            tooltip=f"Jurisdiction: {hobli_id}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=fill_opacity,
            weight=2
        )
        
        polygon.add_to(map_obj)
        return polygon
    
    def create_interactive_map(
        self,
        center_lat: float,
        center_lon: float,
        zoom: int = 10,
        add_bhuvan_layer: bool = True,
        enable_draw: bool = False,
        enable_locate: bool = True
    ) -> folium.Map:
        """
        Create interactive Folium map for Streamlit integration
        
        Args:
            center_lat: Map center latitude
            center_lon: Map center longitude
            zoom: Initial zoom level
            add_bhuvan_layer: Whether to add Bhuvan WMS layer
            enable_draw: Enable drawing tools
            enable_locate: Enable GPS location button
            
        Returns:
            Folium Map object with interactive features
        """
        # Create base map with click events enabled
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom,
            tiles="OpenStreetMap",
            attr="© OpenStreetMap contributors",
            prefer_canvas=True
        )
        
        # Add ISRO Bhuvan WMS layer if requested
        if add_bhuvan_layer:
            bhuvan_wms = folium.WmsTileLayer(
                url=self.bhuvan_base_url,
                layers=self.default_layer,
                fmt="image/png",
                transparent=True,
                version="1.3.0",
                attr="© ISRO Bhuvan",
                name="ISRO Bhuvan LISS III",
                overlay=True,
                control=True
            )
            bhuvan_wms.add_to(m)
        
        # Add GPS location control if requested
        if enable_locate:
            from folium.plugins import LocateControl
            LocateControl(
                auto_start=False,
                position="topleft",
                strings={
                    "title": "Show my location",
                    "popup": "You are here"
                }
            ).add_to(m)
        
        # Add drawing tools if requested
        if enable_draw:
            from folium.plugins import Draw
            Draw(
                export=False,
                position="topleft",
                draw_options={
                    "polyline": False,
                    "polygon": False,
                    "circle": False,
                    "rectangle": False,
                    "circlemarker": False,
                    "marker": True
                }
            ).add_to(m)
        
        # Add click event handler for coordinate capture
        m.add_child(folium.LatLngPopup())
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        return m
    
    def add_clustered_markers(
        self,
        map_obj: folium.Map,
        plots: List[Dict[str, Any]],
        cluster_radius: int = 80
    ) -> None:
        """
        Add clustered plot markers to the map
        
        Args:
            map_obj: Folium Map object
            plots: List of plot dictionaries with lat, lon, plot_id, status
            cluster_radius: Clustering radius in pixels
        """
        from folium.plugins import MarkerCluster
        
        # Create marker cluster
        marker_cluster = MarkerCluster(
            name="Plot Markers",
            overlay=True,
            control=True,
            icon_create_function=None,
            options={
                "maxClusterRadius": cluster_radius,
                "spiderfyOnMaxZoom": True,
                "showCoverageOnHover": True,
                "zoomToBoundsOnClick": True
            }
        )
        
        # Color mapping for plot status
        status_colors = {
            "active": "green",
            "analyzed": "blue",
            "alert": "red",
            "warning": "orange",
            "inactive": "gray"
        }
        
        # Add markers to cluster
        for plot in plots:
            lat = plot.get("lat")
            lon = plot.get("lon")
            plot_id = plot.get("plot_id", "Unknown")
            status = plot.get("status", "active")
            
            if lat is None or lon is None:
                continue
            
            color = status_colors.get(status, "blue")
            
            # Create popup content
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; min-width: 200px;">
                <h4 style="margin: 0 0 10px 0;">Plot {plot_id}</h4>
                <p style="margin: 5px 0;"><b>Status:</b> {status.title()}</p>
                <p style="margin: 5px 0;"><b>Coordinates:</b><br>{lat:.6f}, {lon:.6f}</p>
                {f'<p style="margin: 5px 0;"><b>Crop:</b> {plot.get("crop", "N/A")}</p>' if "crop" in plot else ''}
                {f'<p style="margin: 5px 0;"><b>Farmer:</b> {plot.get("farmer_name", "N/A")}</p>' if "farmer_name" in plot else ''}
            </div>
            """
            
            marker = folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Plot {plot_id} - {status.title()}",
                icon=folium.Icon(color=color, icon="leaf", prefix="fa")
            )
            
            marker.add_to(marker_cluster)
        
        marker_cluster.add_to(map_obj)
    
    def add_heatmap_layer(
        self,
        map_obj: folium.Map,
        alerts: List[Dict[str, Any]],
        radius: int = 15,
        blur: int = 25
    ) -> None:
        """
        Add heatmap layer for alert visualization
        
        Args:
            map_obj: Folium Map object
            alerts: List of alert dictionaries with lat, lon, risk_level
            radius: Heatmap point radius
            blur: Heatmap blur amount
        """
        from folium.plugins import HeatMap
        
        # Risk level to intensity mapping
        risk_intensity = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.9,
            "critical": 1.0
        }
        
        # Prepare heatmap data: [lat, lon, intensity]
        heat_data = []
        for alert in alerts:
            lat = alert.get("lat")
            lon = alert.get("lon")
            risk_level = alert.get("risk_level", "medium")
            
            if lat is None or lon is None:
                continue
            
            intensity = risk_intensity.get(risk_level, 0.5)
            heat_data.append([lat, lon, intensity])
        
        if heat_data:
            HeatMap(
                heat_data,
                name="Alert Heatmap",
                radius=radius,
                blur=blur,
                max_zoom=13,
                gradient={
                    0.0: "green",
                    0.5: "yellow",
                    0.7: "orange",
                    1.0: "red"
                }
            ).add_to(map_obj)
    
    async def close(self):
        """Close HTTP client connections"""
        await self.http_client.aclose()
        logger.info("MapService HTTP client closed")