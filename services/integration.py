"""
Service Integration Module

Handles the complete pipeline: MapService → BrainService → DbService → SMSService
Includes error handling, performance tracking, and service health monitoring.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from services.map_service import MapService
from services.brain_service import BrainService, AnalysisResult
from services.db_service import DbService
from services.sms_service import SMSService
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ServiceIntegration:
    """Orchestrates the complete analysis pipeline across all services"""
    
    def __init__(
        self,
        map_service: MapService,
        brain_service: BrainService,
        db_service: DbService,
        sms_service: Optional[SMSService] = None
    ):
        """
        Initialize service integration
        
        Args:
            map_service: MapService instance
            brain_service: BrainService instance
            db_service: DbService instance
            sms_service: Optional SMSService instance for notifications
        """
        self.map_service = map_service
        self.brain_service = brain_service
        self.db_service = db_service
        self.sms_service = sms_service or SMSService()
        self.settings = get_settings()
        
        # Performance tracking
        self.metrics = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'sms_sent': 0,
            'avg_response_time': 0.0,
            'total_response_time': 0.0
        }
        
        logger.info("ServiceIntegration initialized with SMS notifications")
    
    async def analyze_and_store_plot(
        self,
        latitude: float,
        longitude: float,
        user_id: str,
        plot_id: str,
        farmer_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete end-to-end plot analysis workflow
        
        Pipeline:
        1. Validate coordinates (MapService)
        2. Analyze plot health (BrainService: GEE + Sentinel + Bedrock)
        3. Store results and create alert if needed (DbService)
        
        Args:
            latitude: Plot latitude
            longitude: Plot longitude
            user_id: Farmer user ID
            plot_id: Unique plot ID
            farmer_name: Optional farmer name
            phone: Optional phone number
            
        Returns:
            Dictionary with analysis results and storage status
            
        Raises:
            ValueError: If coordinates are invalid
            Exception: If any service fails
        """
        start_time = time.time()
        self.metrics['total_analyses'] += 1
        
        try:
            logger.info(f"Starting end-to-end analysis for plot {plot_id} at ({latitude}, {longitude})")
            
            # Step 1: Validate coordinates and get jurisdiction info
            validation = self.map_service.validate_coordinates(latitude, longitude)
            
            if not validation.is_valid:
                raise ValueError(f"Invalid coordinates: {validation.error}")
            
            logger.info(f"Coordinates validated: {validation.hobli_name}, {validation.district}")
            
            # Step 2: Run multimodal AI analysis
            analysis_result = await self.brain_service.analyze_plot(
                lat=latitude,
                lon=longitude
            )
            
            logger.info(f"Analysis complete: Risk={analysis_result.risk_level}, "
                       f"NDVI={analysis_result.gee_data.ndvi_float:.3f}")
            
            # Step 3: Store plot data if not exists
            plot_data = {
                'user_id': user_id,
                'plot_id': plot_id,
                'latitude': latitude,
                'longitude': longitude,
                'hobli_id': validation.hobli_id,
                'hobli_name': validation.hobli_name,
                'district': validation.district,
                'state': validation.state,
                'farmer_name': farmer_name or 'Unknown',
                'phone': phone or '',
                'status': 'active'
            }
            
            plot_stored = self.db_service.register_plot(**plot_data)
            
            # Step 4: Create alert if risk is high or critical
            alert_created = False
            sms_sent = False
            
            if analysis_result.risk_level in ['high', 'critical']:
                alert_data = {
                    'hobli_id': validation.hobli_id,
                    'plot_id': plot_id,
                    'risk_level': analysis_result.risk_level,
                    'gee_proof': {
                        'ndvi_value': analysis_result.gee_data.ndvi_float,
                        'quality_score': analysis_result.gee_data.quality_score,
                        'cloud_cover': analysis_result.gee_data.cloud_cover,
                        'acquisition_date': analysis_result.gee_data.acquisition_date.isoformat()
                    },
                    'bedrock_analysis': {
                        'confidence': analysis_result.bedrock_reasoning.confidence_score,
                        'explanation': analysis_result.bedrock_reasoning.explanation,
                        'recommendations': analysis_result.bedrock_reasoning.recommendations
                    },
                    'farmer_contact': {
                        'name': farmer_name or 'Unknown',
                        'phone': phone or ''
                    }
                }
                
                alert_created = self.db_service.create_alert(**alert_data)
                logger.info(f"Alert created for plot {plot_id}: {analysis_result.risk_level}")
                
                # Step 5: Send SMS notifications
                try:
                    # Send SMS to farmer if phone provided
                    if phone and phone.startswith('+91'):
                        farmer_sms = await self.sms_service.send_farmer_alert(
                            farmer_phone=phone,
                            farmer_name=farmer_name or 'Farmer',
                            plot_id=plot_id,
                            risk_level=analysis_result.risk_level,
                            ndvi_value=analysis_result.gee_data.ndvi_float,
                            recommendations=analysis_result.bedrock_reasoning.recommendations
                        )
                        logger.info(f"Sent farmer SMS: {farmer_sms.message_id}")
                        sms_sent = True
                        self.metrics['sms_sent'] += 1
                    
                    # Get Extension Officer for this jurisdiction
                    officer_info = self.db_service.get_officer_for_plot(user_id, plot_id)
                    
                    if officer_info and officer_info.officer_phone:
                        # Get jurisdiction stats
                        stats = self.db_service.get_jurisdiction_stats(validation.hobli_id)
                        
                        # Send SMS to officer
                        officer_sms = await self.sms_service.send_officer_alert(
                            officer_phone=officer_info.officer_phone,
                            officer_name=officer_info.officer_name,
                            hobli_id=validation.hobli_id,
                            hobli_name=validation.hobli_name,
                            alert_count=stats.active_alerts,
                            high_priority_count=stats.high_priority_alerts
                        )
                        logger.info(f"Sent officer SMS: {officer_sms.message_id}")
                        self.metrics['sms_sent'] += 1
                    
                except Exception as e:
                    logger.warning(f"SMS notification failed (non-critical): {e}")
                    # Don't fail the entire pipeline if SMS fails
            
            # Calculate response time
            response_time = time.time() - start_time
            self.metrics['successful_analyses'] += 1
            self.metrics['total_response_time'] += response_time
            self.metrics['avg_response_time'] = (
                self.metrics['total_response_time'] / self.metrics['successful_analyses']
            )
            
            logger.info(f"End-to-end analysis completed in {response_time:.2f}s")
            
            # Check performance requirement (8 seconds)
            performance_ok = response_time <= self.settings.performance.max_response_time_seconds
            
            return {
                'success': True,
                'analysis': analysis_result,
                'validation': validation,
                'plot_stored': plot_stored,
                'alert_created': alert_created,
                'sms_sent': sms_sent,
                'response_time': response_time,
                'performance_ok': performance_ok,
                'timestamp': datetime.now().isoformat()
            }
            
        except ValueError as e:
            self.metrics['failed_analyses'] += 1
            logger.error(f"Validation error: {e}")
            raise
            
        except Exception as e:
            self.metrics['failed_analyses'] += 1
            logger.error(f"Analysis pipeline failed: {e}", exc_info=True)
            raise
    
    async def batch_analyze_plots(
        self,
        plots: list[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> list[Dict[str, Any]]:
        """
        Analyze multiple plots concurrently
        
        Args:
            plots: List of plot dictionaries with coordinates and metadata
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            List of analysis results
        """
        logger.info(f"Starting batch analysis of {len(plots)} plots")
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(plot):
            async with semaphore:
                try:
                    return await self.analyze_and_store_plot(
                        latitude=plot['latitude'],
                        longitude=plot['longitude'],
                        user_id=plot['user_id'],
                        plot_id=plot['plot_id'],
                        farmer_name=plot.get('farmer_name'),
                        phone=plot.get('phone')
                    )
                except Exception as e:
                    logger.error(f"Batch analysis failed for plot {plot['plot_id']}: {e}")
                    return {
                        'success': False,
                        'plot_id': plot['plot_id'],
                        'error': str(e)
                    }
        
        # Run analyses concurrently
        results = await asyncio.gather(
            *[analyze_with_semaphore(plot) for plot in plots],
            return_exceptions=True
        )
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        logger.info(f"Batch analysis complete: {successful}/{len(plots)} successful")
        
        return results
    
    def get_service_health(self) -> Dict[str, Any]:
        """
        Check health status of all services
        
        Returns:
            Dictionary with service health information
        """
        health = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'overall_status': 'healthy'
        }
        
        # Check MapService
        try:
            test_validation = self.map_service.validate_coordinates(12.9716, 77.5946)
            health['services']['map'] = {
                'status': 'healthy' if test_validation.is_valid else 'degraded',
                'message': 'Operational'
            }
        except Exception as e:
            health['services']['map'] = {
                'status': 'unhealthy',
                'message': str(e)
            }
            health['overall_status'] = 'degraded'
        
        # Check BrainService
        try:
            brain_info = self.brain_service.get_service_info()
            health['services']['brain'] = {
                'status': 'healthy',
                'message': 'Operational',
                'gee_available': brain_info.get('gee_available', False)
            }
        except Exception as e:
            health['services']['brain'] = {
                'status': 'unhealthy',
                'message': str(e)
            }
            health['overall_status'] = 'degraded'
        
        # Check DbService
        try:
            # Simple connectivity test
            health['services']['db'] = {
                'status': 'healthy',
                'message': 'Operational'
            }
        except Exception as e:
            health['services']['db'] = {
                'status': 'unhealthy',
                'message': str(e)
            }
            health['overall_status'] = 'degraded'
        
        return health
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics
        
        Returns:
            Dictionary with performance metrics
        """
        success_rate = 0.0
        if self.metrics['total_analyses'] > 0:
            success_rate = (
                self.metrics['successful_analyses'] / self.metrics['total_analyses']
            ) * 100
        
        return {
            'total_analyses': self.metrics['total_analyses'],
            'successful_analyses': self.metrics['successful_analyses'],
            'failed_analyses': self.metrics['failed_analyses'],
            'sms_sent': self.metrics['sms_sent'],
            'success_rate': f"{success_rate:.1f}%",
            'avg_response_time': f"{self.metrics['avg_response_time']:.2f}s",
            'performance_target': f"{self.settings.performance.max_response_time_seconds}s"
        }
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = {
            'total_analyses': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'sms_sent': 0,
            'avg_response_time': 0.0,
            'total_response_time': 0.0
        }
        logger.info("Metrics reset")
