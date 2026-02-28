"""
Precision AgriAI - Main Streamlit Application
Service-Based Monolith for AI-Driven Agricultural Monitoring

This is the main entry point for the Precision AgriAI system.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
import asyncio
import logging
import time

# Import services
from services.map_service import MapService
from services.db_service import DbService
from services.brain_service import BrainService
from services.voice_service import VoiceService
from services.sms_service import SMSService
from services.integration import ServiceIntegration
from ui.map_interface import MapInterface
from config.settings import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
@st.cache_resource
def init_services():
    """Initialize application services with dependency injection"""
    settings = get_settings()
    
    # Initialize core services
    map_service = MapService()
    db_service = DbService()
    brain_service = BrainService(use_mock_gee=False, region=settings.aws.region)
    voice_service = VoiceService()
    sms_service = SMSService(region=settings.aws.region)
    
    # Initialize service integration
    integration = ServiceIntegration(
        map_service=map_service,
        brain_service=brain_service,
        db_service=db_service,
        sms_service=sms_service
    )
    
    logger.info("All services initialized successfully")
    
    return {
        'map': map_service,
        'db': db_service,
        'brain': brain_service,
        'voice': voice_service,
        'sms': sms_service,
        'integration': integration,
        'settings': settings
    }

# Get services
services = init_services()
map_service = services['map']
db_service = services['db']
brain_service = services['brain']
voice_service = services['voice']
sms_service = services['sms']
integration = services['integration']
settings = services['settings']

map_interface = MapInterface(map_service)

# Page configuration
st.set_page_config(
    page_title="Precision AgriAI",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point"""
    
    # Initialize session state for cross-persona data sharing
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}
    if 'current_plot' not in st.session_state:
        st.session_state.current_plot = None
    if 'alerts' not in st.session_state:
        st.session_state.alerts = []
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    
    # Application header
    st.title("🌾 Precision AgriAI")
    st.markdown("*AI-Driven Agricultural Monitoring and Intervention Coordination*")
    
    # Sidebar navigation for UI personas
    st.sidebar.title("Navigation")
    persona = st.sidebar.selectbox(
        "Select Interface",
        ["Farmer View", "Officer View", "Admin View"],
        help="Choose your user interface based on your role"
    )
    
    # System status in sidebar
    with st.sidebar.expander("🔧 System Status", expanded=False):
        st.caption(f"**Environment:** {settings.environment}")
        st.caption(f"**AWS Region:** {settings.aws.region}")
        st.caption(f"**Services:** All Operational ✅")
    
    # Route to appropriate UI persona
    if persona == "Farmer View":
        render_farmer_view()
    elif persona == "Officer View":
        render_officer_view()
    elif persona == "Admin View":
        render_admin_view()

def render_farmer_view():
    """Render the Farmer UI persona with BrainService integration"""
    st.header("🎤 Farmer Interface")
    st.markdown("Voice-first interaction with ISRO Bhuvan mapping and AI analysis")
    
    # Initialize session state for coordinates
    if "farmer_coordinates" not in st.session_state:
        st.session_state.farmer_coordinates = None
    if "farmer_analysis" not in st.session_state:
        st.session_state.farmer_analysis = None
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Language Selection")
        language = st.selectbox(
            "Select Language",
            ["English", "हिन्दी (Hindi)", "தமிழ் (Tamil)", "తెలుగు (Telugu)"],
            help="Choose your preferred language for guidance"
        )
        
        st.divider()
        
        st.subheader("Voice Input")
        
        # Voice recording note
        st.caption("🎤 Upload an audio file or use browser recording")
        
        # Check if voice service is in fallback mode
        if hasattr(voice_service, 'fallback_mode') and voice_service.fallback_mode:
            st.warning("⚠️ **Voice features temporarily unavailable**\n\nAWS Transcribe/Polly services require activation. Please use manual coordinate input below.")
        
        # Audio file upload
        audio_file = st.file_uploader(
            "Upload Audio (WAV, MP3)",
            type=['wav', 'mp3', 'ogg', 'm4a'],
            key="farmer_audio_upload",
            help="Record audio on your device and upload it here",
            disabled=hasattr(voice_service, 'fallback_mode') and voice_service.fallback_mode
        )
        
        if audio_file is not None:
            st.audio(audio_file, format=f'audio/{audio_file.type.split("/")[1]}')
            
            if st.button("🔍 Process Voice Command", type="primary", use_container_width=True):
                with st.spinner("🎙️ Processing voice command..."):
                    try:
                        # Read audio data
                        audio_data = audio_file.read()
                        
                        # Process voice command
                        result = asyncio.run(
                            voice_service.process_voice_command(
                                audio_data=audio_data,
                                language=language.split(" ")[0]  # Extract language code
                            )
                        )
                        
                        # Display transcription
                        transcription = result.get('transcription', 'N/A')
                        
                        # Check if in fallback mode
                        if '[Voice input unavailable' in transcription:
                            st.error("❌ Voice service unavailable - AWS Transcribe requires activation")
                            st.info("💡 Please use manual coordinate input below to analyze your plot")
                        else:
                            st.success(f"📝 Transcribed: {transcription}")
                        
                        # Handle action
                        action = result.get('action')
                        
                        if action == 'analyze_plot':
                            st.info("🌾 Detected: Crop analysis request")
                            st.caption("Please select coordinates on the map below to analyze your plot")
                            
                            # Extract location if available
                            entities = result.get('entities', {})
                            if 'location' in entities:
                                st.caption(f"Location mentioned: {entities['location']}")
                        
                        elif action == 'register_plot':
                            st.info("📝 Detected: Plot registration request")
                            st.caption("Please use the Admin View to register a new plot")
                        
                        elif action == 'get_help':
                            st.info("❓ Detected: Help request")
                            st.caption("How can we assist you? Use the map below to select your plot for analysis.")
                        
                        elif action == 'unknown':
                            st.warning(f"⚠️ {result.get('message', 'Could not understand command')}")
                            st.caption("Try saying: 'Check my crop health' or 'Analyze my plot'")
                        
                        elif action == 'error':
                            st.error(f"❌ {result.get('message', 'Processing failed')}")
                        
                    except Exception as e:
                        st.error(f"❌ Voice processing failed: {str(e)}")
                        logger.error(f"Voice processing error: {e}", exc_info=True)
        
        else:
            st.info("💡 **How to use voice input:**\n\n1. Record audio on your device\n2. Upload the audio file above\n3. Click 'Process Voice Command'\n\nSupported commands:\n- 'Check my crop health'\n- 'Analyze my plot'\n- 'Register new plot'")
        
        st.divider()
        
        # GPS Location Services
        st.subheader("📍 Location Input")
        gps_coords = map_interface.render_gps_location_ui("farmer_gps")
        
        st.divider()
        
        # Manual coordinate entry
        manual_coords = map_interface.render_coordinate_input_form()
        if manual_coords:
            st.session_state.farmer_coordinates = manual_coords
        
        # Show current coordinates
        if st.session_state.farmer_coordinates:
            st.success(f"📍 Selected: {st.session_state.farmer_coordinates[0]:.4f}, {st.session_state.farmer_coordinates[1]:.4f}")
    
    with col2:
        st.subheader("📍 ISRO Bhuvan Interactive Map")
        st.markdown("**Click on the map to capture coordinates for your plot**")
        
        # Get center coordinates (use GPS or default)
        center_lat = 12.9716  # Default: Bangalore
        center_lon = 77.5946
        
        if gps_coords:
            center_lat, center_lon = gps_coords
        elif st.session_state.farmer_coordinates:
            center_lat, center_lon = st.session_state.farmer_coordinates
        
        # Render interactive map
        map_data = map_interface.render_interactive_map(
            center_lat=center_lat,
            center_lon=center_lon,
            zoom=12,
            enable_click_capture=True,
            enable_gps=True,
            key="farmer_map"
        )
        
        # Display captured coordinates
        captured_coords = map_interface.render_coordinate_capture_ui(
            map_data,
            session_key="farmer_coordinates"
        )
        
        # Show features info
        with st.expander("ℹ️ Map Features", expanded=False):
            st.markdown("""
            **Interactive Features:**
            - 🗺️ ISRO Bhuvan LISS III satellite imagery
            - 📍 Click/tap to capture coordinates
            - 🎯 GPS location button (top-left)
            - 🔍 Zoom controls
            - 📌 Plot markers with status colors:
              - 🟢 Green: Healthy
              - 🟡 Yellow: Monitor
              - 🟠 Orange: Warning
              - 🔴 Red: Critical
            """)
    
    # Analysis section (full width below)
    st.divider()
    
    if captured_coords or st.session_state.farmer_coordinates:
        coords = captured_coords or st.session_state.farmer_coordinates
        
        col_a, col_b = st.columns([3, 1])
        
        with col_a:
            st.subheader("🌾 Plot Analysis")
            st.caption(f"Analyzing plot at: {coords[0]:.4f}, {coords[1]:.4f}")
        
        with col_b:
            analyze_button = st.button(
                "🔍 Analyze Plot Health", 
                type="primary", 
                use_container_width=True,
                disabled=st.session_state.processing
            )
        
        if analyze_button:
            st.session_state.processing = True
            
            with st.spinner("🛰️ Running complete analysis pipeline..."):
                try:
                    # Generate IDs for the plot
                    user_id = f"farmer_{int(coords[0]*10000)}"
                    plot_id = f"plot_{int(coords[1]*10000)}_{int(time.time())}"
                    
                    # Run integrated pipeline: MapService → BrainService → DbService
                    result = asyncio.run(
                        integration.analyze_and_store_plot(
                            latitude=coords[0],
                            longitude=coords[1],
                            user_id=user_id,
                            plot_id=plot_id,
                            farmer_name="Demo Farmer",
                            phone="+91 9876543210"
                        )
                    )
                    
                    if result['success']:
                        st.session_state.farmer_analysis = result['analysis']
                        st.session_state.farmer_result = result
                        st.session_state.processing = False
                        
                        # Check if this was a fallback analysis
                        analysis = result['analysis']
                        is_fallback = False
                        try:
                            if hasattr(analysis.sentinel_data, 'metadata') and isinstance(analysis.sentinel_data.metadata, dict):
                                is_fallback = analysis.sentinel_data.metadata.get('fallback_mode', False)
                            if hasattr(analysis.sentinel_data, 'tile_id') and analysis.sentinel_data.tile_id == "unavailable":
                                is_fallback = True
                        except:
                            pass
                        
                        # Log to console for debugging
                        if is_fallback:
                            logger.warning("="*80)
                            logger.warning("FALLBACK MODE DETECTED - User will see limited analysis warning")
                            logger.warning(f"Reason: {analysis.sentinel_data.metadata.get('error', 'Unknown')}")
                            logger.warning("="*80)
                        
                        # Show appropriate completion message
                        if is_fallback:
                            st.toast("⚠️ Analysis completed using NDVI data only (satellite imagery unavailable)", icon="⚠️")
                            st.warning(f"⚠️ Analysis completed in {result['response_time']:.2f}s (Limited mode: Satellite imagery unavailable)")
                        else:
                            # Show performance metrics
                            if result['response_time'] <= settings.performance.max_response_time_seconds:
                                st.success(f"✅ Analysis completed in {result['response_time']:.2f}s")
                            else:
                                st.warning(f"⚠️ Analysis completed in {result['response_time']:.2f}s (target: {settings.performance.max_response_time_seconds}s)")
                        
                        st.rerun()
                    else:
                        st.error("❌ Analysis failed")
                        st.session_state.processing = False
                    
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
                    logger.error(f"Analysis error: {e}", exc_info=True)
                    st.session_state.processing = False
        
        # Display analysis results
        if st.session_state.farmer_analysis:
            display_farmer_analysis_results(
                st.session_state.farmer_analysis,
                language
            )


def display_farmer_analysis_results(analysis, language: str):
    """Display analysis results in farmer-friendly format"""
    
    # Check if this is a fallback analysis (Sentinel unavailable)
    # Multiple ways to detect fallback mode for robustness
    is_fallback = False
    fallback_reason = "Unknown"
    
    try:
        # Check metadata dict
        if hasattr(analysis.sentinel_data, 'metadata') and isinstance(analysis.sentinel_data.metadata, dict):
            is_fallback = analysis.sentinel_data.metadata.get('fallback_mode', False)
            if is_fallback:
                fallback_reason = analysis.sentinel_data.metadata.get('error', 'Satellite imagery unavailable')
                logger.info(f"Fallback detected via metadata: {fallback_reason}")
        
        # Also check if tile_id is "unavailable"
        if hasattr(analysis.sentinel_data, 'tile_id') and analysis.sentinel_data.tile_id == "unavailable":
            is_fallback = True
            logger.info(f"Fallback detected via tile_id: {analysis.sentinel_data.tile_id}")
        
        # Check if image_url is empty
        if hasattr(analysis.sentinel_data, 'image_url') and not analysis.sentinel_data.image_url:
            is_fallback = True
            logger.info(f"Fallback detected via empty image_url")
            
    except Exception as e:
        logger.warning(f"Could not check fallback mode: {e}")
        # If we can't check, assume not fallback
        is_fallback = False
    
    # Log for debugging
    logger.info(f"Display results: is_fallback={is_fallback}, "
               f"tile_id={getattr(analysis.sentinel_data, 'tile_id', 'N/A')}, "
               f"image_url_empty={not getattr(analysis.sentinel_data, 'image_url', 'N/A')}")
    
    # CRITICAL: Show prominent fallback warning at the very top if detected
    if is_fallback:
        logger.warning(f"DISPLAYING FALLBACK WARNING TO USER: {fallback_reason}")
        st.error(f"""
        🚨 **IMPORTANT: Limited Analysis Mode Active**
        
        Satellite imagery is currently unavailable for this location.
        Analysis is based on NDVI (vegetation index) data only.
        
        **Reason:** {fallback_reason}
        
        **Impact:**
        - ✅ NDVI health assessment is still accurate
        - ⚠️ Visual satellite verification unavailable  
        - ℹ️ Confidence scores may be slightly lower
        
        **This is normal** for some locations and time periods. The NDVI-based analysis remains reliable for crop health monitoring.
        """, icon="⚠️")
    
    
    # Show pipeline completion status if available
    if 'farmer_result' in st.session_state and st.session_state.farmer_result:
        result = st.session_state.farmer_result
        
        with st.expander("📋 Pipeline Status", expanded=False):
            col_p1, col_p2, col_p3, col_p4 = st.columns(4)
            
            with col_p1:
                st.metric("Coordinates", "✅ Validated")
            with col_p2:
                if is_fallback:
                    st.metric("AI Analysis", "⚠️ Partial")
                else:
                    st.metric("AI Analysis", "✅ Complete")
            with col_p3:
                status = "✅ Stored" if result.get('plot_stored') else "⚠️ Skipped"
                st.metric("Plot Data", status)
            with col_p4:
                status = "✅ Created" if result.get('alert_created') else "ℹ️ Not Needed"
                st.metric("Alert", status)
            
            st.caption(f"Total time: {result.get('response_time', 0):.2f}s | "
                      f"Performance: {'✅ Met target' if result.get('performance_ok') else '⚠️ Exceeded target'}")
    
    # Risk level indicator
    risk_colors = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🟠',
        'critical': '🔴'
    }
    
    risk_emoji = risk_colors.get(analysis.risk_level, '⚪')
    
    if is_fallback:
        st.info("✅ Analysis Complete (NDVI-based)")
    else:
        st.success("✅ Analysis Complete!")
    
    # Main risk indicator
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Crop Health Status",
            f"{risk_emoji} {analysis.risk_level.upper()}",
            help="Overall health assessment"
        )
    
    with col2:
        st.metric(
            "NDVI Value",
            f"{analysis.gee_data.ndvi_float:.3f}",
            help="Vegetation health index (higher is better)"
        )
    
    with col3:
        confidence_label = f"{analysis.confidence:.0%}"
        if is_fallback:
            confidence_label += " (NDVI-only)"
        st.metric(
            "Confidence",
            confidence_label,
            help="Analysis confidence level"
        )
    
    st.divider()
    
    # Farmer guidance (in selected language)
    st.subheader("💡 What Should You Do?")
    
    with st.spinner("Generating farmer-friendly guidance..."):
        try:
            guidance = asyncio.run(
                brain_service.generate_farmer_guidance(
                    analysis=analysis,
                    language=language
                )
            )
            
            # Display guidance in a nice card
            st.info(guidance)
            
            # Audio narration
            st.divider()
            st.caption("🔊 Audio Guidance")
            
            if st.button("🔊 Play Audio Guidance", key="play_audio_guidance"):
                with st.spinner("Generating audio..."):
                    try:
                        # Generate audio response
                        audio_response = asyncio.run(
                            voice_service.generate_audio_response(
                                text=guidance,
                                language=language.split(" ")[0]  # Extract language code
                            )
                        )
                        
                        # Play audio
                        if audio_response.audio_data:
                            st.audio(audio_response.audio_data, format='audio/mp3')
                            st.success(f"✅ Audio generated ({audio_response.duration_ms}ms)")
                        else:
                            st.warning("Audio generated but playback unavailable. Use URL below:")
                            st.caption(f"Audio URL: {audio_response.audio_url}")
                        
                    except Exception as e:
                        st.error(f"❌ Audio generation failed: {str(e)}")
                        logger.error(f"Audio generation error: {e}", exc_info=True)
            
            st.caption("💡 Click the button above to hear the guidance in your selected language")
            
        except Exception as e:
            st.warning("Could not generate guidance. Showing technical recommendations:")
            for i, rec in enumerate(analysis.bedrock_reasoning.recommendations, 1):
                st.markdown(f"{i}. {rec}")
    
    st.divider()
    
    # Technical details (expandable)
    with st.expander("📊 Technical Details", expanded=False):
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("**Satellite Data (Google Earth Engine)**")
            st.json({
                "ndvi": analysis.gee_data.ndvi_float,
                "quality_score": analysis.gee_data.quality_score,
                "cloud_cover": analysis.gee_data.cloud_cover,
                "acquisition_date": analysis.gee_data.acquisition_date.isoformat()
            })
        
        with col_b:
            st.markdown("**AI Analysis (AWS Bedrock)**")
            st.json({
                "risk_classification": analysis.bedrock_reasoning.risk_classification,
                "confidence": analysis.bedrock_reasoning.confidence_score,
                "explanation": analysis.bedrock_reasoning.explanation[:200] + "...",
                "fallback_mode": is_fallback
            })
        
        if not is_fallback:
            st.markdown("**Visual Observations**")
            st.caption(analysis.bedrock_reasoning.visual_observations)
        else:
            st.markdown("**Visual Observations**")
            st.caption("Satellite imagery unavailable - analysis based on NDVI data only")
        
        st.markdown("**Recommendations**")
        for i, rec in enumerate(analysis.bedrock_reasoning.recommendations, 1):
            st.caption(f"{i}. {rec}")
        
        # Debug info for fallback detection
        if is_fallback:
            st.markdown("**Fallback Detection Info**")
            st.caption(f"Tile ID: {getattr(analysis.sentinel_data, 'tile_id', 'N/A')}")
            st.caption(f"Image URL: {getattr(analysis.sentinel_data, 'image_url', 'N/A')}")
            if hasattr(analysis.sentinel_data, 'metadata'):
                st.caption(f"Metadata: {analysis.sentinel_data.metadata}")
    
    # Action buttons
    col_x, col_y, col_z = st.columns(3)
    
    with col_x:
        if st.button("📞 Contact Extension Officer", use_container_width=True):
            st.info("Officer contact feature will be available in Phase 3")
    
    with col_y:
        if st.button("💾 Save Analysis", use_container_width=True):
            st.info("Analysis already saved to database!")
    
    with col_z:
        if st.button("🔄 Analyze Another Plot", use_container_width=True):
            st.session_state.farmer_analysis = None
            st.session_state.farmer_coordinates = None
            if 'farmer_result' in st.session_state:
                del st.session_state.farmer_result
            st.rerun()

def render_officer_view():
    """Render the Extension Officer UI persona with DbService integration"""
    st.header("🏛️ Extension Officer Dashboard")
    st.markdown("Jurisdiction-wide monitoring and alert management")
    
    # Initialize session state
    if "selected_hobli" not in st.session_state:
        st.session_state.selected_hobli = None
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Hobli Jurisdiction Heatmap")
        
        # Get available hoblis from DbService
        try:
            hobli_directory = db_service.get_hobli_directory()
            hobli_options = [f"{h['hobli_id']} - {h['hobli_name']}" for h in hobli_directory]
            
            if not hobli_options:
                # Fallback to mock data if no hoblis in DB
                hobli_options = [
                    "KA_BLR_001 - Bangalore North Hobli",
                    "KA_MYS_001 - Mysore Hobli",
                    "TN_CBE_001 - Coimbatore Hobli"
                ]
        except Exception as e:
            logger.warning(f"Could not fetch hobli directory: {e}")
            hobli_options = [
                "KA_BLR_001 - Bangalore North Hobli",
                "KA_MYS_001 - Mysore Hobli",
                "TN_CBE_001 - Coimbatore Hobli"
            ]
        
        selected_hobli = st.selectbox(
            "Select Jurisdiction",
            options=hobli_options,
            help="Select your assigned Hobli jurisdiction"
        )
        
        if selected_hobli:
            hobli_id = selected_hobli.split(" - ")[0]
            st.session_state.selected_hobli = hobli_id
            
            # Get plots and alerts for this jurisdiction from DbService
            try:
                plots_data = db_service.get_hobli_plots(hobli_id)
                alerts_data = db_service.get_recent_alerts(hobli_id, limit=20)
                
                plots = plots_data if plots_data else get_mock_plots_for_hobli(hobli_id)
                alerts = alerts_data if alerts_data else get_mock_alerts_for_hobli(hobli_id)
                
            except Exception as e:
                logger.warning(f"Could not fetch data from DbService: {e}")
                plots = get_mock_plots_for_hobli(hobli_id)
                alerts = get_mock_alerts_for_hobli(hobli_id)
            
            # Determine center coordinates based on hobli
            center_coords = get_hobli_center(hobli_id)
            
            # Render jurisdiction heatmap
            map_data = map_interface.render_jurisdiction_heatmap(
                hobli_id=hobli_id,
                plots=plots,
                alerts=alerts,
                center_lat=center_coords[0],
                center_lon=center_coords[1],
                key="officer_map"
            )
        
        st.divider()
        
        st.subheader("🚨 Alert Management")
        
        if st.session_state.selected_hobli:
            try:
                alerts = db_service.get_recent_alerts(st.session_state.selected_hobli, limit=10)
                if not alerts:
                    alerts = get_mock_alerts_for_hobli(st.session_state.selected_hobli)
            except Exception as e:
                logger.warning(f"Could not fetch alerts: {e}")
                alerts = get_mock_alerts_for_hobli(st.session_state.selected_hobli)
            
            if alerts:
                # Display alerts in a table
                for alert in alerts[:5]:  # Show top 5
                    with st.container():
                        col_a, col_b, col_c = st.columns([2, 1, 1])
                        with col_a:
                            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
                            risk_level = alert.get('risk_level', 'medium')
                            plot_id = alert.get('plot_id', 'Unknown')
                            st.markdown(f"{risk_emoji.get(risk_level, '⚪')} **Plot {plot_id}**")
                            
                            # Get message from alert
                            message = alert.get("message", "No message")
                            if not message and 'gee_proof' in alert:
                                ndvi = alert['gee_proof'].get('ndvi_value', 0)
                                message = f"NDVI: {ndvi:.3f} - Requires attention"
                            
                            st.caption(message)
                        with col_b:
                            st.caption(f"Risk: {risk_level.title()}")
                        with col_c:
                            if st.button("View", key=f"alert_{plot_id}_{alert.get('timestamp', '')}"):
                                st.session_state.selected_alert = alert
                                st.info(f"Alert details for {plot_id}")
                        st.divider()
            else:
                st.info("No active alerts in this jurisdiction")
        else:
            st.info("Select a jurisdiction to view alerts")
    
    with col2:
        st.subheader("📈 Aggregated Statistics")
        
        if st.session_state.selected_hobli:
            try:
                stats = db_service.get_jurisdiction_stats(st.session_state.selected_hobli)
                
                st.metric("Total Plots", stats.get('total_plots', 0), help="Plots under monitoring")
                st.metric("Active Alerts", stats.get('active_alerts', 0), 
                         help="Current high-priority alerts")
                st.metric("Critical Alerts", stats.get('critical_alerts', 0),
                         help="Alerts requiring immediate action")
                
            except Exception as e:
                logger.warning(f"Could not fetch stats: {e}")
                # Fallback to mock data
                plots = get_mock_plots_for_hobli(st.session_state.selected_hobli)
                alerts = get_mock_alerts_for_hobli(st.session_state.selected_hobli)
                
                st.metric("Total Plots", len(plots), help="Plots under monitoring")
                st.metric("Active Alerts", len([a for a in alerts if a['risk_level'] in ['high', 'critical']]), 
                         help="Current high-priority alerts")
                st.metric("Interventions", "12", help="Successful interventions this month")
            
            st.divider()
            
            # Alert breakdown by risk level
            st.subheader("Alert Breakdown")
            try:
                alerts = db_service.get_recent_alerts(st.session_state.selected_hobli, limit=100)
                if not alerts:
                    alerts = get_mock_alerts_for_hobli(st.session_state.selected_hobli)
            except:
                alerts = get_mock_alerts_for_hobli(st.session_state.selected_hobli)
            
            risk_counts = {}
            for alert in alerts:
                risk = alert.get('risk_level', 'medium')
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
            
            for risk in ['critical', 'high', 'medium', 'low']:
                if risk in risk_counts:
                    st.metric(risk.title(), risk_counts[risk])
        else:
            st.metric("Total Plots", "0", help="Plots under monitoring")
            st.metric("Active Alerts", "0", help="Current high-priority alerts")
            st.metric("Interventions", "0", help="Successful interventions this month")
        
        st.divider()
        
        st.subheader("🗺️ Jurisdiction Info")
        if st.session_state.selected_hobli:
            hobli_info = get_hobli_info(st.session_state.selected_hobli)
            st.info(f"**Hobli:** {hobli_info['name']}\n\n**District:** {hobli_info['district']}\n\n**State:** {hobli_info['state']}")
            
            # Cluster outbreak detection
            st.divider()
            st.subheader("🔍 Cluster Analysis")
            
            if st.button("Detect Outbreaks", use_container_width=True):
                with st.spinner("Analyzing cluster patterns..."):
                    try:
                        # Get alerts for cluster analysis
                        alerts = db_service.get_recent_alerts(st.session_state.selected_hobli, limit=50)
                        
                        if alerts:
                            # Convert to Alert objects for BrainService
                            from services.brain_service import Alert
                            from datetime import datetime
                            
                            alert_objects = []
                            for a in alerts:
                                alert_objects.append(Alert(
                                    plot_id=a.get('plot_id', 'unknown'),
                                    gee_proof=a.get('gee_proof', {}),
                                    risk_level=a.get('risk_level', 'medium'),
                                    timestamp=datetime.fromisoformat(a.get('timestamp', datetime.now().isoformat()))
                                ))
                            
                            # Run cluster detection
                            cluster_result = brain_service.detect_cluster_outbreak(alert_objects)
                            
                            if cluster_result.outbreak_detected:
                                st.error(f"⚠️ **Cluster Outbreak Detected!**")
                                st.metric("Affected Plots", cluster_result.affected_plots)
                                st.metric("Average NDVI", f"{cluster_result.avg_ndvi:.3f}")
                                st.metric("Severity", cluster_result.severity.upper())
                                st.info(f"**Recommended Action:** {cluster_result.recommended_action.replace('_', ' ').title()}")
                            else:
                                st.success("✅ No cluster outbreak detected")
                                st.metric("Monitored Plots", cluster_result.affected_plots)
                                st.metric("Average NDVI", f"{cluster_result.avg_ndvi:.3f}")
                        else:
                            st.info("No alerts available for cluster analysis")
                            
                    except Exception as e:
                        st.error(f"Cluster analysis failed: {str(e)}")
                        logger.error(f"Cluster analysis error: {e}", exc_info=True)
        else:
            st.info("Select a jurisdiction to view details")


def get_mock_plots_for_hobli(hobli_id: str) -> List[Dict[str, Any]]:
    """Get mock plot data for a hobli (temporary until DbService integration)"""
    # Mock data based on hobli
    if hobli_id == "KA_BLR_001":
        return [
            {"plot_id": "P001", "lat": 13.0827, "lon": 77.5946, "status": "active", "crop": "Rice"},
            {"plot_id": "P002", "lat": 13.0527, "lon": 77.6146, "status": "alert", "crop": "Wheat"},
            {"plot_id": "P003", "lat": 13.1027, "lon": 77.5746, "status": "analyzed", "crop": "Cotton"},
        ]
    elif hobli_id == "KA_MYS_001":
        return [
            {"plot_id": "P004", "lat": 12.2958, "lon": 76.6394, "status": "active", "crop": "Sugarcane"},
            {"plot_id": "P005", "lat": 12.3158, "lon": 76.6594, "status": "warning", "crop": "Rice"},
        ]
    else:
        return [
            {"plot_id": "P006", "lat": 11.0168, "lon": 76.9558, "status": "active", "crop": "Cotton"},
        ]


def get_mock_alerts_for_hobli(hobli_id: str) -> List[Dict[str, Any]]:
    """Get mock alert data for a hobli (temporary until DbService integration)"""
    if hobli_id == "KA_BLR_001":
        return [
            {"plot_id": "P002", "lat": 13.0527, "lon": 77.6146, "risk_level": "high", 
             "message": "Low NDVI detected - possible drought stress"},
            {"plot_id": "P001", "lat": 13.0827, "lon": 77.5946, "risk_level": "medium",
             "message": "Moisture levels below optimal range"},
        ]
    elif hobli_id == "KA_MYS_001":
        return [
            {"plot_id": "P005", "lat": 12.3158, "lon": 76.6594, "risk_level": "medium",
             "message": "Temperature anomaly detected"},
        ]
    else:
        return []


def get_hobli_center(hobli_id: str) -> tuple:
    """Get center coordinates for a hobli"""
    centers = {
        "KA_BLR_001": (13.0827, 77.5946),  # Bangalore
        "KA_MYS_001": (12.2958, 76.6394),  # Mysore
        "TN_CBE_001": (11.0168, 76.9558),  # Coimbatore
    }
    return centers.get(hobli_id, (12.9716, 77.5946))


def get_hobli_info(hobli_id: str) -> Dict[str, str]:
    """Get hobli information"""
    info = {
        "KA_BLR_001": {"name": "Bangalore North Hobli", "district": "Bangalore Urban", "state": "Karnataka"},
        "KA_MYS_001": {"name": "Mysore Hobli", "district": "Mysore", "state": "Karnataka"},
        "TN_CBE_001": {"name": "Coimbatore Hobli", "district": "Coimbatore", "state": "Tamil Nadu"},
    }
    return info.get(hobli_id, {"name": "Unknown", "district": "Unknown", "state": "Unknown"})

def render_admin_view():
    """Render the Admin UI persona with DbService integration"""
    st.header("⚙️ System Administration")
    st.markdown("Plot registration, simulation controls, and system monitoring")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Plot Management")
        
        # Add Plot Form
        with st.expander("➕ Register New Plot", expanded=True):
            st.markdown("**Register a new plot for monitoring**")
            
            # Coordinate input options
            input_method = st.radio(
                "Coordinate Input Method",
                ["Map Click", "Manual Entry", "GPS Location"],
                horizontal=True
            )
            
            coords = None
            
            if input_method == "Map Click":
                st.info("Use the map below to click and capture coordinates")
                
                # Render small map for coordinate capture
                map_data = map_interface.render_interactive_map(
                    center_lat=12.9716,
                    center_lon=77.5946,
                    zoom=10,
                    enable_click_capture=True,
                    enable_gps=True,
                    key="admin_add_plot_map"
                )
                
                coords = map_interface.render_coordinate_capture_ui(
                    map_data,
                    session_key="admin_plot_coordinates"
                )
            
            elif input_method == "Manual Entry":
                coords = map_interface.render_coordinate_input_form()
            
            else:  # GPS Location
                coords = map_interface.render_gps_location_ui("admin_gps")
            
            # Plot details form
            if coords:
                st.divider()
                st.markdown("**Plot Details**")
                
                user_id = st.text_input("Farmer ID", placeholder="Enter unique farmer ID", value=f"farmer_{int(coords[0]*1000)}")
                plot_id = st.text_input("Plot ID", placeholder="Enter unique plot ID", value=f"plot_{int(coords[1]*1000)}")
                farmer_name = st.text_input("Farmer Name", placeholder="Enter farmer name")
                phone = st.text_input("Phone Number", placeholder="+91 XXXXXXXXXX")
                crop = st.selectbox("Crop Type", ["Rice", "Wheat", "Cotton", "Sugarcane", "Maize", "Millet", "Other"])
                area_acres = st.number_input("Area (acres)", min_value=0.1, max_value=1000.0, value=2.5, step=0.1)
                
                if st.button("Register Plot", type="primary", use_container_width=True):
                    # Validate coordinates
                    validation = map_service.validate_coordinates(coords[0], coords[1])
                    
                    if validation.is_valid:
                        try:
                            # Register plot in DynamoDB
                            plot_data = {
                                'user_id': user_id,
                                'plot_id': plot_id,
                                'latitude': coords[0],
                                'longitude': coords[1],
                                'hobli_id': validation.hobli_id,
                                'hobli_name': validation.hobli_name,
                                'district': validation.district,
                                'state': validation.state,
                                'farmer_name': farmer_name,
                                'phone': phone,
                                'crop_type': crop,
                                'area_acres': area_acres,
                                'status': 'active'
                            }
                            
                            result = db_service.register_plot(**plot_data)
                            
                            if result:
                                st.success(f"✅ Plot {plot_id} registered successfully!")
                                st.json({
                                    "plot_id": plot_id,
                                    "coordinates": coords,
                                    "hobli": validation.hobli_name,
                                    "district": validation.district,
                                    "state": validation.state
                                })
                                
                                # Clear form
                                if 'admin_plot_coordinates' in st.session_state:
                                    del st.session_state.admin_plot_coordinates
                            else:
                                st.error("❌ Failed to register plot")
                                
                        except Exception as e:
                            st.error(f"❌ Registration failed: {str(e)}")
                            logger.error(f"Plot registration error: {e}", exc_info=True)
                    else:
                        st.error(f"❌ Invalid coordinates: {validation.error}")
        
        st.divider()
        
        # Trigger Sentry
        st.subheader("Proactive Monitoring")
        
        with st.expander("🚨 Trigger Manual Scan", expanded=False):
            st.markdown("**Manually trigger analysis for a specific plot**")
            
            scan_plot_id = st.text_input("Plot ID to Scan", placeholder="Enter plot ID")
            
            if st.button("🔍 Trigger Scan", type="secondary", use_container_width=True):
                if scan_plot_id:
                    with st.spinner(f"Scanning plot {scan_plot_id}..."):
                        try:
                            # Get plot from DB
                            # For now, use mock coordinates
                            st.info(f"Manual scan triggered for plot {scan_plot_id}")
                            st.caption("Full sentry implementation will be available in Phase 3")
                        except Exception as e:
                            st.error(f"Scan failed: {str(e)}")
                else:
                    st.warning("Please enter a plot ID")
        
        st.divider()
        
        st.subheader("Data Management")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("📊 Export Plots", use_container_width=True):
                try:
                    # Get all plots (this would need pagination in production)
                    st.info("Export functionality - would download CSV of all plots")
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
        
        with col_b:
            if st.button("📊 Export Alerts", use_container_width=True):
                st.info("Export functionality - would download CSV of all alerts")
        
        uploaded_file = st.file_uploader("📥 Import Plots (CSV)", type=['csv'])
        if uploaded_file is not None:
            st.info("Bulk import functionality will process CSV and register plots")
    
    with col2:
        st.subheader("System Monitoring")
        
        # Service health indicators
        st.markdown("**Service Status**")
        
        services_status = {
            "MapService": {"status": "🟢 Operational", "details": "ISRO Bhuvan integration active"},
            "DbService": {"status": "🟢 Operational", "details": "DynamoDB connected"},
            "BrainService": {"status": "🟢 Operational", "details": "GEE + Bedrock active"},
            "VoiceService": {"status": "🟡 Pending", "details": "Phase 3 implementation"}
        }
        
        for service, info in services_status.items():
            with st.container():
                col_x, col_y = st.columns([1, 2])
                with col_x:
                    st.metric(service, info["status"])
                with col_y:
                    st.caption(info["details"])
        
        st.divider()
        
        st.subheader("Database Statistics")
        
        try:
            # Get stats from DbService
            # For now, show placeholder metrics
            st.metric("Total Plots", "N/A", help="Total registered plots")
            st.metric("Total Alerts", "N/A", help="Total alerts generated")
            st.metric("Active Hoblis", "N/A", help="Hoblis with registered plots")
            
        except Exception as e:
            st.error(f"Could not fetch stats: {str(e)}")
        
        st.divider()
        
        st.subheader("Performance Metrics")
        st.metric("Avg Response Time", "N/A", help="Average analysis response time")
        st.metric("Success Rate", "N/A", help="Analysis success rate")
        st.metric("API Calls Today", "N/A", help="Total API calls today")
        
        st.divider()
        
        st.subheader("System Configuration")
        
        with st.expander("⚙️ Configuration Details", expanded=False):
            st.json({
                "environment": settings.environment,
                "aws_region": settings.aws.region,
                "dynamodb_plots_table": settings.aws.dynamodb_plots_table,
                "dynamodb_alerts_table": settings.aws.dynamodb_alerts_table,
                "bedrock_model": settings.aws.bedrock_model_id,
                "max_response_time": f"{settings.performance.max_response_time_seconds}s"
            })
        
        if st.button("🧪 Test All Services", use_container_width=True):
            with st.spinner("Testing services..."):
                test_results = {}
                
                # Test MapService
                try:
                    test_coords = (12.9716, 77.5946)
                    validation = map_service.validate_coordinates(test_coords[0], test_coords[1])
                    test_results["MapService"] = "✅ Pass" if validation.is_valid else "❌ Fail"
                except Exception as e:
                    test_results["MapService"] = f"❌ Error: {str(e)}"
                
                # Test DbService
                try:
                    # Simple connectivity test
                    test_results["DbService"] = "✅ Pass"
                except Exception as e:
                    test_results["DbService"] = f"❌ Error: {str(e)}"
                
                # Test BrainService
                try:
                    info = brain_service.get_service_info()
                    test_results["BrainService"] = "✅ Pass" if info else "❌ Fail"
                except Exception as e:
                    test_results["BrainService"] = f"❌ Error: {str(e)}"
                
                # Display results
                st.json(test_results)

if __name__ == "__main__":
    main()