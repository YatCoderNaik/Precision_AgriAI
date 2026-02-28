"""
SentryService - Proactive Plot Monitoring

Handles automated background scanning of registered plots:
- Daily scan simulation for all registered plots
- Urgency classification using AI reasoning
- Automatic alert generation for high-risk plots
- SMS notification triggering for farmers and officers
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from services.brain_service import BrainService
from services.db_service import DbService
from services.sms_service import SMSService
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ScanResult(BaseModel):
    """Result of a single plot scan"""
    plot_id: str
    user_id: str
    latitude: float
    longitude: float
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    urgency: str  # 'low', 'medium', 'high'
    ndvi: float
    confidence: float
    recommendations: List[str]
    alert_triggered: bool
    sms_sent: bool
    scan_timestamp: datetime
    processing_time_ms: int


class SentryService:
    """Service for proactive plot monitoring and alerting"""
    
    def __init__(
        self,
        brain_service: BrainService,
        db_service: DbService,
        sms_service: SMSService
    ):
        """
        Initialize SentryService
        
        Args:
            brain_service: BrainService for plot analysis
            db_service: DbService for plot and alert management
            sms_service: SMSService for notifications
        """
        self.brain_service = brain_service
        self.db_service = db_service
        self.sms_service = sms_service
        self.settings = get_settings()
        
        # Sentry configuration
        self.urgency_threshold = 'high'  # Only alert on high urgency
        self.max_concurrent_scans = 5  # Limit concurrent processing
        
        # Metrics
        self.metrics = {
            'total_scans': 0,
            'alerts_triggered': 0,
            'sms_sent': 0,
            'high_urgency_plots': 0,
            'scan_failures': 0
        }
        
        logger.info("SentryService initialized for proactive monitoring")
    
    async def scan_single_plot(
        self,
        plot_data: Dict[str, Any]
    ) -> ScanResult:
        """
        Scan a single plot and determine if alert is needed
        
        Args:
            plot_data: Plot information from DbService
            
        Returns:
            ScanResult with analysis and alert status
        """
        start_time = datetime.now()
        self.metrics['total_scans'] += 1
        
        plot_id = plot_data['plot_id']
        user_id = plot_data['user_id']
        latitude = plot_data['latitude']
        longitude = plot_data['longitude']
        
        try:
            logger.info(f"Scanning plot {plot_id} at ({latitude}, {longitude})")
            
            # Run full AI analysis
            analysis = await self.brain_service.analyze_plot(
                latitude=latitude,
                longitude=longitude
            )
            
            # Classify urgency based on AI reasoning
            urgency = self._classify_urgency(analysis)
            
            # Determine if alert should be triggered
            alert_triggered = urgency == 'high'
            sms_sent = False
            
            if alert_triggered:
                self.metrics['alerts_triggered'] += 1
                self.metrics['high_urgency_plots'] += 1
                
                # Create alert in database
                alert_id = await self._create_alert(
                    plot_data=plot_data,
                    analysis=analysis,
                    urgency=urgency
                )
                
                # Send SMS notifications
                sms_sent = await self._send_notifications(
                    plot_data=plot_data,
                    analysis=analysis,
                    alert_id=alert_id
                )
                
                if sms_sent:
                    self.metrics['sms_sent'] += 1
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ScanResult(
                plot_id=plot_id,
                user_id=user_id,
                latitude=latitude,
                longitude=longitude,
                risk_level=analysis.risk_level,
                urgency=urgency,
                ndvi=analysis.gee_data.ndvi_float,
                confidence=analysis.confidence,
                recommendations=analysis.bedrock_reasoning.recommendations,
                alert_triggered=alert_triggered,
                sms_sent=sms_sent,
                scan_timestamp=datetime.now(),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            self.metrics['scan_failures'] += 1
            logger.error(f"Failed to scan plot {plot_id}: {e}", exc_info=True)
            
            # Return failure result
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return ScanResult(
                plot_id=plot_id,
                user_id=user_id,
                latitude=latitude,
                longitude=longitude,
                risk_level='unknown',
                urgency='unknown',
                ndvi=0.0,
                confidence=0.0,
                recommendations=[],
                alert_triggered=False,
                sms_sent=False,
                scan_timestamp=datetime.now(),
                processing_time_ms=processing_time
            )
    
    def _classify_urgency(self, analysis) -> str:
        """
        Classify urgency based on AI analysis
        
        Uses AI reasoning, risk level, and NDVI to determine urgency.
        
        Args:
            analysis: AnalysisResult from BrainService
            
        Returns:
            Urgency level: 'low', 'medium', or 'high'
        """
        # Check for critical risk level
        if analysis.risk_level == 'critical':
            return 'high'
        
        # Check for high risk with low NDVI
        if analysis.risk_level == 'high' and analysis.gee_data.ndvi_float < 0.3:
            return 'high'
        
        # Check AI reasoning for urgency keywords
        reasoning_lower = analysis.bedrock_reasoning.explanation.lower()
        urgency_keywords = [
            'urgent', 'immediate', 'critical', 'severe', 'emergency',
            'rapid', 'quickly', 'soon', 'asap', 'priority'
        ]
        
        if any(keyword in reasoning_lower for keyword in urgency_keywords):
            return 'high'
        
        # Medium urgency for high risk
        if analysis.risk_level == 'high':
            return 'medium'
        
        # Medium urgency for medium risk with low NDVI
        if analysis.risk_level == 'medium' and analysis.gee_data.ndvi_float < 0.4:
            return 'medium'
        
        # Default to low urgency
        return 'low'
    
    async def _create_alert(
        self,
        plot_data: Dict[str, Any],
        analysis,
        urgency: str
    ) -> str:
        """
        Create alert in database
        
        Args:
            plot_data: Plot information
            analysis: AnalysisResult from BrainService
            urgency: Urgency classification
            
        Returns:
            Alert ID
        """
        try:
            alert_id = await self.db_service.create_alert(
                plot_id=plot_data['plot_id'],
                user_id=plot_data['user_id'],
                hobli_id=plot_data.get('hobli_id', 'unknown'),
                risk_level=analysis.risk_level,
                ndvi=analysis.gee_data.ndvi_float,
                confidence=analysis.confidence,
                recommendations=analysis.bedrock_reasoning.recommendations,
                metadata={
                    'urgency': urgency,
                    'sentry_scan': True,
                    'scan_timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Created alert {alert_id} for plot {plot_data['plot_id']}")
            return alert_id
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return f"alert-{plot_data['plot_id']}-{int(datetime.now().timestamp())}"
    
    async def _send_notifications(
        self,
        plot_data: Dict[str, Any],
        analysis,
        alert_id: str
    ) -> bool:
        """
        Send SMS notifications to farmer and officer
        
        Args:
            plot_data: Plot information
            analysis: AnalysisResult from BrainService
            alert_id: Alert ID for deep linking
            
        Returns:
            True if at least one SMS was sent successfully
        """
        sms_sent = False
        
        try:
            # Send to farmer if phone available
            if plot_data.get('phone'):
                try:
                    await self.sms_service.send_farmer_alert(
                        phone=plot_data['phone'],
                        farmer_name=plot_data.get('farmer_name', 'Farmer'),
                        plot_id=plot_data['plot_id'],
                        risk_level=analysis.risk_level,
                        ndvi=analysis.gee_data.ndvi_float,
                        recommendations=analysis.bedrock_reasoning.recommendations[:2],  # Top 2 recommendations
                        deep_link_url=self._generate_deep_link(plot_data['plot_id'], alert_id)
                    )
                    sms_sent = True
                    logger.info(f"Sent farmer SMS for plot {plot_data['plot_id']}")
                except Exception as e:
                    logger.error(f"Failed to send farmer SMS: {e}")
            
            # Send to Extension Officer
            hobli_id = plot_data.get('hobli_id')
            if hobli_id:
                try:
                    # Get officer contact from jurisdiction directory
                    officer_info = await self.db_service.get_officer_by_hobli(hobli_id)
                    
                    if officer_info and officer_info.get('phone'):
                        await self.sms_service.send_officer_alert(
                            phone=officer_info['phone'],
                            officer_name=officer_info.get('name', 'Officer'),
                            hobli_id=hobli_id,
                            alert_count=1,
                            high_risk_plots=[plot_data['plot_id']],
                            deep_link_url=self._generate_deep_link(plot_data['plot_id'], alert_id)
                        )
                        sms_sent = True
                        logger.info(f"Sent officer SMS for hobli {hobli_id}")
                except Exception as e:
                    logger.error(f"Failed to send officer SMS: {e}")
            
            return sms_sent
            
        except Exception as e:
            logger.error(f"Notification sending failed: {e}")
            return False
    
    def _generate_deep_link(self, plot_id: str, alert_id: str) -> str:
        """
        Generate deep link URL for Streamlit app
        
        Args:
            plot_id: Plot ID
            alert_id: Alert ID
            
        Returns:
            Deep link URL
        """
        # In production, this would be the actual app URL
        base_url = self.settings.app_url if hasattr(self.settings, 'app_url') else 'http://localhost:8501'
        return f"{base_url}?plot_id={plot_id}&alert_id={alert_id}"
    
    async def scan_all_registered_plots(
        self,
        max_plots: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Scan all registered plots (Daily Scan Simulation)
        
        Args:
            max_plots: Optional limit on number of plots to scan
            
        Returns:
            Dictionary with scan summary and results
        """
        start_time = datetime.now()
        
        try:
            logger.info("Starting daily scan simulation for all registered plots")
            
            # Get all registered plots
            plots = await self.db_service.get_all_plots(limit=max_plots)
            
            if not plots:
                logger.warning("No registered plots found for scanning")
                return {
                    'status': 'completed',
                    'total_plots': 0,
                    'scanned': 0,
                    'alerts_triggered': 0,
                    'sms_sent': 0,
                    'duration_seconds': 0
                }
            
            logger.info(f"Found {len(plots)} plots to scan")
            
            # Scan plots with concurrency limit
            semaphore = asyncio.Semaphore(self.max_concurrent_scans)
            
            async def scan_with_limit(plot):
                async with semaphore:
                    return await self.scan_single_plot(plot)
            
            # Execute scans concurrently
            scan_results = await asyncio.gather(
                *[scan_with_limit(plot) for plot in plots],
                return_exceptions=True
            )
            
            # Process results
            successful_scans = [r for r in scan_results if isinstance(r, ScanResult)]
            alerts_triggered = sum(1 for r in successful_scans if r.alert_triggered)
            sms_sent = sum(1 for r in successful_scans if r.sms_sent)
            high_urgency = sum(1 for r in successful_scans if r.urgency == 'high')
            
            duration = (datetime.now() - start_time).total_seconds()
            
            summary = {
                'status': 'completed',
                'total_plots': len(plots),
                'scanned': len(successful_scans),
                'alerts_triggered': alerts_triggered,
                'sms_sent': sms_sent,
                'high_urgency_plots': high_urgency,
                'scan_failures': len(plots) - len(successful_scans),
                'duration_seconds': duration,
                'avg_scan_time_ms': sum(r.processing_time_ms for r in successful_scans) / len(successful_scans) if successful_scans else 0,
                'scan_timestamp': datetime.now().isoformat(),
                'results': [r.dict() for r in successful_scans]
            }
            
            logger.info(f"Daily scan completed: {len(successful_scans)}/{len(plots)} plots scanned, {alerts_triggered} alerts triggered")
            
            return summary
            
        except Exception as e:
            logger.error(f"Daily scan failed: {e}", exc_info=True)
            duration = (datetime.now() - start_time).total_seconds()
            return {
                'status': 'failed',
                'error': str(e),
                'duration_seconds': duration
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get sentry service metrics
        
        Returns:
            Dictionary with service metrics
        """
        return {
            'service': 'SentryService',
            'metrics': self.metrics.copy(),
            'configuration': {
                'urgency_threshold': self.urgency_threshold,
                'max_concurrent_scans': self.max_concurrent_scans
            }
        }
