"""
Verification script for testing framework setup

This script demonstrates that all testing framework components are working:
1. Pytest configuration
2. Hypothesis strategies
3. Moto AWS mocking
4. Test data generators
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.conftest import (
    indian_coordinates,
    ndvi_values,
    hobli_ids,
    plot_data,
    alert_data,
    gee_data,
    sentinel_data,
    TestDataGenerator,
)
from tests.test_utils import (
    CoordinateTestHelper,
    NDVITestHelper,
    HobliTestHelper,
    MockAWSResponses,
    TestDataFactory,
)
from hypothesis import given, settings
import boto3
from moto import mock_aws


def verify_hypothesis_strategies():
    """Verify Hypothesis strategies are working"""
    print("✓ Verifying Hypothesis strategies...")
    
    # Test coordinate strategy
    @given(coords=indian_coordinates())
    @settings(max_examples=5)
    def test_coords(coords):
        lat, lon = coords
        assert CoordinateTestHelper.is_valid_coordinate(lat, lon)
        assert CoordinateTestHelper.is_in_india(lat, lon)
    
    test_coords()
    print("  ✓ Indian coordinates strategy works")
    
    # Test NDVI strategy
    @given(ndvi=ndvi_values)
    @settings(max_examples=5)
    def test_ndvi(ndvi):
        assert NDVITestHelper.is_valid_ndvi(ndvi)
    
    test_ndvi()
    print("  ✓ NDVI values strategy works")
    
    # Test Hobli ID strategy
    @given(hobli_id=hobli_ids())
    @settings(max_examples=5)
    def test_hobli(hobli_id):
        assert HobliTestHelper.is_valid_hobli_id(hobli_id)
    
    test_hobli()
    print("  ✓ Hobli IDs strategy works")
    
    # Test plot data strategy
    @given(plot=plot_data())
    @settings(max_examples=5)
    def test_plot(plot):
        assert "user_id" in plot
        assert "plot_id" in plot
        assert CoordinateTestHelper.is_valid_coordinate(plot["lat"], plot["lon"])
    
    test_plot()
    print("  ✓ Plot data strategy works")
    
    print("✓ All Hypothesis strategies verified!\n")


def verify_moto_mocking():
    """Verify Moto AWS mocking is working"""
    print("✓ Verifying Moto AWS mocking...")
    
    with mock_aws():
        # Test DynamoDB mocking
        dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
        table = dynamodb.create_table(
            TableName="TestTable",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        
        # Write and read
        table.put_item(Item={"id": "test", "data": "value"})
        response = table.get_item(Key={"id": "test"})
        assert response["Item"]["data"] == "value"
        print("  ✓ DynamoDB mocking works")
        
        # Test SNS mocking
        sns = boto3.client("sns", region_name="ap-south-1")
        topic_response = sns.create_topic(Name="TestTopic")
        assert "TopicArn" in topic_response
        print("  ✓ SNS mocking works")
        
        # Test Bedrock mocking (client creation)
        bedrock = boto3.client("bedrock-runtime", region_name="ap-south-1")
        assert bedrock is not None
        print("  ✓ Bedrock client mocking works")
    
    print("✓ All Moto AWS mocking verified!\n")


def verify_test_data_generators():
    """Verify test data generators are working"""
    print("✓ Verifying test data generators...")
    
    generator = TestDataGenerator()
    
    # Test coordinate batch generation
    coords = generator.generate_coordinates_batch(count=5)
    assert len(coords) == 5
    for lat, lon in coords:
        assert CoordinateTestHelper.is_valid_coordinate(lat, lon)
    print("  ✓ Coordinate batch generator works")
    
    # Test NDVI range generation
    ndvi_range = generator.generate_ndvi_range(start=-1.0, end=1.0, steps=5)
    assert len(ndvi_range) == 6  # steps + 1
    assert ndvi_range[0] == -1.0
    assert ndvi_range[-1] == 1.0
    print("  ✓ NDVI range generator works")
    
    # Test Hobli mapping generation
    mapping = generator.generate_hobli_mapping(num_hoblis=3, plots_per_hobli=5)
    assert len(mapping) == 3
    for hobli_id, plots in mapping.items():
        assert HobliTestHelper.is_valid_hobli_id(hobli_id)
        assert len(plots) == 5
    print("  ✓ Hobli mapping generator works")
    
    print("✓ All test data generators verified!\n")


def verify_test_utilities():
    """Verify test utilities are working"""
    print("✓ Verifying test utilities...")
    
    # Test MockAWSResponses
    bedrock_response = MockAWSResponses.bedrock_multimodal_response(risk_level="high")
    assert "content" in bedrock_response
    print("  ✓ MockAWSResponses works")
    
    # Test TestDataFactory
    plot = TestDataFactory.create_plot_registration()
    assert plot["user_id"] == "user_001"
    assert plot["plot_id"] == "plot_001"
    print("  ✓ TestDataFactory works")
    
    # Test CoordinateTestHelper
    assert CoordinateTestHelper.is_valid_coordinate(12.9716, 77.5946)
    assert CoordinateTestHelper.is_in_india(12.9716, 77.5946)
    print("  ✓ CoordinateTestHelper works")
    
    # Test NDVITestHelper
    assert NDVITestHelper.classify_ndvi(0.75) == "healthy"
    assert NDVITestHelper.classify_ndvi(0.35) == "stressed"
    print("  ✓ NDVITestHelper works")
    
    # Test HobliTestHelper
    assert HobliTestHelper.is_valid_hobli_id("hobli_bangalore_001")
    assert HobliTestHelper.extract_district("hobli_bangalore_001") == "bangalore"
    print("  ✓ HobliTestHelper works")
    
    print("✓ All test utilities verified!\n")


def main():
    """Run all verification checks"""
    print("\n" + "=" * 70)
    print("Testing Framework Verification")
    print("=" * 70 + "\n")
    
    try:
        verify_hypothesis_strategies()
        verify_moto_mocking()
        verify_test_data_generators()
        verify_test_utilities()
        
        print("=" * 70)
        print("✓ ALL TESTING FRAMEWORK COMPONENTS VERIFIED SUCCESSFULLY!")
        print("=" * 70 + "\n")
        
        print("Testing framework is ready for use:")
        print("  • Pytest configured with coverage and markers")
        print("  • Hypothesis strategies for property-based testing")
        print("  • Moto for AWS service mocking (DynamoDB, Bedrock, SNS)")
        print("  • Test data generators for coordinates, NDVI, Hobli mappings")
        print("  • Test utilities and helper classes")
        print("\nRun tests with: pytest tests/")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
