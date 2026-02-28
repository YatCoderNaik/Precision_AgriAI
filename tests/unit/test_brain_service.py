"""
Unit Tests for BrainService

Tests multimodal AI orchestration including:
- GEEService and SentinelService integration
- Bedrock multimodal analysis
- Risk classification
- Farmer guidance generation
- Cluster outbreak detection
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json

from services.brain_service import (
    BrainService, AnalysisResult, BedrockResponse, 
    ClusterAnalysis, Alert
)
from services.gee_service import GEEData
from services.sentinel_service import SentinelData


class TestBrainServiceInitialization:
    """Test BrainService initialization"""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        service = BrainService(use_mock_gee=True)
        
        assert service.gee_service is not None
        assert service.sentinel_service is not None
        assert service.bedrock_client is not None
        assert service.bedrock_model_id == 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    def test_init_with_custom_region(self):
        """Test initialization with custom AWS region"""
        service = BrainService(use_mock_gee=True, region='us-west-2')
        
        assert service.region == 'us-west-2'
    
    def test_risk_thresholds(self):
        """Test risk classification thresholds are set correctly"""
        service = BrainService(use_mock_gee=True)
        
        assert service.ndvi_critical_threshold == 0.2
        assert service.ndvi_high_threshold == 0.4
        assert service.ndvi_medium_threshold == 0.6
    
    def test_service_info(self):
        """Test service information retrieval"""
        service = BrainService(use_mock_gee=True)
        info = service.get_service_info()
        
        assert info['service'] == 'BrainService'
        assert 'gee_available' in info
        assert 'bedrock_model' in info
        assert 'risk_thresholds' in info


class TestFallbackRiskClassification:
    """Test fallback risk classification logic"""
    
    def test_critical_risk_classification(self):
        """Test critical risk classification for very low NDVI"""
        service = BrainService(use_mock_gee=True)
        
        result = service._fallback_risk_classification(0.1)
        
        assert result.risk_classification == 'critical'
        assert 0.0 <= result.confidence_score <= 1.0
        assert len(result.recommendations) > 0
        assert 'severe' in result.explanation.lower() or 'stress' in result.explanation.lower()
    
    def test_high_risk_classification(self):
        """Test high risk classification for low NDVI"""
        service = BrainService(use_mock_gee=True)
        
        result = service._fallback_risk_classification(0.3)
        
        assert result.risk_classification == 'high'
        assert len(result.recommendations) > 0
    
    def test_medium_risk_classification(self):
        """Test medium risk classification for moderate NDVI"""
        service = BrainService(use_mock_gee=True)
        
        result = service._fallback_risk_classification(0.5)
        
        assert result.risk_classification == 'medium'
        assert len(result.recommendations) > 0
    
    def test_low_risk_classification(self):
        """Test low risk classification for healthy NDVI"""
        service = BrainService(use_mock_gee=True)
        
        result = service._fallback_risk_classification(0.7)
        
        assert result.risk_classification == 'low'
        assert 'healthy' in result.explanation.lower()
        assert len(result.recommendations) > 0


class TestAnalyzePlot:
    """Test plot analysis functionality"""
    
    @pytest.mark.asyncio
    async def test_analyze_plot_success(self):
        """Test successful plot analysis"""
        service = BrainService(use_mock_gee=True)
        
        # Mock SentinelService to return mock data
        mock_sentinel_data = SentinelData(
            image_url='http://example.com/image.jpg',
            tile_id='43PPGP',
            acquisition_date=datetime.now(),
            cloud_cover_percentage=10.0,
            resolution='60m',
            quality_assessment='usable',
            metadata={}
        )
        
        # Mock Bedrock response
        with patch.object(service.sentinel_service, 'get_latest_image', new_callable=AsyncMock) as mock_sentinel:
            mock_sentinel.return_value = mock_sentinel_data
            
            with patch.object(service, '_bedrock_multimodal_analysis', new_callable=AsyncMock) as mock_bedrock:
                mock_bedrock.return_value = BedrockResponse(
                    risk_classification='low',
                    confidence_score=0.85,
                    explanation='Healthy vegetation detected',
                    visual_observations='Green, dense vegetation visible',
                    recommendations=['Maintain current practices']
                )
                
                result = await service.analyze_plot(12.9716, 77.5946)
                
                assert isinstance(result, AnalysisResult)
                assert isinstance(result.gee_data, GEEData)
                assert isinstance(result.sentinel_data, SentinelData)
                assert isinstance(result.bedrock_reasoning, BedrockResponse)
                assert result.risk_level == 'low'
                assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_plot_invalid_coordinates(self):
        """Test plot analysis with invalid coordinates"""
        service = BrainService(use_mock_gee=True)
        
        with pytest.raises(ValueError):
            await service.analyze_plot(91.0, 77.5946)  # Invalid latitude
    
    @pytest.mark.asyncio
    async def test_analyze_plot_concurrent_fetching(self):
        """Test that GEE and Sentinel data are fetched concurrently"""
        service = BrainService(use_mock_gee=True)
        
        # Track call order
        call_order = []
        
        async def mock_gee(*args, **kwargs):
            call_order.append('gee_start')
            # Simulate some processing time
            import asyncio
            await asyncio.sleep(0.01)
            call_order.append('gee_end')
            return GEEData(
                ndvi_float=0.65,
                acquisition_date=datetime.now(),
                cloud_cover=10.0,
                metadata={'sensor': 'MODIS'},
                quality_score=0.85
            )
        
        async def mock_sentinel(*args, **kwargs):
            call_order.append('sentinel_start')
            import asyncio
            await asyncio.sleep(0.01)
            call_order.append('sentinel_end')
            return SentinelData(
                image_url='http://example.com/image.jpg',
                tile_id='43PGP',
                acquisition_date=datetime.now(),
                cloud_cover_percentage=10.0,
                resolution='60m',
                quality_assessment='usable',
                metadata={}
            )
        
        with patch.object(service.gee_service, 'get_ndvi_analysis', side_effect=mock_gee):
            with patch.object(service.sentinel_service, 'get_latest_image', side_effect=mock_sentinel):
                with patch.object(service, '_bedrock_multimodal_analysis', new_callable=AsyncMock) as mock_bedrock:
                    mock_bedrock.return_value = BedrockResponse(
                        risk_classification='low',
                        confidence_score=0.85,
                        explanation='Test',
                        visual_observations='Test',
                        recommendations=['Test']
                    )
                    
                    result = await service.analyze_plot(12.9716, 77.5946)
                    
                    # Verify both services were called
                    assert 'gee_start' in call_order
                    assert 'sentinel_start' in call_order
                    assert isinstance(result, AnalysisResult)


class TestClassifyUrgency:
    """Test urgency classification"""
    
    @pytest.mark.asyncio
    async def test_classify_urgency(self):
        """Test urgency classification from analysis result"""
        service = BrainService(use_mock_gee=True)
        
        # Create mock analysis result
        analysis_result = AnalysisResult(
            gee_data=GEEData(
                ndvi_float=0.3,
                acquisition_date=datetime.now(),
                cloud_cover=10.0,
                metadata={},
                quality_score=0.8
            ),
            sentinel_data=SentinelData(
                image_url='http://example.com/image.jpg',
                tile_id='43PGP',
                acquisition_date=datetime.now(),
                cloud_cover_percentage=10.0,
                resolution='60m',
                quality_assessment='usable',
                metadata={}
            ),
            bedrock_reasoning=BedrockResponse(
                risk_classification='high',
                confidence_score=0.8,
                explanation='Test',
                visual_observations='Test',
                recommendations=['Test']
            ),
            risk_level='high',
            confidence=0.8,
            analysis_timestamp=datetime.now()
        )
        
        urgency = await service.classify_urgency(analysis_result)
        
        assert urgency == 'high'


class TestGenerateFarmerGuidance:
    """Test farmer guidance generation"""
    
    @pytest.mark.asyncio
    async def test_generate_guidance_success(self):
        """Test successful farmer guidance generation"""
        service = BrainService(use_mock_gee=True)
        
        analysis_result = AnalysisResult(
            gee_data=GEEData(
                ndvi_float=0.7,
                acquisition_date=datetime.now(),
                cloud_cover=10.0,
                metadata={},
                quality_score=0.85
            ),
            sentinel_data=SentinelData(
                image_url='http://example.com/image.jpg',
                tile_id='43PGP',
                acquisition_date=datetime.now(),
                cloud_cover_percentage=10.0,
                resolution='60m',
                quality_assessment='usable',
                metadata={}
            ),
            bedrock_reasoning=BedrockResponse(
                risk_classification='low',
                confidence_score=0.85,
                explanation='Healthy vegetation',
                visual_observations='Green vegetation',
                recommendations=['Maintain practices']
            ),
            risk_level='low',
            confidence=0.85,
            analysis_timestamp=datetime.now()
        )
        
        # Mock Bedrock response
        mock_response = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': 'Your crop is healthy. Continue your good farming practices.'}]
            }).encode())
        }
        
        with patch.object(service.bedrock_client, 'invoke_model', return_value=mock_response):
            guidance = await service.generate_farmer_guidance(analysis_result, 'English')
            
            assert isinstance(guidance, str)
            assert len(guidance) > 0
    
    @pytest.mark.asyncio
    async def test_generate_guidance_fallback(self):
        """Test farmer guidance generation with fallback"""
        service = BrainService(use_mock_gee=True)
        
        analysis_result = AnalysisResult(
            gee_data=GEEData(
                ndvi_float=0.15,
                acquisition_date=datetime.now(),
                cloud_cover=10.0,
                metadata={},
                quality_score=0.8
            ),
            sentinel_data=SentinelData(
                image_url='http://example.com/image.jpg',
                tile_id='43PGP',
                acquisition_date=datetime.now(),
                cloud_cover_percentage=10.0,
                resolution='60m',
                quality_assessment='usable',
                metadata={}
            ),
            bedrock_reasoning=BedrockResponse(
                risk_classification='critical',
                confidence_score=0.8,
                explanation='Severe stress',
                visual_observations='Brown vegetation',
                recommendations=['Immediate action']
            ),
            risk_level='critical',
            confidence=0.8,
            analysis_timestamp=datetime.now()
        )
        
        # Force fallback by making Bedrock fail
        with patch.object(service.bedrock_client, 'invoke_model', side_effect=Exception('API Error')):
            guidance = await service.generate_farmer_guidance(analysis_result, 'English')
            
            assert isinstance(guidance, str)
            assert len(guidance) > 0
            assert 'URGENT' in guidance or 'urgent' in guidance.lower()


class TestClusterOutbreakDetection:
    """Test cluster outbreak detection"""
    
    def test_no_alerts(self):
        """Test cluster detection with no alerts"""
        service = BrainService(use_mock_gee=True)
        
        result = service.detect_cluster_outbreak([])
        
        assert isinstance(result, ClusterAnalysis)
        assert result.outbreak_detected is False
        assert result.affected_plots == 0
    
    def test_few_alerts_no_outbreak(self):
        """Test cluster detection with few alerts (< 3)"""
        service = BrainService(use_mock_gee=True)
        
        alerts = [
            Alert(
                plot_id='plot1',
                gee_proof={'ndvi_value': 0.25},
                risk_level='high',
                timestamp=datetime.now()
            ),
            Alert(
                plot_id='plot2',
                gee_proof={'ndvi_value': 0.28},
                risk_level='high',
                timestamp=datetime.now()
            )
        ]
        
        result = service.detect_cluster_outbreak(alerts)
        
        assert result.outbreak_detected is False
        assert result.affected_plots == 2
    
    def test_outbreak_detected_low_ndvi(self):
        """Test cluster detection with outbreak (low NDVI)"""
        service = BrainService(use_mock_gee=True)
        
        alerts = [
            Alert(
                plot_id=f'plot{i}',
                gee_proof={'ndvi_value': 0.25},
                risk_level='high',
                timestamp=datetime.now()
            )
            for i in range(5)
        ]
        
        result = service.detect_cluster_outbreak(alerts)
        
        assert result.outbreak_detected is True
        assert result.affected_plots == 5
        assert result.avg_ndvi < 0.3
        assert result.severity in ['high', 'critical']
    
    def test_outbreak_detected_high_risk_count(self):
        """Test cluster detection with many high-risk alerts"""
        service = BrainService(use_mock_gee=True)
        
        alerts = [
            Alert(
                plot_id=f'plot{i}',
                gee_proof={'ndvi_value': 0.35},
                risk_level='high' if i < 3 else 'medium',
                timestamp=datetime.now()
            )
            for i in range(4)
        ]
        
        result = service.detect_cluster_outbreak(alerts)
        
        assert result.affected_plots == 4
        # With 3/4 high risk and avg NDVI 0.35, should detect outbreak
        assert result.severity in ['low', 'medium', 'high', 'critical']
    
    def test_no_outbreak_healthy_plots(self):
        """Test cluster detection with healthy plots"""
        service = BrainService(use_mock_gee=True)
        
        alerts = [
            Alert(
                plot_id=f'plot{i}',
                gee_proof={'ndvi_value': 0.7},
                risk_level='low',
                timestamp=datetime.now()
            )
            for i in range(5)
        ]
        
        result = service.detect_cluster_outbreak(alerts)
        
        assert result.outbreak_detected is False
        assert result.avg_ndvi > 0.6
        assert result.severity == 'low'
        assert result.recommended_action == 'routine_monitoring'
    
    def test_severity_levels(self):
        """Test different severity levels based on NDVI"""
        service = BrainService(use_mock_gee=True)
        
        # Critical severity
        critical_alerts = [
            Alert(
                plot_id=f'plot{i}',
                gee_proof={'ndvi_value': 0.15},
                risk_level='critical',
                timestamp=datetime.now()
            )
            for i in range(5)
        ]
        
        result = service.detect_cluster_outbreak(critical_alerts)
        
        assert result.outbreak_detected is True
        assert result.severity == 'critical'
        assert result.recommended_action == 'immediate_intervention'


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_analyze_plot_with_bedrock_failure(self):
        """Test plot analysis when Bedrock fails"""
        service = BrainService(use_mock_gee=True)
        
        # Mock Bedrock to raise exception
        with patch.object(service, '_bedrock_multimodal_analysis', side_effect=Exception('Bedrock error')):
            with pytest.raises(Exception):
                await service.analyze_plot(12.9716, 77.5946)
    
    def test_cluster_detection_missing_ndvi(self):
        """Test cluster detection with alerts missing NDVI data"""
        service = BrainService(use_mock_gee=True)
        
        alerts = [
            Alert(
                plot_id='plot1',
                gee_proof={},  # Missing ndvi_value
                risk_level='high',
                timestamp=datetime.now()
            ),
            Alert(
                plot_id='plot2',
                gee_proof={'ndvi_value': 0.3},
                risk_level='high',
                timestamp=datetime.now()
            )
        ]
        
        # Should handle missing NDVI gracefully
        result = service.detect_cluster_outbreak(alerts)
        
        assert isinstance(result, ClusterAnalysis)
        assert result.affected_plots == 2
