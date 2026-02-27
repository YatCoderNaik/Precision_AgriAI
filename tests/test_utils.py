"""
Test Utilities for Precision AgriAI

Provides helper functions and utilities for testing.
"""

from typing import Dict, Any, List, Tuple
import json
from datetime import datetime, timedelta
import random


class MockAWSResponses:
    """Mock responses for AWS services"""
    
    @staticmethod
    def bedrock_multimodal_response(risk_level: str = "medium") -> Dict[str, Any]:
        """Generate a mock Bedrock multimodal analysis response"""
        risk_descriptions = {
            "low": "Vegetation appears healthy with no immediate concerns.",
            "medium": "Some stress indicators detected, monitoring recommended.",
            "high": "Significant stress detected, intervention may be needed.",
            "critical": "Severe stress detected, immediate action required.",
        }
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "risk_classification": risk_level,
                        "confidence_score": random.uniform(0.7, 0.95),
                        "explanation": risk_descriptions.get(risk_level, "Analysis complete."),
                        "visual_observations": "Satellite imagery shows vegetation patterns consistent with analysis.",
                        "recommendations": [
                            "Monitor soil moisture levels",
                            "Check for pest activity",
                            "Consider irrigation if conditions persist",
                        ],
                    }),
                }
            ],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 150, "output_tokens": 200},
        }
    
    @staticmethod
    def polly_synthesize_speech_response() -> Dict[str, Any]:
        """Generate a mock Polly synthesize speech response"""
        return {
            "AudioStream": b"mock_audio_data",
            "ContentType": "audio/mpeg",
            "RequestCharacters": 100,
        }
    
    @staticmethod
    def transcribe_job_response(text: str = "Check my crop health") -> Dict[str, Any]:
        """Generate a mock Transcribe job response"""
        return {
            "TranscriptionJob": {
                "TranscriptionJobName": "test-job",
                "TranscriptionJobStatus": "COMPLETED",
                "LanguageCode": "hi-IN",
                "MediaFormat": "mp3",
                "Transcript": {
                    "TranscriptFileUri": "https://s3.amazonaws.com/test-transcript.json"
                },
            }
        }
    
    @staticmethod
    def sns_publish_response() -> Dict[str, Any]:
        """Generate a mock SNS publish response"""
        return {
            "MessageId": f"test-message-{random.randint(1000, 9999)}",
            "ResponseMetadata": {
                "RequestId": f"test-request-{random.randint(1000, 9999)}",
                "HTTPStatusCode": 200,
            },
        }


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_plot_registration(
        user_id: str = "user_001",
        plot_id: str = "plot_001",
        lat: float = 12.9716,
        lon: float = 77.5946,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a plot registration data structure"""
        data = {
            "user_id": user_id,
            "plot_id": plot_id,
            "lat": lat,
            "lon": lon,
            "crop": "rice",
            "hobli_id": "hobli_bangalore_001",
            "farmer_name": "Test Farmer",
            "phone_number": "+919876543210",
            "registration_date": datetime.now().isoformat(),
            "last_analysis": None,
            "status": "active",
        }
        data.update(kwargs)
        return data
    
    @staticmethod
    def create_alert(
        hobli_id: str = "hobli_bangalore_001",
        plot_id: str = "plot_001",
        risk_level: str = "high",
        **kwargs
    ) -> Dict[str, Any]:
        """Create an alert data structure"""
        data = {
            "hobli_id": hobli_id,
            "timestamp": datetime.now().isoformat(),
            "plot_id": plot_id,
            "user_id": "user_001",
            "risk_level": risk_level,
            "message": "Crop stress detected",
            "gee_proof": {
                "ndvi_value": 0.35,
                "moisture_index": 0.25,
                "temperature_anomaly": 2.5,
            },
            "bedrock_reasoning": "Low NDVI indicates vegetation stress",
            "officer_response": None,
            "resolution_status": "pending",
            "sms_sent": False,
        }
        data.update(kwargs)
        return data
    
    @staticmethod
    def create_gee_analysis(ndvi: float = 0.65, **kwargs) -> Dict[str, Any]:
        """Create a GEE analysis result"""
        data = {
            "ndvi_float": ndvi,
            "acquisition_date": (datetime.now() - timedelta(days=3)).isoformat(),
            "cloud_cover": 15.5,
            "metadata": {
                "sensor": "Landsat-8",
                "resolution": "30m",
                "bands_used": ["SR_B5", "SR_B4"],
            },
        }
        data.update(kwargs)
        return data
    
    @staticmethod
    def create_sentinel_data(**kwargs) -> Dict[str, Any]:
        """Create Sentinel-2 imagery data"""
        data = {
            "image_url": "https://sentinel-s2-l2a.s3.amazonaws.com/tiles/43P/GQ/2024/01/15/0/R60m/TCI.jp2",
            "tile_id": "43PGQ",
            "acquisition_date": (datetime.now() - timedelta(days=2)).isoformat(),
            "cloud_cover_percentage": 12.3,
            "resolution": "60m",
        }
        data.update(kwargs)
        return data


class CoordinateTestHelper:
    """Helper functions for coordinate testing"""
    
    @staticmethod
    def is_valid_coordinate(lat: float, lon: float) -> bool:
        """Check if coordinates are valid"""
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    @staticmethod
    def is_in_india(lat: float, lon: float) -> bool:
        """Check if coordinates are within India's approximate bounds"""
        return 8.0 <= lat <= 37.0 and 68.0 <= lon <= 97.0
    
    @staticmethod
    def has_sufficient_precision(lat: float, lon: float, min_decimals: int = 4) -> bool:
        """Check if coordinates have sufficient decimal precision"""
        lat_str = str(lat).split(".")
        lon_str = str(lon).split(".")
        
        lat_decimals = len(lat_str[1]) if len(lat_str) > 1 else 0
        lon_decimals = len(lon_str[1]) if len(lon_str) > 1 else 0
        
        return lat_decimals >= min_decimals and lon_decimals >= min_decimals
    
    @staticmethod
    def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate approximate distance between two coordinates in kilometers"""
        from math import radians, sin, cos, sqrt, atan2
        
        lat1, lon1 = radians(coord1[0]), radians(coord1[1])
        lat2, lon2 = radians(coord2[0]), radians(coord2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        # Earth's radius in kilometers
        radius = 6371.0
        
        return radius * c


class NDVITestHelper:
    """Helper functions for NDVI testing"""
    
    @staticmethod
    def classify_ndvi(ndvi: float) -> str:
        """Classify NDVI value into health categories"""
        if ndvi >= 0.6:
            return "healthy"
        elif ndvi >= 0.4:
            return "moderate"
        elif ndvi >= 0.2:
            return "stressed"
        else:
            return "critical"
    
    @staticmethod
    def is_valid_ndvi(ndvi: float) -> bool:
        """Check if NDVI value is valid"""
        return -1.0 <= ndvi <= 1.0
    
    @staticmethod
    def generate_ndvi_time_series(
        start_ndvi: float = 0.7,
        trend: str = "declining",
        steps: int = 10
    ) -> List[float]:
        """Generate a time series of NDVI values"""
        series = [start_ndvi]
        
        for _ in range(steps - 1):
            if trend == "declining":
                change = random.uniform(-0.05, -0.01)
            elif trend == "improving":
                change = random.uniform(0.01, 0.05)
            else:  # stable
                change = random.uniform(-0.02, 0.02)
            
            next_value = max(-1.0, min(1.0, series[-1] + change))
            series.append(round(next_value, 3))
        
        return series


class HobliTestHelper:
    """Helper functions for Hobli mapping testing"""
    
    @staticmethod
    def is_valid_hobli_id(hobli_id: str) -> bool:
        """Check if Hobli ID follows the expected format"""
        parts = hobli_id.split("_")
        return (
            len(parts) == 3
            and parts[0] == "hobli"
            and parts[1].isalpha()
            and parts[2].isdigit()
        )
    
    @staticmethod
    def extract_district(hobli_id: str) -> str:
        """Extract district name from Hobli ID"""
        parts = hobli_id.split("_")
        return parts[1] if len(parts) >= 2 else ""
    
    @staticmethod
    def group_plots_by_hobli(plots: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Group plots by their Hobli ID"""
        grouped = {}
        for plot in plots:
            hobli_id = plot.get("hobli_id")
            plot_id = plot.get("plot_id")
            
            if hobli_id and plot_id:
                if hobli_id not in grouped:
                    grouped[hobli_id] = []
                grouped[hobli_id].append(plot_id)
        
        return grouped


class PerformanceTestHelper:
    """Helper functions for performance testing"""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure execution time of a function"""
        import time
        
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    async def measure_async_execution_time(func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure execution time of an async function"""
        import time
        
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    def assert_within_time_limit(execution_time: float, limit: float, message: str = ""):
        """Assert that execution time is within the specified limit"""
        assert execution_time <= limit, (
            f"{message} Execution time {execution_time:.2f}s exceeded limit {limit:.2f}s"
        )
