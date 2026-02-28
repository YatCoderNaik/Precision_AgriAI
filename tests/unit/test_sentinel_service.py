"""
Unit Tests for SentinelService

Tests AWS Open Data Sentinel-2 integration including:
- Tile ID conversion from coordinates
- Image retrieval and presigned URL generation
- Image quality assessment
- Data availability checking
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from services.sentinel_service import (
    SentinelService,
    SentinelData,
    ImageQualityResult
)


@pytest.fixture
def sentinel_service():
    """Create SentinelService instance for testing"""
    with patch('services.sentinel_service.boto3.client'):
        service = SentinelService(region='ap-south-1')
        return service


@pytest.fixture
def mock_s3_client():
    """Create mock S3 client"""
    return Mock()


class TestSentinelServiceInitialization:
    """Test SentinelService initialization"""
    
    def test_initialization_with_default_region(self):
        """Test service initializes with default region from settings"""
        with patch('services.sentinel_service.boto3.client') as mock_boto3:
            service = SentinelService()
            
            assert service.region == 'ap-south-1'
            assert service.sentinel_bucket == 'sentinel-s2-l2a'
            assert service.default_resolution == '60m'
            assert service.presigned_url_expiry == 3600
            mock_boto3.assert_called_once()
    
    def test_initialization_with_custom_region(self):
        """Test service initializes with custom region"""
        with patch('services.sentinel_service.boto3.client'):
            service = SentinelService(region='us-west-2')
            
            assert service.region == 'us-west-2'


class TestCoordinateToTileConversion:
    """Test coordinate to Sentinel-2 tile ID conversion"""
    
    def test_bangalore_coordinates_to_tile(self, sentinel_service):
        """Test Bangalore coordinates convert to correct tile"""
        # Bangalore: ~12.97°N, 77.59°E
        tile_id = sentinel_service._lat_lon_to_sentinel_tile(12.97, 77.59)
        
        assert isinstance(tile_id, str)
        assert len(tile_id) >= 5  # Format: [UTM][LAT][GRID]
        assert tile_id[:2].isdigit()  # UTM zone is numeric
        assert tile_id == "43PPGP"  # Expected tile for Bangalore
    
    def test_chennai_coordinates_to_tile(self, sentinel_service):
        """Test Chennai coordinates convert to correct tile"""
        # Chennai: ~13.08°N, 80.27°E
        tile_id = sentinel_service._lat_lon_to_sentinel_tile(13.08, 80.27)
        
        assert isinstance(tile_id, str)
        assert tile_id == "44PPGP"  # Expected tile for Chennai region
    
    def test_hyderabad_coordinates_to_tile(self, sentinel_service):
        """Test Hyderabad coordinates convert to correct tile"""
        # Hyderabad: ~17.38°N, 78.48°E
        tile_id = sentinel_service._lat_lon_to_sentinel_tile(17.38, 78.48)
        
        assert isinstance(tile_id, str)
        assert tile_id == "44QPET"  # Expected tile for Hyderabad
    
    def test_utm_zone_calculation(self, sentinel_service):
        """Test UTM zone is calculated correctly"""
        # Test various longitudes
        tile_id_1 = sentinel_service._lat_lon_to_sentinel_tile(12.0, 75.0)
        tile_id_2 = sentinel_service._lat_lon_to_sentinel_tile(12.0, 81.0)
        
        # Different longitudes should have different UTM zones
        assert tile_id_1[:2] != tile_id_2[:2]


class TestImageRetrieval:
    """Test Sentinel-2 image retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_latest_image_success(self, sentinel_service, mock_s3_client):
        """Test successful image retrieval"""
        sentinel_service.s3_client = mock_s3_client
        
        # Mock S3 list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'tiles/43/P/GP/2024/01/15/0/R60m/TCI.jp2',
                    'Size': 1024000
                }
            ]
        }
        
        # Mock presigned URL generation
        mock_s3_client.generate_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        # Get latest image
        result = await sentinel_service.get_latest_image(12.97, 77.59)
        
        assert isinstance(result, SentinelData)
        assert result.image_url == 'https://s3.amazonaws.com/presigned-url'
        assert result.tile_id == '43PPGP'
        assert result.resolution == '60m'
        assert result.quality_assessment in ['usable', 'marginal', 'unusable']
        assert 's3_key' in result.metadata
        assert 'coordinates' in result.metadata
    
    @pytest.mark.asyncio
    async def test_get_latest_image_no_data_found(self, sentinel_service, mock_s3_client):
        """Test image retrieval when no data is available"""
        sentinel_service.s3_client = mock_s3_client
        
        # Mock S3 to return no results
        mock_s3_client.list_objects_v2.return_value = {}
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="No Sentinel-2 imagery found"):
            await sentinel_service.get_latest_image(12.97, 77.59, max_days_back=5)
    
    @pytest.mark.asyncio
    async def test_get_latest_image_with_recent_data(self, sentinel_service, mock_s3_client):
        """Test image retrieval finds recent data"""
        sentinel_service.s3_client = mock_s3_client
        
        # Mock S3 to return data on first try (today)
        today = datetime.now()
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': f'tiles/43/P/GP/{today.year}/{today.month:02d}/{today.day:02d}/0/R60m/TCI.jp2',
                    'Size': 2048000
                }
            ]
        }
        
        mock_s3_client.generate_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        result = await sentinel_service.get_latest_image(12.97, 77.59)
        
        assert result.acquisition_date.date() == today.date()
        assert result.metadata['size_bytes'] == 2048000
    
    @pytest.mark.asyncio
    async def test_get_latest_image_s3_error(self, sentinel_service, mock_s3_client):
        """Test image retrieval handles S3 errors"""
        sentinel_service.s3_client = mock_s3_client
        
        # Mock S3 to raise ClientError on generate_presigned_url
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'tiles/43/P/GP/2024/01/15/0/R60m/TCI.jp2',
                    'Size': 2048000
                }
            ]
        }
        mock_s3_client.generate_presigned_url.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'GeneratePresignedUrl'
        )
        
        # Should raise ClientError
        with pytest.raises(ClientError):
            await sentinel_service.get_latest_image(12.97, 77.59)


class TestPresignedURLGeneration:
    """Test presigned URL generation"""
    
    def test_generate_presigned_url_success(self, sentinel_service, mock_s3_client):
        """Test successful presigned URL generation"""
        sentinel_service.s3_client = mock_s3_client
        
        expected_url = 'https://s3.amazonaws.com/sentinel-s2-l2a/tiles/43/P/GP/2024/01/15/0/R60m/TCI.jp2?signature=xyz'
        mock_s3_client.generate_presigned_url.return_value = expected_url
        
        s3_key = 'tiles/43/P/GP/2024/01/15/0/R60m/TCI.jp2'
        url = sentinel_service._generate_presigned_url(s3_key)
        
        assert url == expected_url
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={
                'Bucket': 'sentinel-s2-l2a',
                'Key': s3_key
            },
            ExpiresIn=3600
        )
    
    def test_generate_presigned_url_error(self, sentinel_service, mock_s3_client):
        """Test presigned URL generation handles errors"""
        sentinel_service.s3_client = mock_s3_client
        
        mock_s3_client.generate_presigned_url.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'Key not found'}},
            'GeneratePresignedUrl'
        )
        
        with pytest.raises(ClientError):
            sentinel_service._generate_presigned_url('invalid/key')


class TestImageQualityAssessment:
    """Test image quality assessment"""
    
    def test_assess_quality_usable_image(self, sentinel_service):
        """Test quality assessment for usable image (low cloud cover)"""
        image_metadata = {
            's3_key': 'tiles/43/P/GP/2024/01/15/0/R60m/TCI.jp2',
            'acquisition_date': datetime.now(),
            'size': 2048000
        }
        
        result = sentinel_service._assess_image_quality(image_metadata, cloud_cover=10.0)
        
        assert isinstance(result, ImageQualityResult)
        assert result.is_usable is True
        assert result.quality_assessment == 'usable'
        assert result.cloud_cover_percentage == 10.0
        assert result.data_available is True
        assert result.confidence > 0.7
    
    def test_assess_quality_marginal_image(self, sentinel_service):
        """Test quality assessment for marginal image (moderate cloud cover)"""
        image_metadata = {
            's3_key': 'tiles/43/P/GP/2024/01/15/0/R60m/TCI.jp2',
            'acquisition_date': datetime.now(),
            'size': 2048000
        }
        
        result = sentinel_service._assess_image_quality(image_metadata, cloud_cover=35.0)
        
        assert result.is_usable is True
        assert result.quality_assessment == 'marginal'
        assert result.cloud_cover_percentage == 35.0
        assert 'Moderate cloud cover' in ' '.join(result.issues)
        assert result.confidence < 1.0
    
    def test_assess_quality_unusable_image(self, sentinel_service):
        """Test quality assessment for unusable image (high cloud cover)"""
        image_metadata = {
            's3_key': 'tiles/43/P/GP/2024/01/15/0/R60m/TCI.jp2',
            'acquisition_date': datetime.now(),
            'size': 2048000
        }
        
        result = sentinel_service._assess_image_quality(image_metadata, cloud_cover=75.0)
        
        assert result.is_usable is False
        assert result.quality_assessment == 'unusable'
        assert result.cloud_cover_percentage == 75.0
        assert 'High cloud cover' in ' '.join(result.issues)
        assert result.confidence < 0.5
    
    def test_assess_quality_no_data(self, sentinel_service):
        """Test quality assessment when no data is available"""
        result = sentinel_service._assess_image_quality(None, cloud_cover=None)
        
        assert result.is_usable is False
        assert result.quality_assessment == 'unusable'
        assert result.data_available is False
        assert 'No imagery data available' in result.issues
        assert result.confidence == 0.0
    
    def test_assess_quality_old_image(self, sentinel_service):
        """Test quality assessment for old image"""
        old_date = datetime.now() - timedelta(days=20)
        image_metadata = {
            's3_key': 'tiles/43/P/GP/2024/01/01/0/R60m/TCI.jp2',
            'acquisition_date': old_date,
            'size': 2048000
        }
        
        result = sentinel_service._assess_image_quality(image_metadata, cloud_cover=10.0)
        
        assert result.is_usable is True
        assert 'days old' in ' '.join(result.issues)
        assert result.confidence < 1.0
    
    def test_assess_quality_estimated_cloud_cover(self, sentinel_service):
        """Test quality assessment with estimated cloud cover"""
        image_metadata = {
            's3_key': 'tiles/43/P/GP/2024/01/15/0/R60m/TCI.jp2',
            'acquisition_date': datetime.now(),
            'size': 2048000
        }
        
        result = sentinel_service._assess_image_quality(image_metadata, cloud_cover=None)
        
        assert 'Cloud cover estimated' in ' '.join(result.issues)
        assert result.confidence < 1.0


class TestDataAvailability:
    """Test data availability checking"""
    
    def test_check_data_availability_exists(self, sentinel_service, mock_s3_client):
        """Test data availability check when data exists"""
        sentinel_service.s3_client = mock_s3_client
        
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{'Key': 'tiles/43/P/GP/2024/01/15/0/metadata.xml'}]
        }
        
        available = sentinel_service.check_data_availability(12.97, 77.59)
        
        assert available is True
    
    def test_check_data_availability_not_exists(self, sentinel_service, mock_s3_client):
        """Test data availability check when data doesn't exist"""
        sentinel_service.s3_client = mock_s3_client
        
        mock_s3_client.list_objects_v2.return_value = {}
        
        available = sentinel_service.check_data_availability(12.97, 77.59)
        
        assert available is False
    
    def test_check_data_availability_specific_date(self, sentinel_service, mock_s3_client):
        """Test data availability check for specific date"""
        sentinel_service.s3_client = mock_s3_client
        
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [{'Key': 'tiles/43/P/GP/2024/01/15/0/metadata.xml'}]
        }
        
        specific_date = datetime(2024, 1, 15)
        available = sentinel_service.check_data_availability(12.97, 77.59, date=specific_date)
        
        assert available is True
        
        # Verify correct prefix was used
        call_args = mock_s3_client.list_objects_v2.call_args
        assert '2024/01/15' in call_args[1]['Prefix']
    
    def test_check_data_availability_error_handling(self, sentinel_service, mock_s3_client):
        """Test data availability check handles errors gracefully"""
        sentinel_service.s3_client = mock_s3_client
        
        mock_s3_client.list_objects_v2.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'ListObjectsV2'
        )
        
        available = sentinel_service.check_data_availability(12.97, 77.59)
        
        assert available is False


class TestTileInfo:
    """Test tile information retrieval"""
    
    def test_get_tile_info(self, sentinel_service):
        """Test getting tile information for coordinates"""
        info = sentinel_service.get_tile_info(12.97, 77.59)
        
        assert isinstance(info, dict)
        assert 'tile_id' in info
        assert 'utm_zone' in info
        assert 'latitude_band' in info
        assert 'grid_square' in info
        assert 'coordinates' in info
        assert 'bucket' in info
        assert 'resolution' in info
        
        assert info['tile_id'] == '43PPGP'
        assert info['utm_zone'] == '43'
        assert info['latitude_band'] == 'P'
        assert info['grid_square'] == 'PGP'
        assert info['coordinates'] == {'lat': 12.97, 'lon': 77.59}
        assert info['bucket'] == 'sentinel-s2-l2a'
        assert info['resolution'] == '60m'


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_invalid_coordinates(self, sentinel_service, mock_s3_client):
        """Test handling of invalid coordinates"""
        sentinel_service.s3_client = mock_s3_client
        
        # Mock S3 to return no results
        mock_s3_client.list_objects_v2.return_value = {}
        
        # Should raise ValueError for coordinates with no data
        with pytest.raises(ValueError):
            await sentinel_service.get_latest_image(999.0, 999.0)
    
    @pytest.mark.asyncio
    async def test_network_error(self, sentinel_service, mock_s3_client):
        """Test handling of network errors"""
        sentinel_service.s3_client = mock_s3_client
        
        mock_s3_client.list_objects_v2.side_effect = Exception("Network error")
        
        with pytest.raises(Exception):
            await sentinel_service.get_latest_image(12.97, 77.59)


class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_image_retrieval_workflow(self, sentinel_service, mock_s3_client):
        """Test complete workflow from coordinates to presigned URL"""
        sentinel_service.s3_client = mock_s3_client
        
        # Setup mocks
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'tiles/43/P/GP/2024/01/15/0/R60m/TCI.jp2',
                    'Size': 3072000
                }
            ]
        }
        mock_s3_client.generate_presigned_url.return_value = 'https://s3.amazonaws.com/presigned-url'
        
        # Execute workflow
        result = await sentinel_service.get_latest_image(12.97, 77.59)
        
        # Verify complete result
        assert result.image_url.startswith('https://')
        assert result.tile_id == '43PPGP'
        assert result.quality_assessment in ['usable', 'marginal', 'unusable']
        assert result.metadata['s3_bucket'] == 'sentinel-s2-l2a'
        assert result.metadata['coordinates']['lat'] == 12.97
        assert result.metadata['coordinates']['lon'] == 77.59
        
        # Verify quality assessment
        quality = sentinel_service.assess_image_quality(result)
        assert isinstance(quality, ImageQualityResult)
        assert quality.data_available is True
