"""
Unit tests for SentryService

Tests proactive monitoring, urgency classification, and notification triggering.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

from services.sentry_service import SentryService, ScanResult
from services.brain_service import AnalysisResult, BedrockResponse
from services.gee_service import GEEData
from services.sentinel_service import SentinelData
from services.db_service import DbService
from services.sms_service import SMSService


@pytest.fixture
def mock_brain_service():
    """Mock BrainService for testing"""
    service = Mock()
    service.analyze_plot = AsyncMock()
    return service


@pytest.fixture
def mock_db_service():
    """Mock DbService for testing"""
    service = Mock()
    service.get_all_plots = AsyncMock()
    service.create_alert = AsyncMock()
    service.get_officer_by_hobli = AsyncMock()
    return service


@pytest.fixture
def mock_sms_service():
    """Mock SMSService for testing"""
    service = Mock()
    service.send_farmer_alert = AsyncMock()
    service.send_officer_alert = AsyncMock()
    return service


@pytest.fixture
def sentry_service(mock_brain_service, mock_db_service, mock_sms_service):
    """Create SentryService instance with mocked dependencies"""
    return SentryService(
        brain_service=mock_brain_service,
        db_service=mock_db_service,
        sms_service=mock_sms_service
    )


@pytest.fixture
def sample_plot_data():
    """Sample plot data for testing"""
    return {
        'plot_id': 'plot_001',
        'user_id': 'farmer_001',
        'latitude': 12.9716,
        'longitude': 77.5946,
        'hobli_id': 'hobli_001',
        'farmer_name': 'Test Farmer',
        'phone': '+919876543210',
        'crop_type': 'Rice',
        'area_hectares': 2.5
    }


@pytest.fixture
def sample_analysis_result():
    """Sample analysis result for testing"""
    return AnalysisResult(
        gee_data=GEEData(
            ndvi_float=0.25,
            acquisition_date=datetime.now(),
            cloud_cover=10.0,
            metadata={'sensor': 'MODIS', 'source': 'GEE'},
            quality_score=0.85
        ),
        sentinel_data=SentinelData(
            tile_id='T43PGQ',
            image_url='https://example.com/image.jpg',
            acquisition_date=datetime.now(),
            cloud_cover_percentage=10.0,
            resolution='10m',
            quality_assessment='usable',
            metadata={}
        ),
        bedrock_reasoning=BedrockResponse(
            risk_classification='high',
            confidence_score=0.85,
            explanation='Low NDVI indicates severe crop stress. Immediate irrigation needed.',
            visual_observations='Satellite imagery shows stressed vegetation with low chlorophyll content.',
            recommendations=[
                'Immediate irrigation required',
                'Check for pest infestation',
                'Apply nitrogen fertilizer'
            ]
        ),
        risk_level='high',
        confidence=0.85,
        analysis_timestamp=datetime.now()
    )


class TestSentryServiceInitialization:
    """Test SentryService initialization"""
    
    def test_initialization(self, sentry_service):
        """Test service initializes correctly"""
        assert sentry_service is not None
        assert sentry_service.urgency_threshold == 'high'
        assert sentry_service.max_concurrent_scans == 5
        assert sentry_service.metrics['total_scans'] == 0
    
    def test_metrics_initialization(self, sentry_service):
        """Test metrics are initialized to zero"""
        metrics = sentry_service.metrics
        assert metrics['total_scans'] == 0
        assert metrics['alerts_triggered'] == 0
        assert metrics['sms_sent'] == 0
        assert metrics['high_urgency_plots'] == 0
        assert metrics['scan_failures'] == 0


class TestUrgencyClassification:
    """Test urgency classification logic"""
    
    def test_critical_risk_is_high_urgency(self, sentry_service, sample_analysis_result):
        """Test critical risk level results in high urgency"""
        sample_analysis_result.risk_level = 'critical'
        urgency = sentry_service._classify_urgency(sample_analysis_result)
        assert urgency == 'high'
    
    def test_high_risk_low_ndvi_is_high_urgency(self, sentry_service, sample_analysis_result):
        """Test high risk with low NDVI results in high urgency"""
        sample_analysis_result.risk_level = 'high'
        sample_analysis_result.gee_data.ndvi_float = 0.25
        urgency = sentry_service._classify_urgency(sample_analysis_result)
        assert urgency == 'high'
    
    def test_urgent_keywords_trigger_high_urgency(self, sentry_service, sample_analysis_result):
        """Test urgency keywords in reasoning trigger high urgency"""
        sample_analysis_result.risk_level = 'medium'
        sample_analysis_result.bedrock_reasoning.explanation = 'Urgent action required to prevent crop failure'
        urgency = sentry_service._classify_urgency(sample_analysis_result)
        assert urgency == 'high'
    
    def test_high_risk_is_medium_urgency(self, sentry_service, sample_analysis_result):
        """Test high risk with normal NDVI results in medium urgency"""
        sample_analysis_result.risk_level = 'high'
        sample_analysis_result.gee_data.ndvi_float = 0.6
        sample_analysis_result.bedrock_reasoning.explanation = 'Some stress detected'
        urgency = sentry_service._classify_urgency(sample_analysis_result)
        assert urgency == 'medium'
    
    def test_medium_risk_low_ndvi_is_medium_urgency(self, sentry_service, sample_analysis_result):
        """Test medium risk with low NDVI results in medium urgency"""
        sample_analysis_result.risk_level = 'medium'
        sample_analysis_result.gee_data.ndvi_float = 0.35
        urgency = sentry_service._classify_urgency(sample_analysis_result)
        assert urgency == 'medium'
    
    def test_low_risk_is_low_urgency(self, sentry_service, sample_analysis_result):
        """Test low risk results in low urgency"""
        sample_analysis_result.risk_level = 'low'
        sample_analysis_result.gee_data.ndvi_float = 0.7
        urgency = sentry_service._classify_urgency(sample_analysis_result)
        assert urgency == 'low'


class TestSinglePlotScan:
    """Test single plot scanning"""
    
    @pytest.mark.asyncio
    async def test_scan_single_plot_success(
        self,
        sentry_service,
        mock_brain_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test successful single plot scan"""
        # Setup mock
        mock_brain_service.analyze_plot.return_value = sample_analysis_result
        
        # Execute scan
        result = await sentry_service.scan_single_plot(sample_plot_data)
        
        # Verify
        assert isinstance(result, ScanResult)
        assert result.plot_id == 'plot_001'
        assert result.user_id == 'farmer_001'
        assert result.risk_level == 'high'
        assert result.urgency == 'high'
        assert result.ndvi == 0.25
        assert result.confidence == 0.85
        assert result.alert_triggered is True
        assert sentry_service.metrics['total_scans'] == 1
    
    @pytest.mark.asyncio
    async def test_scan_low_urgency_no_alert(
        self,
        sentry_service,
        mock_brain_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test low urgency scan does not trigger alert"""
        # Setup mock with low risk
        sample_analysis_result.risk_level = 'low'
        sample_analysis_result.gee_data.ndvi_float = 0.7
        mock_brain_service.analyze_plot.return_value = sample_analysis_result
        
        # Execute scan
        result = await sentry_service.scan_single_plot(sample_plot_data)
        
        # Verify no alert triggered
        assert result.urgency == 'low'
        assert result.alert_triggered is False
        assert result.sms_sent is False
        assert sentry_service.metrics['alerts_triggered'] == 0
    
    @pytest.mark.asyncio
    async def test_scan_handles_analysis_failure(
        self,
        sentry_service,
        mock_brain_service,
        sample_plot_data
    ):
        """Test scan handles analysis failures gracefully"""
        # Setup mock to raise exception
        mock_brain_service.analyze_plot.side_effect = Exception('Analysis failed')
        
        # Execute scan
        result = await sentry_service.scan_single_plot(sample_plot_data)
        
        # Verify failure is handled
        assert result.risk_level == 'unknown'
        assert result.urgency == 'unknown'
        assert result.alert_triggered is False
        assert sentry_service.metrics['scan_failures'] == 1


class TestAlertCreation:
    """Test alert creation in database"""
    
    @pytest.mark.asyncio
    async def test_create_alert_success(
        self,
        sentry_service,
        mock_db_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test successful alert creation"""
        # Setup mock
        mock_db_service.create_alert.return_value = 'alert_123'
        
        # Execute
        alert_id = await sentry_service._create_alert(
            plot_data=sample_plot_data,
            analysis=sample_analysis_result,
            urgency='high'
        )
        
        # Verify
        assert alert_id == 'alert_123'
        mock_db_service.create_alert.assert_called_once()
        
        # Check call arguments
        call_args = mock_db_service.create_alert.call_args[1]
        assert call_args['plot_id'] == 'plot_001'
        assert call_args['user_id'] == 'farmer_001'
        assert call_args['risk_level'] == 'high'
        assert call_args['ndvi'] == 0.25
        assert call_args['metadata']['urgency'] == 'high'
        assert call_args['metadata']['sentry_scan'] is True
    
    @pytest.mark.asyncio
    async def test_create_alert_handles_failure(
        self,
        sentry_service,
        mock_db_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test alert creation handles database failures"""
        # Setup mock to raise exception
        mock_db_service.create_alert.side_effect = Exception('DB error')
        
        # Execute
        alert_id = await sentry_service._create_alert(
            plot_data=sample_plot_data,
            analysis=sample_analysis_result,
            urgency='high'
        )
        
        # Verify fallback alert ID is generated
        assert alert_id.startswith('alert-plot_001-')


class TestSMSNotifications:
    """Test SMS notification sending"""
    
    @pytest.mark.asyncio
    async def test_send_farmer_notification(
        self,
        sentry_service,
        mock_sms_service,
        mock_db_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test farmer SMS notification is sent"""
        # Setup mocks
        mock_sms_service.send_farmer_alert.return_value = None
        mock_db_service.get_officer_by_hobli.return_value = None
        
        # Execute
        sms_sent = await sentry_service._send_notifications(
            plot_data=sample_plot_data,
            analysis=sample_analysis_result,
            alert_id='alert_123'
        )
        
        # Verify
        assert sms_sent is True
        mock_sms_service.send_farmer_alert.assert_called_once()
        
        # Check call arguments
        call_args = mock_sms_service.send_farmer_alert.call_args[1]
        assert call_args['phone'] == '+919876543210'
        assert call_args['farmer_name'] == 'Test Farmer'
        assert call_args['plot_id'] == 'plot_001'
    
    @pytest.mark.asyncio
    async def test_send_officer_notification(
        self,
        sentry_service,
        mock_sms_service,
        mock_db_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test officer SMS notification is sent"""
        # Setup mocks
        mock_db_service.get_officer_by_hobli.return_value = {
            'officer_id': 'officer_001',
            'name': 'Test Officer',
            'phone': '+919876543211'
        }
        mock_sms_service.send_officer_alert.return_value = None
        
        # Execute
        sms_sent = await sentry_service._send_notifications(
            plot_data=sample_plot_data,
            analysis=sample_analysis_result,
            alert_id='alert_123'
        )
        
        # Verify
        assert sms_sent is True
        mock_sms_service.send_officer_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_notification_handles_sms_failure(
        self,
        sentry_service,
        mock_sms_service,
        mock_db_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test notification handles SMS failures gracefully"""
        # Setup mock to raise exception
        mock_sms_service.send_farmer_alert.side_effect = Exception('SMS failed')
        mock_db_service.get_officer_by_hobli.return_value = None
        
        # Execute
        sms_sent = await sentry_service._send_notifications(
            plot_data=sample_plot_data,
            analysis=sample_analysis_result,
            alert_id='alert_123'
        )
        
        # Verify failure is handled
        assert sms_sent is False


class TestDailyScanSimulation:
    """Test daily scan simulation for all plots"""
    
    @pytest.mark.asyncio
    async def test_scan_all_plots_success(
        self,
        sentry_service,
        mock_db_service,
        mock_brain_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test successful scan of all registered plots"""
        # Setup mocks
        plots = [sample_plot_data, {**sample_plot_data, 'plot_id': 'plot_002'}]
        mock_db_service.get_all_plots.return_value = plots
        mock_brain_service.analyze_plot.return_value = sample_analysis_result
        
        # Execute
        result = await sentry_service.scan_all_registered_plots()
        
        # Verify
        assert result['status'] == 'completed'
        assert result['total_plots'] == 2
        assert result['scanned'] == 2
        assert result['alerts_triggered'] == 2  # Both high urgency
        assert 'duration_seconds' in result
        assert 'results' in result
    
    @pytest.mark.asyncio
    async def test_scan_all_plots_with_limit(
        self,
        sentry_service,
        mock_db_service,
        mock_brain_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test scan respects max_plots limit"""
        # Setup mocks
        plots = [sample_plot_data]
        mock_db_service.get_all_plots.return_value = plots
        mock_brain_service.analyze_plot.return_value = sample_analysis_result
        
        # Execute with limit
        result = await sentry_service.scan_all_registered_plots(max_plots=1)
        
        # Verify
        mock_db_service.get_all_plots.assert_called_once_with(limit=1)
        assert result['total_plots'] == 1
    
    @pytest.mark.asyncio
    async def test_scan_all_plots_no_plots(
        self,
        sentry_service,
        mock_db_service
    ):
        """Test scan handles no registered plots"""
        # Setup mock
        mock_db_service.get_all_plots.return_value = []
        
        # Execute
        result = await sentry_service.scan_all_registered_plots()
        
        # Verify
        assert result['status'] == 'completed'
        assert result['total_plots'] == 0
        assert result['scanned'] == 0
        assert result['alerts_triggered'] == 0
    
    @pytest.mark.asyncio
    async def test_scan_all_plots_handles_failure(
        self,
        sentry_service,
        mock_db_service
    ):
        """Test scan handles database failures"""
        # Setup mock to raise exception
        mock_db_service.get_all_plots.side_effect = Exception('DB error')
        
        # Execute
        result = await sentry_service.scan_all_registered_plots()
        
        # Verify
        assert result['status'] == 'failed'
        assert 'error' in result


class TestDeepLinkGeneration:
    """Test deep link URL generation"""
    
    def test_generate_deep_link(self, sentry_service):
        """Test deep link generation"""
        deep_link = sentry_service._generate_deep_link('plot_001', 'alert_123')
        
        assert 'plot_id=plot_001' in deep_link
        assert 'alert_id=alert_123' in deep_link
        assert deep_link.startswith('http')


class TestMetrics:
    """Test metrics tracking"""
    
    def test_get_metrics(self, sentry_service):
        """Test metrics retrieval"""
        metrics = sentry_service.get_metrics()
        
        assert 'service' in metrics
        assert metrics['service'] == 'SentryService'
        assert 'metrics' in metrics
        assert 'configuration' in metrics
        assert metrics['configuration']['urgency_threshold'] == 'high'
        assert metrics['configuration']['max_concurrent_scans'] == 5
    
    @pytest.mark.asyncio
    async def test_metrics_update_on_scan(
        self,
        sentry_service,
        mock_brain_service,
        sample_plot_data,
        sample_analysis_result
    ):
        """Test metrics are updated after scans"""
        # Setup mock
        mock_brain_service.analyze_plot.return_value = sample_analysis_result
        
        # Execute scan
        await sentry_service.scan_single_plot(sample_plot_data)
        
        # Verify metrics updated
        assert sentry_service.metrics['total_scans'] == 1
        assert sentry_service.metrics['alerts_triggered'] == 1
        assert sentry_service.metrics['high_urgency_plots'] == 1
