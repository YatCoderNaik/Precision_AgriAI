"""
BrainService - Multimodal AI Orchestration

Orchestrates multimodal AI analysis by combining:
- GEEService: Google Earth Engine NDVI data
- SentinelService: AWS Open Data Sentinel-2 imagery
- AWS Bedrock: Multimodal reasoning (NDVI + Image → Analysis)
"""

from typing import Tuple, Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
import logging
import json
import asyncio
import boto3
from botocore.exceptions import ClientError

from services.gee_service import GEEService, GEEData
from services.sentinel_service import SentinelService, SentinelData
from config.settings import get_settings

logger = logging.getLogger(__name__)


class BedrockResponse(BaseModel):
    """AWS Bedrock analysis response"""
    risk_classification: str  # 'low', 'medium', 'high', 'critical'
    confidence_score: float
    explanation: str
    visual_observations: str
    recommendations: List[str]


class AnalysisResult(BaseModel):
    """Complete multimodal analysis result"""
    gee_data: GEEData
    sentinel_data: SentinelData
    bedrock_reasoning: BedrockResponse
    risk_level: str
    confidence: float
    analysis_timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ClusterAnalysis(BaseModel):
    """Cluster outbreak analysis result"""
    outbreak_detected: bool
    affected_plots: int
    avg_ndvi: float
    severity: str
    recommended_action: str


class Alert(BaseModel):
    """Alert data structure for cluster analysis"""
    plot_id: str
    gee_proof: Dict[str, Any]
    risk_level: str
    timestamp: datetime


class BrainService:
    """Service for multimodal AI orchestration with GEE, Sentinel, and Bedrock"""
    
    def __init__(self, use_mock_gee: bool = False, region: Optional[str] = None):
        """
        Initialize BrainService with sub-services
        
        Args:
            use_mock_gee: If True, use mock GEE data
            region: AWS region for Bedrock (defaults to settings)
        """
        settings = get_settings()
        
        # Initialize sub-services
        self.gee_service = GEEService(use_mock=use_mock_gee)
        self.sentinel_service = SentinelService(region=region)
        
        # Initialize Bedrock client
        self.region = region or settings.aws.region
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.region)
        
        # Bedrock model configuration
        self.bedrock_model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        self.bedrock_haiku_model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
        
        # Risk classification thresholds
        self.ndvi_critical_threshold = 0.2  # < 0.2 is critical
        self.ndvi_high_threshold = 0.4      # < 0.4 is high risk
        self.ndvi_medium_threshold = 0.6    # < 0.6 is medium risk
        
        logger.info(f"BrainService initialized with region={self.region}, "
                   f"model={self.bedrock_model_id}")
    
    async def analyze_plot(self, lat: float, lon: float) -> AnalysisResult:
        """
        Multimodal analysis combining GEE data and Sentinel imagery
        
        Performs concurrent data fetching from GEE and Sentinel services,
        then sends both numerical NDVI data and visual imagery to Bedrock
        for comprehensive multimodal reasoning.
        
        FALLBACK: If Sentinel imagery is unavailable, falls back to NDVI-only analysis.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            AnalysisResult with complete or fallback analysis
            
        Raises:
            ValueError: If coordinates are invalid or GEE data unavailable
            ClientError: If critical AWS services fail
        """
        try:
            logger.info(f"Starting multimodal analysis for plot at ({lat}, {lon})")
            
            # Step 1 & 2: Concurrent data fetching (GEE + Sentinel)
            # This meets the 6-second concurrent processing requirement
            gee_task = self.gee_service.get_ndvi_analysis(lat, lon)
            sentinel_task = self.sentinel_service.get_latest_image(lat, lon)
            
            # Wait for both to complete concurrently, but handle failures
            gee_data = None
            sentinel_data = None
            sentinel_error = None
            
            try:
                results = await asyncio.gather(gee_task, sentinel_task, return_exceptions=True)
                
                # Check GEE result (critical - must succeed)
                if isinstance(results[0], Exception):
                    raise ValueError(f"GEE data unavailable: {results[0]}")
                gee_data = results[0]
                
                # Check Sentinel result (optional - can fallback)
                if isinstance(results[1], Exception):
                    sentinel_error = results[1]
                    logger.warning(f"Sentinel imagery unavailable: {sentinel_error}")
                    logger.info("Falling back to NDVI-only analysis")
                else:
                    sentinel_data = results[1]
                    
            except Exception as e:
                logger.error(f"Data fetching error: {e}")
                raise
            
            # Log what we got
            if sentinel_data:
                logger.info(f"Data fetched - NDVI: {gee_data.ndvi_float:.3f}, "
                           f"Sentinel tile: {sentinel_data.tile_id}")
            else:
                logger.info(f"Data fetched - NDVI: {gee_data.ndvi_float:.3f} (Sentinel unavailable)")
            
            # Step 3: Send to Bedrock for reasoning (multimodal or NDVI-only)
            if sentinel_data:
                # Full multimodal analysis
                bedrock_response = await self._bedrock_multimodal_analysis(
                    ndvi_value=gee_data.ndvi_float,
                    image_url=sentinel_data.image_url,
                    coordinates=(lat, lon),
                    additional_context={
                        'gee_metadata': gee_data.metadata,
                        'sentinel_metadata': {
                            'tile_id': sentinel_data.tile_id,
                            'cloud_cover': sentinel_data.cloud_cover_percentage,
                            'quality': sentinel_data.quality_assessment
                        }
                    }
                )
            else:
                # Fallback to NDVI-only analysis
                logger.info("Using fallback NDVI-only analysis")
                bedrock_response = self._fallback_risk_classification(gee_data.ndvi_float)
                
                # Add fallback note to explanation
                bedrock_response.explanation += (
                    f"\n\nNote: Satellite imagery unavailable for this location. "
                    f"Analysis based on NDVI data only. Reason: {str(sentinel_error)[:100]}"
                )
            
            # Create mock Sentinel data if unavailable
            if not sentinel_data:
                from services.sentinel_service import SentinelData
                sentinel_data = SentinelData(
                    image_url="",
                    tile_id="unavailable",
                    acquisition_date=datetime.now(),
                    cloud_cover_percentage=0.0,
                    resolution="N/A",
                    quality_assessment="unavailable",
                    metadata={
                        'error': str(sentinel_error),
                        'fallback_mode': True
                    }
                )
            
            # Create complete analysis result
            analysis_result = AnalysisResult(
                gee_data=gee_data,
                sentinel_data=sentinel_data,
                bedrock_reasoning=bedrock_response,
                risk_level=bedrock_response.risk_classification,
                confidence=bedrock_response.confidence_score,
                analysis_timestamp=datetime.now()
            )
            
            logger.info(f"Analysis complete - Risk: {bedrock_response.risk_classification}, "
                       f"Confidence: {bedrock_response.confidence_score:.2f}")
            
            return analysis_result
            
        except ValueError as e:
            logger.error(f"Invalid input for plot analysis: {e}")
            raise
        except ClientError as e:
            logger.error(f"AWS service error during analysis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during plot analysis: {e}")
            raise
    
    async def _bedrock_multimodal_analysis(
        self, 
        ndvi_value: float, 
        image_url: str, 
        coordinates: Tuple[float, float],
        additional_context: Dict[str, Any]
    ) -> BedrockResponse:
        """
        Send both numerical data and imagery to Bedrock for analysis
        
        Uses Claude 3 Sonnet with multimodal inputs (text + image) to perform
        contextual agricultural analysis combining NDVI mathematics with
        visual satellite imagery verification.
        
        Args:
            ndvi_value: NDVI float value from GEE
            image_url: Sentinel-2 image URL
            coordinates: Plot coordinates (lat, lon)
            additional_context: Additional GEE and Sentinel metadata
            
        Returns:
            BedrockResponse with multimodal analysis
            
        Raises:
            ClientError: If Bedrock API call fails
        """
        try:
            lat, lon = coordinates
            
            # Construct Chain-of-Thought prompt for agricultural analysis
            prompt = f"""You are an expert AI agronomist analyzing agricultural plot health using multimodal data.

NUMERICAL DATA (Google Earth Engine):
- NDVI Value: {ndvi_value:.3f} (Range: -1 to 1, where higher = healthier vegetation)
- Coordinates: ({lat:.4f}, {lon:.4f})
- Data Source: {additional_context.get('gee_metadata', {}).get('sensor', 'MODIS')}
- Cloud Cover: {additional_context.get('gee_metadata', {}).get('cloud_cover', 'N/A')}%

VISUAL DATA (Sentinel-2 Satellite Imagery):
- Image URL provided below shows true-color RGB satellite view
- Tile ID: {additional_context.get('sentinel_metadata', {}).get('tile_id', 'N/A')}
- Image Quality: {additional_context.get('sentinel_metadata', {}).get('quality', 'N/A')}

ANALYSIS TASK:
Using Chain-of-Thought reasoning, analyze this agricultural plot:

1. NDVI INTERPRETATION: What does the NDVI value {ndvi_value:.3f} indicate about vegetation health?
   - Consider: Is this healthy (>0.6), moderate (0.4-0.6), stressed (0.2-0.4), or critical (<0.2)?

2. VISUAL VERIFICATION: Examine the satellite image for:
   - Vegetation color and density (green = healthy, brown = stressed)
   - Visible anomalies (flooding, bare patches, browning)
   - Cloud cover or data quality issues
   - Consistency with NDVI mathematical analysis

3. CONTEXTUAL AWARENESS: Consider agricultural context:
   - Could low NDVI be normal (harvest season, fallow period)?
   - Are visual patterns consistent with crop stress or natural cycles?
   - Any signs of drought, disease, or pest damage?

4. RISK CLASSIFICATION: Classify risk level as:
   - "critical": Immediate intervention needed (NDVI < 0.2 or severe visual stress)
   - "high": Urgent attention required (NDVI 0.2-0.4 or moderate visual stress)
   - "medium": Monitor closely (NDVI 0.4-0.6 or minor visual concerns)
   - "low": Healthy, routine monitoring (NDVI > 0.6 and visually healthy)

5. SUSTAINABILITY RECOMMENDATIONS: Provide actionable, sustainable farming advice.

Respond in JSON format:
{{
    "risk_classification": "low|medium|high|critical",
    "confidence_score": 0.0-1.0,
    "explanation": "Your chain-of-thought reasoning combining NDVI and visual analysis",
    "visual_observations": "What you observe in the satellite image",
    "recommendations": ["Action 1", "Action 2", "Action 3"]
}}"""

            # Prepare Bedrock API request with multimodal content
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.3,  # Lower temperature for more consistent analysis
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "url",
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ]
            }
            
            logger.debug(f"Sending multimodal request to Bedrock: NDVI={ndvi_value:.3f}")
            
            # Call Bedrock API
            response = self.bedrock_client.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Parse JSON response from Claude
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                # Fallback if response is not valid JSON
                logger.warning("Bedrock response not valid JSON, using fallback parsing")
                analysis = self._fallback_risk_classification(ndvi_value)
            
            # Create BedrockResponse
            bedrock_response = BedrockResponse(
                risk_classification=analysis.get('risk_classification', 'medium'),
                confidence_score=float(analysis.get('confidence_score', 0.7)),
                explanation=analysis.get('explanation', 'Analysis completed'),
                visual_observations=analysis.get('visual_observations', 'Visual analysis performed'),
                recommendations=analysis.get('recommendations', ['Monitor plot regularly'])
            )
            
            logger.info(f"Bedrock analysis complete: {bedrock_response.risk_classification}")
            
            return bedrock_response
            
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            # Fallback to rule-based classification
            logger.info("Using fallback risk classification")
            return self._fallback_risk_classification(ndvi_value)
        except Exception as e:
            logger.error(f"Unexpected error in Bedrock analysis: {e}")
            return self._fallback_risk_classification(ndvi_value)
    
    def _fallback_risk_classification(self, ndvi_value: float) -> BedrockResponse:
        """
        Fallback risk classification when Bedrock is unavailable
        
        Uses deterministic NDVI thresholds for risk assessment.
        
        Args:
            ndvi_value: NDVI value
            
        Returns:
            BedrockResponse with rule-based classification
        """
        if ndvi_value < self.ndvi_critical_threshold:
            risk = "critical"
            explanation = f"NDVI {ndvi_value:.3f} indicates severe vegetation stress or bare soil"
            recommendations = [
                "Immediate field inspection required",
                "Check irrigation system",
                "Assess for pest or disease damage"
            ]
            confidence = 0.8
        elif ndvi_value < self.ndvi_high_threshold:
            risk = "high"
            explanation = f"NDVI {ndvi_value:.3f} indicates moderate vegetation stress"
            recommendations = [
                "Increase monitoring frequency",
                "Consider supplemental irrigation",
                "Check soil moisture levels"
            ]
            confidence = 0.75
        elif ndvi_value < self.ndvi_medium_threshold:
            risk = "medium"
            explanation = f"NDVI {ndvi_value:.3f} indicates fair vegetation health"
            recommendations = [
                "Continue routine monitoring",
                "Maintain current irrigation schedule",
                "Monitor for early stress signs"
            ]
            confidence = 0.7
        else:
            risk = "low"
            explanation = f"NDVI {ndvi_value:.3f} indicates healthy vegetation"
            recommendations = [
                "Maintain current practices",
                "Routine monitoring sufficient",
                "Continue sustainable farming methods"
            ]
            confidence = 0.85
        
        return BedrockResponse(
            risk_classification=risk,
            confidence_score=confidence,
            explanation=explanation,
            visual_observations="Visual analysis unavailable (fallback mode)",
            recommendations=recommendations
        )
    
    async def classify_urgency(self, analysis_result: AnalysisResult) -> str:
        """
        Classify urgency based on combined analysis
        
        Uses Bedrock's multimodal reasoning for final classification.
        
        Args:
            analysis_result: Complete analysis result
            
        Returns:
            Urgency classification string ('low', 'medium', 'high', 'critical')
        """
        return analysis_result.bedrock_reasoning.risk_classification
    
    async def generate_farmer_guidance(
        self, 
        analysis: AnalysisResult, 
        language: str = "English"
    ) -> str:
        """
        Generate farmer-friendly guidance based on multimodal analysis
        
        Converts technical analysis into simple, actionable advice in the
        farmer's preferred language using AWS Bedrock.
        
        Args:
            analysis: Complete analysis result
            language: Target language for guidance (default: English)
            
        Returns:
            Farmer-friendly guidance text
            
        Raises:
            ClientError: If Bedrock API call fails
        """
        try:
            # Construct prompt for farmer-friendly guidance
            guidance_prompt = f"""Convert this technical agricultural analysis into simple, farmer-friendly guidance in {language}.

TECHNICAL ANALYSIS:
- Risk Level: {analysis.risk_level}
- NDVI Value: {analysis.gee_data.ndvi_float:.3f}
- Confidence: {analysis.confidence:.0%}
- Technical Explanation: {analysis.bedrock_reasoning.explanation}
- Visual Observations: {analysis.bedrock_reasoning.visual_observations}
- Recommendations: {', '.join(analysis.bedrock_reasoning.recommendations)}

TASK:
Create simple, actionable advice for a farmer in {language}. Use:
- Simple, non-technical language
- Clear action steps
- Empathetic, supportive tone
- Practical, affordable solutions
- Urgency indicators (if needed)

Keep it concise (3-4 sentences) and focus on what the farmer should DO.

Respond in plain text (not JSON)."""

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "temperature": 0.5,
                "messages": [
                    {
                        "role": "user",
                        "content": guidance_prompt
                    }
                ]
            }
            
            logger.debug(f"Generating farmer guidance in {language}")
            
            # Use Haiku for faster, cost-effective guidance generation
            response = self.bedrock_client.invoke_model(
                modelId=self.bedrock_haiku_model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            guidance = response_body['content'][0]['text']
            
            logger.info(f"Generated farmer guidance ({len(guidance)} chars)")
            
            return guidance.strip()
            
        except ClientError as e:
            logger.error(f"Bedrock API error generating guidance: {e}")
            # Fallback to simple template
            return self._fallback_farmer_guidance(analysis, language)
        except Exception as e:
            logger.error(f"Unexpected error generating guidance: {e}")
            return self._fallback_farmer_guidance(analysis, language)
    
    def _fallback_farmer_guidance(
        self, 
        analysis: AnalysisResult, 
        language: str
    ) -> str:
        """
        Fallback farmer guidance when Bedrock is unavailable
        
        Args:
            analysis: Analysis result
            language: Target language
            
        Returns:
            Simple guidance text
        """
        risk = analysis.risk_level
        ndvi = analysis.gee_data.ndvi_float
        
        if risk == "critical":
            guidance = f"URGENT: Your crop needs immediate attention. NDVI reading is {ndvi:.2f}, which is very low. Please inspect your field today and check water supply."
        elif risk == "high":
            guidance = f"IMPORTANT: Your crop shows signs of stress. NDVI reading is {ndvi:.2f}. Check irrigation and look for pest damage within 2-3 days."
        elif risk == "medium":
            guidance = f"Your crop health is fair. NDVI reading is {ndvi:.2f}. Continue monitoring and maintain regular watering schedule."
        else:
            guidance = f"Good news! Your crop is healthy. NDVI reading is {ndvi:.2f}. Keep up your current farming practices."
        
        # Note: In production, this would use translation service for other languages
        if language != "English":
            guidance += f" (Translation to {language} unavailable in fallback mode)"
        
        return guidance
    
    def detect_cluster_outbreak(
        self, 
        hobli_alerts: List[Alert]
    ) -> ClusterAnalysis:
        """
        Analyze multiple alerts for coordinated outbreak patterns
        
        Aggregates NDVI values and risk patterns across multiple plots
        within a jurisdiction to detect regional stress patterns.
        
        Args:
            hobli_alerts: List of alerts within a jurisdiction (Hobli)
            
        Returns:
            ClusterAnalysis with outbreak detection results
        """
        if not hobli_alerts:
            return ClusterAnalysis(
                outbreak_detected=False,
                affected_plots=0,
                avg_ndvi=0.0,
                severity="none",
                recommended_action="no_action"
            )
        
        # Extract NDVI values from alerts
        ndvi_values = []
        high_risk_count = 0
        
        for alert in hobli_alerts:
            gee_proof = alert.gee_proof
            if 'ndvi_value' in gee_proof:
                ndvi_values.append(gee_proof['ndvi_value'])
            
            if alert.risk_level in ['high', 'critical']:
                high_risk_count += 1
        
        # Calculate average NDVI
        avg_ndvi = sum(ndvi_values) / len(ndvi_values) if ndvi_values else 0.0
        
        # Determine if this represents a coordinated outbreak
        # Criteria: 3+ plots AND (avg NDVI < 0.3 OR 50%+ high risk)
        outbreak_detected = (
            len(hobli_alerts) >= 3 and 
            (avg_ndvi < 0.3 or high_risk_count >= len(hobli_alerts) * 0.5)
        )
        
        # Determine severity
        if outbreak_detected:
            if avg_ndvi < 0.2 or high_risk_count >= len(hobli_alerts) * 0.7:
                severity = "critical"
                recommended_action = "immediate_intervention"
            elif avg_ndvi < 0.3 or high_risk_count >= len(hobli_alerts) * 0.5:
                severity = "high"
                recommended_action = "coordinate_intervention"
            else:
                severity = "medium"
                recommended_action = "enhanced_monitoring"
        else:
            severity = "low"
            recommended_action = "routine_monitoring"
        
        logger.info(f"Cluster analysis: {len(hobli_alerts)} plots, "
                   f"avg_ndvi={avg_ndvi:.3f}, outbreak={outbreak_detected}")
        
        return ClusterAnalysis(
            outbreak_detected=outbreak_detected,
            affected_plots=len(hobli_alerts),
            avg_ndvi=round(avg_ndvi, 3),
            severity=severity,
            recommended_action=recommended_action
        )
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get service information and status
        
        Returns:
            Dictionary with service information
        """
        return {
            'service': 'BrainService',
            'gee_available': self.gee_service.check_gee_availability(),
            'bedrock_model': self.bedrock_model_id,
            'bedrock_haiku_model': self.bedrock_haiku_model_id,
            'region': self.region,
            'risk_thresholds': {
                'critical': f'< {self.ndvi_critical_threshold}',
                'high': f'< {self.ndvi_high_threshold}',
                'medium': f'< {self.ndvi_medium_threshold}',
                'low': f'>= {self.ndvi_medium_threshold}'
            }
        }
