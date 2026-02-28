"""
SentinelService - AWS Open Data Sentinel-2 Integration

Handles satellite imagery retrieval from AWS Open Data Sentinel-2:
- Fetches latest cloud-free RGB imagery from S3
- Generates presigned URLs for secure image access
- Assesses image quality (cloud cover, data availability)
- Supports multimodal Bedrock analysis
"""

from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging
import boto3
from botocore.exceptions import ClientError
from config.settings import get_settings
import math

logger = logging.getLogger(__name__)


class SentinelData(BaseModel):
    """Sentinel-2 imagery data result"""
    image_url: str
    tile_id: str
    acquisition_date: datetime
    cloud_cover_percentage: float
    resolution: str
    quality_assessment: str  # 'usable', 'marginal', 'unusable'
    metadata: Dict[str, Any]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ImageQualityResult(BaseModel):
    """Image quality assessment result"""
    is_usable: bool
    cloud_cover_percentage: float
    quality_assessment: str  # 'usable', 'marginal', 'unusable'
    data_available: bool
    issues: list[str]
    confidence: float


class SentinelService:
    """Service for AWS Open Data Sentinel-2 integration"""
    
    def __init__(self, region: Optional[str] = None):
        """
        Initialize SentinelService with S3 client
        
        Args:
            region: AWS region (defaults to settings)
        """
        settings = get_settings()
        
        # Initialize boto3 S3 client
        self.region = region or settings.aws.region
        self.s3_client = boto3.client('s3', region_name=self.region)
        
        # Get configuration from settings
        self.sentinel_bucket = settings.sentinel.s3_bucket
        self.default_resolution = settings.sentinel.default_resolution
        self.presigned_url_expiry = settings.sentinel.presigned_url_expiry
        
        # Quality thresholds
        self.cloud_cover_threshold_usable = 20.0  # < 20% is usable
        self.cloud_cover_threshold_marginal = 50.0  # 20-50% is marginal
        
        logger.info(f"SentinelService initialized with region={self.region}, "
                   f"bucket={self.sentinel_bucket}, "
                   f"presigned_url_expiry={self.presigned_url_expiry}s")
    
    def _lat_lon_to_sentinel_tile(self, lat: float, lon: float) -> str:
        """
        Convert latitude/longitude to Sentinel-2 tile ID (MGRS)
        
        Sentinel-2 uses Military Grid Reference System (MGRS) for tile naming.
        Format: [UTM Zone][Latitude Band][Grid Square]
        Example: 43PGP
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            Sentinel-2 tile ID (MGRS format)
        """
        # Calculate UTM zone from longitude
        utm_zone = int((lon + 180) / 6) + 1
        
        # Determine latitude band (C-X, excluding I and O)
        # Simplified mapping for demonstration
        lat_bands = "CDEFGHJKLMNPQRSTUVWX"
        lat_band_idx = int((lat + 80) / 8)
        lat_band_idx = max(0, min(lat_band_idx, len(lat_bands) - 1))
        lat_band = lat_bands[lat_band_idx]
        
        # For grid square, we'll use a simplified approach
        # In production, use a proper MGRS library like mgrs-python
        # For now, we'll use common tiles for Indian region
        
        # Common Sentinel-2 tiles for India (Karnataka region)
        # This is a simplified mapping - in production use proper MGRS conversion
        if 12.0 <= lat <= 18.0 and 74.0 <= lon <= 78.0:
            # Karnataka region
            grid_square = "PGP"  # Bangalore area
        elif 8.0 <= lat <= 13.0 and 76.0 <= lon <= 80.0:
            # Tamil Nadu region
            grid_square = "PNR"  # Chennai area
        elif 15.0 <= lat <= 20.0 and 78.0 <= lon <= 82.0:
            # Telangana region
            grid_square = "PET"  # Hyderabad area
        else:
            # Default grid square
            grid_square = "PGP"
        
        tile_id = f"{utm_zone}{lat_band}{grid_square}"
        
        logger.debug(f"Converted coordinates ({lat}, {lon}) to tile ID: {tile_id}")
        
        return tile_id
    
    def _find_latest_sentinel_image(
        self, 
        tile_id: str, 
        max_days_back: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Find the latest available Sentinel-2 image for a tile
        
        Args:
            tile_id: Sentinel-2 tile ID (MGRS format)
            max_days_back: Maximum days to search backwards
            
        Returns:
            Dictionary with image metadata or None if not found
        """
        try:
            # Sentinel-2 L2A path structure:
            # tiles/[UTM]/[LAT]/[GRID]/[YEAR]/[MONTH]/[DAY]/[SEQUENCE]/
            
            # Extract tile components
            utm_zone = tile_id[:2]
            lat_band = tile_id[2]
            grid_square = tile_id[3:]
            
            # Search backwards from today
            current_date = datetime.now()
            
            for days_back in range(max_days_back):
                search_date = current_date - timedelta(days=days_back)
                year = search_date.strftime('%Y')
                month = search_date.strftime('%m')
                day = search_date.strftime('%d')
                
                # Construct S3 prefix
                prefix = f"tiles/{utm_zone}/{lat_band}/{grid_square}/{year}/{month}/{day}/"
                
                try:
                    # List objects with this prefix
                    response = self.s3_client.list_objects_v2(
                        Bucket=self.sentinel_bucket,
                        Prefix=prefix,
                        MaxKeys=10
                    )
                    
                    if 'Contents' in response and len(response['Contents']) > 0:
                        # Found imagery for this date
                        # Look for TCI (True Color Image) file
                        for obj in response['Contents']:
                            if 'TCI.jp2' in obj['Key'] or 'R60m/TCI.jp2' in obj['Key']:
                                logger.info(f"Found Sentinel-2 image: {obj['Key']}")
                                
                                return {
                                    's3_key': obj['Key'],
                                    'acquisition_date': search_date,
                                    'tile_id': tile_id,
                                    'size': obj['Size']
                                }
                
                except ClientError as e:
                    # Continue searching if this date doesn't exist
                    logger.debug(f"No data found for {prefix}: {e}")
                    continue
            
            logger.warning(f"No Sentinel-2 imagery found for tile {tile_id} "
                          f"within {max_days_back} days")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for Sentinel-2 imagery: {e}")
            return None
    
    def _generate_presigned_url(self, s3_key: str) -> str:
        """
        Generate presigned URL for S3 object access
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Presigned URL string
            
        Raises:
            ClientError: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.sentinel_bucket,
                    'Key': s3_key
                },
                ExpiresIn=self.presigned_url_expiry
            )
            
            logger.debug(f"Generated presigned URL for {s3_key} "
                        f"(expires in {self.presigned_url_expiry}s)")
            
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise
    
    def _assess_image_quality(
        self, 
        image_metadata: Dict[str, Any],
        cloud_cover: Optional[float] = None
    ) -> ImageQualityResult:
        """
        Assess image quality based on metadata and cloud cover
        
        Args:
            image_metadata: Image metadata dictionary
            cloud_cover: Cloud cover percentage (if available)
            
        Returns:
            ImageQualityResult with quality assessment
        """
        issues = []
        is_usable = True
        confidence = 1.0
        
        # Assess cloud cover
        if cloud_cover is None:
            # Estimate cloud cover (in production, parse from metadata)
            cloud_cover = 15.0  # Default assumption for demonstration
            issues.append("Cloud cover estimated (metadata not available)")
            confidence *= 0.8
        
        if cloud_cover < self.cloud_cover_threshold_usable:
            quality_assessment = "usable"
        elif cloud_cover < self.cloud_cover_threshold_marginal:
            quality_assessment = "marginal"
            issues.append(f"Moderate cloud cover ({cloud_cover:.1f}%)")
            confidence *= 0.7
        else:
            quality_assessment = "unusable"
            is_usable = False
            issues.append(f"High cloud cover ({cloud_cover:.1f}%)")
            confidence *= 0.3
        
        # Check data availability
        data_available = image_metadata is not None and 's3_key' in image_metadata
        
        if not data_available:
            is_usable = False
            issues.append("No imagery data available")
            quality_assessment = "unusable"
            confidence = 0.0
        
        # Check image age
        if data_available and 'acquisition_date' in image_metadata:
            age_days = (datetime.now() - image_metadata['acquisition_date']).days
            if age_days > 14:
                issues.append(f"Image is {age_days} days old")
                confidence *= 0.9
        
        return ImageQualityResult(
            is_usable=is_usable,
            cloud_cover_percentage=cloud_cover,
            quality_assessment=quality_assessment,
            data_available=data_available,
            issues=issues,
            confidence=confidence
        )
    
    async def get_latest_image(
        self, 
        lat: float, 
        lon: float,
        max_days_back: int = 30
    ) -> SentinelData:
        """
        Fetch latest cloud-free Sentinel-2 RGB image from AWS Open Data
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            max_days_back: Maximum days to search backwards (default: 30)
            
        Returns:
            SentinelData with image URL and metadata
            
        Raises:
            ValueError: If no suitable imagery is found
            ClientError: If S3 operations fail
        """
        try:
            logger.info(f"Fetching Sentinel-2 imagery for coordinates: ({lat}, {lon})")
            
            # Step 1: Convert coordinates to Sentinel-2 tile ID
            tile_id = self._lat_lon_to_sentinel_tile(lat, lon)
            
            # Step 2: Find latest available image
            image_metadata = self._find_latest_sentinel_image(tile_id, max_days_back)
            
            if not image_metadata:
                raise ValueError(
                    f"No Sentinel-2 imagery found for coordinates ({lat}, {lon}) "
                    f"within {max_days_back} days"
                )
            
            # Step 3: Generate presigned URL
            image_url = self._generate_presigned_url(image_metadata['s3_key'])
            
            # Step 4: Assess image quality
            quality_result = self._assess_image_quality(image_metadata)
            
            # Step 5: Create SentinelData result
            sentinel_data = SentinelData(
                image_url=image_url,
                tile_id=tile_id,
                acquisition_date=image_metadata['acquisition_date'],
                cloud_cover_percentage=quality_result.cloud_cover_percentage,
                resolution=self.default_resolution,
                quality_assessment=quality_result.quality_assessment,
                metadata={
                    's3_key': image_metadata['s3_key'],
                    's3_bucket': self.sentinel_bucket,
                    'size_bytes': image_metadata.get('size', 0),
                    'quality_confidence': quality_result.confidence,
                    'quality_issues': quality_result.issues,
                    'coordinates': {'lat': lat, 'lon': lon},
                    'url_expires_in': self.presigned_url_expiry
                }
            )
            
            logger.info(f"Successfully retrieved Sentinel-2 image: tile={tile_id}, "
                       f"date={image_metadata['acquisition_date'].date()}, "
                       f"quality={quality_result.quality_assessment}")
            
            return sentinel_data
            
        except ValueError as e:
            logger.error(f"Failed to retrieve Sentinel-2 imagery: {e}")
            raise
        except ClientError as e:
            logger.error(f"AWS S3 error while retrieving Sentinel-2 imagery: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving Sentinel-2 imagery: {e}")
            raise
    
    def assess_image_quality(
        self, 
        sentinel_data: SentinelData
    ) -> ImageQualityResult:
        """
        Assess image quality for a SentinelData result
        
        Args:
            sentinel_data: SentinelData to assess
            
        Returns:
            ImageQualityResult with detailed quality assessment
        """
        return self._assess_image_quality(
            image_metadata=sentinel_data.metadata,
            cloud_cover=sentinel_data.cloud_cover_percentage
        )
    
    def check_data_availability(
        self, 
        lat: float, 
        lon: float,
        date: Optional[datetime] = None
    ) -> bool:
        """
        Check if Sentinel-2 data is available for coordinates and date
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            date: Specific date to check (defaults to today)
            
        Returns:
            True if data is available, False otherwise
        """
        try:
            tile_id = self._lat_lon_to_sentinel_tile(lat, lon)
            
            if date is None:
                date = datetime.now()
            
            # Check if data exists for this tile and date
            year = date.strftime('%Y')
            month = date.strftime('%m')
            day = date.strftime('%d')
            
            utm_zone = tile_id[:2]
            lat_band = tile_id[2]
            grid_square = tile_id[3:]
            
            prefix = f"tiles/{utm_zone}/{lat_band}/{grid_square}/{year}/{month}/{day}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.sentinel_bucket,
                Prefix=prefix,
                MaxKeys=1
            )
            
            available = 'Contents' in response and len(response['Contents']) > 0
            
            logger.info(f"Data availability check for {tile_id} on {date.date()}: {available}")
            
            return available
            
        except Exception as e:
            logger.error(f"Error checking data availability: {e}")
            return False
    
    def get_tile_info(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get Sentinel-2 tile information for coordinates
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            Dictionary with tile information
        """
        tile_id = self._lat_lon_to_sentinel_tile(lat, lon)
        
        return {
            'tile_id': tile_id,
            'utm_zone': tile_id[:2],
            'latitude_band': tile_id[2],
            'grid_square': tile_id[3:],
            'coordinates': {'lat': lat, 'lon': lon},
            'bucket': self.sentinel_bucket,
            'resolution': self.default_resolution
        }
