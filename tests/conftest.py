"""
Pytest Configuration and Shared Fixtures

Provides common fixtures for testing all services including:
- AWS service mocking with moto
- Hypothesis strategies for property-based testing
- Test data generators for coordinates, NDVI values, and Hobli mappings
"""

import pytest
from typing import Generator, Dict, Any
import os
import boto3
from moto import mock_aws
from hypothesis import strategies as st
from hypothesis import settings, HealthCheck


# Configure Hypothesis settings for all tests
settings.register_profile("default", max_examples=50, deadline=5000, database=None)
settings.register_profile("ci", max_examples=100, deadline=10000, database=None)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


@pytest.fixture(scope="session")
def aws_credentials():
    """Mock AWS credentials for testing"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"


@pytest.fixture
def sample_coordinates():
    """Sample valid coordinates for testing"""
    return {
        "valid": (12.9716, 77.5946),  # Bangalore, India
        "invalid_lat": (100.0, 77.5946),  # Invalid latitude
        "invalid_lon": (12.9716, 200.0),  # Invalid longitude
        "outside_india": (40.7128, -74.0060),  # New York, USA
    }


@pytest.fixture
def sample_plot_data():
    """Sample plot registration data"""
    return {
        "user_id": "user_001",
        "plot_id": "plot_001",
        "lat": 12.9716,
        "lon": 77.5946,
        "crop": "rice",
        "hobli_id": "hobli_bangalore_001",
        "farmer_name": "Test Farmer",
        "phone_number": "+919876543210",
    }


@pytest.fixture
def sample_alert_data():
    """Sample alert data"""
    return {
        "hobli_id": "hobli_bangalore_001",
        "plot_id": "plot_001",
        "user_id": "user_001",
        "risk_level": "high",
        "message": "Crop stress detected",
        "gee_proof": {
            "ndvi_value": 0.35,
            "moisture_index": 0.25,
            "temperature_anomaly": 2.5,
        },
        "bedrock_reasoning": "Low NDVI indicates vegetation stress",
    }


@pytest.fixture
def sample_ndvi_values():
    """Sample NDVI values for testing"""
    return {
        "healthy": 0.75,
        "moderate": 0.55,
        "stressed": 0.35,
        "critical": 0.15,
    }


@pytest.fixture
def sample_hobli_ids():
    """Sample Hobli identifiers"""
    return [
        "hobli_bangalore_001",
        "hobli_bangalore_002",
        "hobli_mysore_001",
        "hobli_mysore_002",
    ]


@pytest.fixture
def sample_hobli_directory():
    """Sample Hobli directory entry"""
    return {
        "hobli_id": "hobli_bangalore_001",
        "hobli_name": "Bangalore North Hobli",
        "district": "Bangalore Urban",
        "state": "Karnataka",
        "officer_id": "officer_001",
        "officer_name": "Extension Officer Kumar",
        "officer_phone": "+919876543210",
        "officer_email": "kumar@agriculture.gov.in",
    }


# ============================================================================
# AWS Service Mocking Fixtures (moto)
# ============================================================================


@pytest.fixture(scope="function")
def mock_dynamodb_service(aws_credentials):
    """Mock DynamoDB service for testing
    
    Function-scoped to ensure fresh mock for each test.
    """
    with mock_aws():
        yield boto3.resource("dynamodb", region_name="ap-south-1")


@pytest.fixture(scope="function", autouse=False)
def mock_dynamodb_tables(mock_dynamodb_service):
    """Create mock DynamoDB tables for testing
    
    This fixture creates fresh tables for each test to ensure isolation.
    Function-scoped with explicit cleanup to prevent state leakage between
    Hypothesis examples.
    """
    dynamodb = mock_dynamodb_service
    
    # Create PrecisionAgri_Plots table
    plots_table = dynamodb.create_table(
        TableName="PrecisionAgri_Plots",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "plot_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "plot_id", "AttributeType": "S"},
            {"AttributeName": "hobli_id", "AttributeType": "S"},
            {"AttributeName": "registration_date", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "hobli_id-registration_date-index",
                "KeySchema": [
                    {"AttributeName": "hobli_id", "KeyType": "HASH"},
                    {"AttributeName": "registration_date", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            }
        ],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    
    # Create PrecisionAgri_Alerts table
    alerts_table = dynamodb.create_table(
        TableName="PrecisionAgri_Alerts",
        KeySchema=[
            {"AttributeName": "hobli_id", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "hobli_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "S"},
            {"AttributeName": "risk_level", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "risk_level-timestamp-index",
                "KeySchema": [
                    {"AttributeName": "risk_level", "KeyType": "HASH"},
                    {"AttributeName": "timestamp", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            }
        ],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    
    # Create PrecisionAgri_HobliDirectory table
    hobli_directory_table = dynamodb.create_table(
        TableName="PrecisionAgri_HobliDirectory",
        KeySchema=[
            {"AttributeName": "hobli_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "hobli_id", "AttributeType": "S"},
            {"AttributeName": "officer_id", "AttributeType": "S"},
            {"AttributeName": "last_updated", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "officer_id-last_updated-index",
                "KeySchema": [
                    {"AttributeName": "officer_id", "KeyType": "HASH"},
                    {"AttributeName": "last_updated", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            }
        ],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    
    tables = {
        "plots": plots_table, 
        "alerts": alerts_table,
        "hobli_directory": hobli_directory_table
    }
    
    yield tables
    
    # Cleanup is handled by mock_aws context manager
    # No explicit cleanup needed as tables are destroyed with the mock


@pytest.fixture
def mock_bedrock_service(aws_credentials):
    """Mock AWS Bedrock service for testing"""
    with mock_aws():
        yield boto3.client("bedrock-runtime", region_name="ap-south-1")


@pytest.fixture
def mock_sns_service(aws_credentials):
    """Mock AWS SNS service for testing"""
    with mock_aws():
        client = boto3.client("sns", region_name="ap-south-1")
        yield client


@pytest.fixture
def mock_polly_service(aws_credentials):
    """Mock AWS Polly service for testing"""
    with mock_aws():
        yield boto3.client("polly", region_name="ap-south-1")


@pytest.fixture
def mock_transcribe_service(aws_credentials):
    """Mock AWS Transcribe service for testing"""
    with mock_aws():
        yield boto3.client("transcribe", region_name="ap-south-1")


# ============================================================================
# Hypothesis Strategies for Property-Based Testing
# ============================================================================


# Coordinate Strategies
@st.composite
def indian_coordinates(draw):
    """Generate valid coordinates within India's geographic bounds
    
    Constrains float values to DynamoDB-compatible range (1e-130 to 1e+126)
    to avoid number underflow errors.
    """
    # India's approximate bounds: lat 8-37°N, lon 68-97°E
    # Round to 6 decimals to ensure values are well within DynamoDB range
    lat = draw(st.floats(min_value=8.0, max_value=37.0, allow_nan=False, allow_infinity=False))
    lon = draw(st.floats(min_value=68.0, max_value=97.0, allow_nan=False, allow_infinity=False))
    
    # Round to 6 decimals to avoid very small float values
    lat = round(lat, 6)
    lon = round(lon, 6)
    
    # Ensure values are not too small (DynamoDB minimum is ~1e-130)
    if abs(lat) < 1e-100:
        lat = 8.0
    if abs(lon) < 1e-100:
        lon = 68.0
    
    return (lat, lon)


@st.composite
def invalid_coordinates(draw):
    """Generate invalid coordinates for testing validation"""
    choice = draw(st.integers(min_value=0, max_value=2))
    
    if choice == 0:
        # Invalid latitude (outside -90 to 90)
        lat = draw(st.one_of(
            st.floats(min_value=-180, max_value=-91),
            st.floats(min_value=91, max_value=180)
        ))
        lon = draw(st.floats(min_value=-180, max_value=180))
    elif choice == 1:
        # Invalid longitude (outside -180 to 180)
        lat = draw(st.floats(min_value=-90, max_value=90))
        lon = draw(st.one_of(
            st.floats(min_value=-360, max_value=-181),
            st.floats(min_value=181, max_value=360)
        ))
    else:
        # Valid range but outside India
        lat = draw(st.one_of(
            st.floats(min_value=-90, max_value=7.9),
            st.floats(min_value=37.1, max_value=90)
        ))
        lon = draw(st.floats(min_value=-180, max_value=180))
    
    return (lat, lon)


# NDVI Value Strategies - constrained to DynamoDB-compatible range
ndvi_values = st.floats(
    min_value=-1.0, 
    max_value=1.0, 
    allow_nan=False, 
    allow_infinity=False
).map(lambda x: round(x, 6))  # Round to avoid very small values

healthy_ndvi = st.floats(min_value=0.6, max_value=1.0).map(lambda x: round(x, 6))
moderate_ndvi = st.floats(min_value=0.4, max_value=0.6).map(lambda x: round(x, 6))
stressed_ndvi = st.floats(min_value=0.2, max_value=0.4).map(lambda x: round(x, 6))
critical_ndvi = st.floats(min_value=-1.0, max_value=0.2).map(lambda x: round(x, 6))


# Hobli Mapping Strategies
@st.composite
def hobli_ids(draw):
    """Generate valid Hobli identifiers"""
    districts = ["bangalore", "mysore", "mandya", "tumkur", "hassan"]
    district = draw(st.sampled_from(districts))
    number = draw(st.integers(min_value=1, max_value=999))
    return f"hobli_{district}_{number:03d}"


# Plot Data Strategies
@st.composite
def plot_data(draw):
    """Generate complete plot registration data"""
    coords = draw(indian_coordinates())
    crops = ["rice", "wheat", "cotton", "sugarcane", "maize", "pulses"]
    
    return {
        "user_id": f"user_{draw(st.integers(min_value=1, max_value=9999)):04d}",
        "plot_id": f"plot_{draw(st.integers(min_value=1, max_value=9999)):04d}",
        "lat": coords[0],
        "lon": coords[1],
        "crop": draw(st.sampled_from(crops)),
        "hobli_id": draw(hobli_ids()),
        "farmer_name": draw(st.text(min_size=3, max_size=50, alphabet=st.characters(categories=["Lu", "Ll"]))),
        "phone_number": f"+91{draw(st.integers(min_value=6000000000, max_value=9999999999))}",
    }


# Alert Data Strategies
@st.composite
def alert_data(draw):
    """Generate alert data for testing
    
    Constrains all float values to DynamoDB-compatible range.
    """
    risk_levels = ["low", "medium", "high", "critical"]
    
    # Generate DynamoDB-compatible float values (rounded to 6 decimals)
    ndvi = round(draw(ndvi_values), 6)
    moisture = round(draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)), 6)
    temp_anomaly = round(draw(st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False)), 6)
    
    return {
        "hobli_id": draw(hobli_ids()),
        "plot_id": f"plot_{draw(st.integers(min_value=1, max_value=9999)):04d}",
        "user_id": f"user_{draw(st.integers(min_value=1, max_value=9999)):04d}",
        "risk_level": draw(st.sampled_from(risk_levels)),
        "message": draw(st.text(min_size=10, max_size=200, alphabet=st.characters(categories=["Lu", "Ll", "Nd", "Zs"]))),
        "gee_proof": {
            "ndvi_value": ndvi,
            "moisture_index": moisture,
            "temperature_anomaly": temp_anomaly,
        },
        "bedrock_reasoning": draw(st.text(min_size=20, max_size=500, alphabet=st.characters(categories=["Lu", "Ll", "Nd", "Zs", "Po"]))),
    }


# GEE Data Strategies
@st.composite
def gee_data(draw):
    """Generate Google Earth Engine data for testing
    
    Constrains all float values to DynamoDB-compatible range.
    """
    from datetime import datetime, timedelta
    
    # Generate a date within the last year
    days_ago = draw(st.integers(min_value=0, max_value=365))
    acquisition_date = (datetime.now() - timedelta(days=days_ago)).isoformat()
    
    # Round float values to avoid DynamoDB underflow
    ndvi = round(draw(ndvi_values), 6)
    cloud_cover = round(draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)), 6)
    
    return {
        "ndvi_float": ndvi,
        "acquisition_date": acquisition_date,
        "cloud_cover": cloud_cover,
        "metadata": {
            "sensor": draw(st.sampled_from(["Landsat-8", "Sentinel-2"])),
            "resolution": draw(st.sampled_from(["10m", "30m", "60m"])),
            "bands_used": ["SR_B5", "SR_B4"],
        },
    }


# Sentinel Data Strategies
@st.composite
def sentinel_data(draw):
    """Generate Sentinel-2 imagery data for testing
    
    Constrains all float values to DynamoDB-compatible range.
    """
    from datetime import datetime, timedelta
    
    # Generate a date within the last year
    days_ago = draw(st.integers(min_value=0, max_value=365))
    acquisition_date = (datetime.now() - timedelta(days=days_ago)).isoformat()
    
    # Round cloud cover to avoid DynamoDB underflow
    cloud_cover = round(draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)), 6)
    
    return {
        "image_url": f"https://sentinel-s2-l2a.s3.amazonaws.com/tiles/{draw(st.text(min_size=5, max_size=10, alphabet=st.characters(categories=['Lu', 'Nd'])))}/TCI.jp2",
        "tile_id": draw(st.text(min_size=5, max_size=10, alphabet=st.characters(categories=["Lu", "Nd"]))),
        "acquisition_date": acquisition_date,
        "cloud_cover_percentage": cloud_cover,
        "resolution": draw(st.sampled_from(["10m", "20m", "60m"])),
    }


# ============================================================================
# Test Data Generators
# ============================================================================


class TestDataGenerator:
    """Utility class for generating test data"""
    
    @staticmethod
    def generate_coordinates_batch(count: int = 10) -> list:
        """Generate a batch of valid Indian coordinates"""
        coords = []
        for i in range(count):
            lat = 8.0 + (29.0 * (i / count))
            lon = 68.0 + (29.0 * (i / count))
            coords.append((round(lat, 6), round(lon, 6)))
        return coords
    
    @staticmethod
    def generate_ndvi_range(start: float = -1.0, end: float = 1.0, steps: int = 10) -> list:
        """Generate a range of NDVI values"""
        step_size = (end - start) / steps
        return [round(start + (i * step_size), 3) for i in range(steps + 1)]
    
    @staticmethod
    def generate_hobli_mapping(num_hoblis: int = 5, plots_per_hobli: int = 10) -> Dict[str, list]:
        """Generate a mapping of Hoblis to plots"""
        mapping = {}
        districts = ["bangalore", "mysore", "mandya", "tumkur", "hassan"]
        
        for i in range(num_hoblis):
            hobli_id = f"hobli_{districts[i % len(districts)]}_{i+1:03d}"
            plots = [f"plot_{j:04d}" for j in range(i * plots_per_hobli, (i + 1) * plots_per_hobli)]
            mapping[hobli_id] = plots
        
        return mapping


@pytest.fixture
def test_data_generator():
    """Fixture providing test data generator"""
    return TestDataGenerator()


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def map_service():
    """Fixture providing MapService instance for testing"""
    from services.map_service import MapService
    
    return MapService()
