from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

_ee = None
_ee_initialized = False

class GEEData(BaseModel):
    ndvi_float: float
    acquisition_date: datetime
    cloud_cover: float
    metadata: Dict[str, Any]
    quality_score: float
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

class QualityAssessment(BaseModel):
    is_reliable: bool
    quality_score: float
    issues: list[str]
    confidence: float

class GEEService:
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self._ee_available = False
        self.ndvi_min_threshold = -1.0
        self.ndvi_max_threshold = 1.0
        self.cloud_cover_threshold = 30.0

    def _init_earth_engine(self) -> bool:
        global _ee, _ee_initialized
        if _ee_initialized:
            return self._ee_available
        try:
            import ee
            _ee = ee
            try:
                _ee.Initialize()
                self._ee_available = True
                _ee_initialized = True
                return True
            except Exception:
                self._ee_available = False
                _ee_initialized = True
                return False
        except ImportError:
            self._ee_available = False
            _ee_initialized = True
            return False
    
    def _get_mock_ndvi_data(self, lat: float, lon: float) -> GEEData:
        import hashlib
        coord_hash = hashlib.md5(f"{lat:.4f}{lon:.4f}".encode()).hexdigest()
        hash_value = int(coord_hash[:8], 16)
        ndvi = 0.4 + (hash_value % 1000) / 2500.0
        return GEEData(
            ndvi_float=round(ndvi, 3),
            acquisition_date=datetime.now(),
            cloud_cover=10.0,
            metadata={'sensor': 'MODIS/061/MOD13Q1', 'resolution': '250m', 'data_source': 'mock'},
            quality_score=0.85
        )

    async def get_ndvi_analysis(self, lat: float, lon: float, year: Optional[int] = None) -> GEEData:
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Invalid coordinates: ({lat}, {lon})")
        if self.use_mock or not self._init_earth_engine():
            return self._get_mock_ndvi_data(lat, lon)
        if year is None:
            year = datetime.now().year
        point = _ee.Geometry.Point([lon, lat])
        modis = _ee.ImageCollection("MODIS/061/MOD13Q1")
        image = modis.filterBounds(point).filterDate(f"{year}-01-01", f"{year}-12-31").median()
        stats = image.reduceRegion(reducer=_ee.Reducer.mean(), geometry=point, scale=250, bestEffort=True).getInfo()
        ndvi_raw = stats.get('NDVI', 0)
        ndvi = ndvi_raw * 0.0001 if ndvi_raw else 0.0
        cloud_cover = stats.get('SummaryQA', 0)
        quality_result = self._assess_data_quality(ndvi, cloud_cover)
        return GEEData(
            ndvi_float=round(ndvi, 3),
            acquisition_date=datetime(year, 6, 15),
            cloud_cover=float(cloud_cover),
            metadata={'sensor': 'MODIS/061/MOD13Q1', 'resolution': '250m'},
            quality_score=quality_result.quality_score
        )

    def _assess_data_quality(self, ndvi: float, cloud_cover: float) -> QualityAssessment:
        issues = []
        is_reliable = True
        confidence = 1.0
        if not (self.ndvi_min_threshold <= ndvi <= self.ndvi_max_threshold):
            issues.append(f"NDVI outside valid range")
            is_reliable = False
            confidence *= 0.3
        if ndvi < 0:
            issues.append(f"Negative NDVI")
            confidence *= 0.8
        elif ndvi < 0.2:
            issues.append(f"Low NDVI")
            confidence *= 0.9
        if cloud_cover > self.cloud_cover_threshold:
            issues.append(f"High cloud cover")
            confidence *= 0.7
            if cloud_cover > 60:
                is_reliable = False
        return QualityAssessment(is_reliable=is_reliable, quality_score=confidence, issues=issues, confidence=confidence)
    
    def assess_vegetation_health(self, ndvi: float) -> Dict[str, Any]:
        if ndvi < 0:
            return {'category': 'water_or_bare_soil', 'health': 'not_applicable', 'ndvi': ndvi}
        elif ndvi < 0.2:
            return {'category': 'sparse_vegetation', 'health': 'poor', 'ndvi': ndvi}
        elif ndvi < 0.4:
            return {'category': 'moderate_vegetation', 'health': 'fair', 'ndvi': ndvi}
        elif ndvi < 0.6:
            return {'category': 'healthy_vegetation', 'health': 'good', 'ndvi': ndvi}
        elif ndvi < 0.8:
            return {'category': 'very_healthy_vegetation', 'health': 'excellent', 'ndvi': ndvi}
        else:
            return {'category': 'dense_vegetation', 'health': 'excellent', 'ndvi': ndvi}
    
    def check_gee_availability(self) -> bool:
        if not _ee_initialized:
            self._init_earth_engine()
        return self._ee_available
    
    def get_service_info(self) -> Dict[str, Any]:
        return {
            'service': 'GEEService',
            'gee_available': self._ee_available,
            'use_mock': self.use_mock,
            'data_source': 'MODIS/061/MOD13Q1',
            'resolution': '250m',
            'ndvi_range': [self.ndvi_min_threshold, self.ndvi_max_threshold],
            'cloud_cover_threshold': self.cloud_cover_threshold
        }

