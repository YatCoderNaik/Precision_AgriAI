# Precision AgriAI Testing Framework

This directory contains the comprehensive testing framework for the Precision AgriAI Service-Based Monolith.

## Overview

The testing framework includes:
- **Unit Tests**: Test individual components and functions
- **Integration Tests**: Test service coordination and workflows
- **Property-Based Tests**: Test universal correctness properties using Hypothesis

## Directory Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest fixtures and Hypothesis strategies
├── pytest.ini                  # Pytest configuration
├── hypothesis_config.py        # Hypothesis profiles and settings
├── test_utils.py              # Test utilities and helpers
├── README.md                  # This file
├── unit/                      # Unit tests
│   ├── __init__.py
│   ├── test_db_service.py
│   ├── test_map_service.py
│   ├── test_brain_service.py
│   └── test_voice_service.py
├── integration/               # Integration tests
│   ├── __init__.py
│   ├── test_service_coordination.py
│   └── test_end_to_end_workflow.py
└── property/                  # Property-based tests
    ├── __init__.py
    ├── test_framework_setup.py
    ├── test_data_persistence.py
    ├── test_map_interface.py
    ├── test_multimodal_analysis.py
    └── test_concurrent_processing.py
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Types
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Property-based tests only
pytest -m property

# AWS service tests
pytest -m aws

# DynamoDB tests
pytest -m dynamodb
```

### Run with Coverage
```bash
pytest --cov=services --cov=config --cov-report=html
```

### Run with Different Hypothesis Profiles
```bash
# Default profile (50 examples)
pytest tests/property/

# Development profile (20 examples, fast feedback)
HYPOTHESIS_PROFILE=dev pytest tests/property/

# CI profile (100 examples)
HYPOTHESIS_PROFILE=ci pytest tests/property/

# Thorough profile (500 examples)
HYPOTHESIS_PROFILE=thorough pytest tests/property/

# Debug profile (10 examples, verbose output)
HYPOTHESIS_PROFILE=debug pytest tests/property/
```

## Testing Framework Components

### 1. Pytest Configuration (`pytest.ini`)

Configures pytest with:
- Test discovery patterns
- Coverage reporting
- Markers for test categorization
- Asyncio support
- Timeout settings

### 2. Hypothesis Configuration (`hypothesis_config.py`)

Defines profiles for property-based testing:
- **default**: 50 examples, 5s deadline
- **dev**: 20 examples, 2s deadline (fast feedback)
- **ci**: 100 examples, 10s deadline (CI/CD)
- **debug**: 10 examples, no deadline (debugging)
- **thorough**: 500 examples, 30s deadline (comprehensive)

### 3. Fixtures and Strategies (`conftest.py`)

#### AWS Service Mocking (moto)
- `mock_dynamodb_service`: Mock DynamoDB resource
- `mock_dynamodb_tables`: Pre-configured DynamoDB tables
- `mock_bedrock_service`: Mock AWS Bedrock client
- `mock_sns_service`: Mock AWS SNS client
- `mock_polly_service`: Mock AWS Polly client
- `mock_transcribe_service`: Mock AWS Transcribe client

#### Hypothesis Strategies
- `indian_coordinates()`: Valid coordinates within India
- `invalid_coordinates()`: Invalid coordinates for validation testing
- `ndvi_values`: NDVI values in range [-1, 1]
- `healthy_ndvi`: NDVI values indicating healthy vegetation (0.6-1.0)
- `moderate_ndvi`: NDVI values indicating moderate health (0.4-0.6)
- `stressed_ndvi`: NDVI values indicating stress (0.2-0.4)
- `critical_ndvi`: NDVI values indicating critical stress (-1.0-0.2)
- `hobli_ids()`: Valid Hobli identifiers
- `plot_data()`: Complete plot registration data
- `alert_data()`: Alert data with GEE proof
- `gee_data()`: Google Earth Engine analysis data
- `sentinel_data()`: Sentinel-2 imagery data

#### Test Data Generators
- `TestDataGenerator.generate_coordinates_batch()`: Batch coordinate generation
- `TestDataGenerator.generate_ndvi_range()`: NDVI value ranges
- `TestDataGenerator.generate_hobli_mapping()`: Hobli-to-plot mappings

### 4. Test Utilities (`test_utils.py`)

#### Mock AWS Responses
- `MockAWSResponses.bedrock_multimodal_response()`: Mock Bedrock responses
- `MockAWSResponses.polly_synthesize_speech_response()`: Mock Polly responses
- `MockAWSResponses.transcribe_job_response()`: Mock Transcribe responses
- `MockAWSResponses.sns_publish_response()`: Mock SNS responses

#### Test Data Factories
- `TestDataFactory.create_plot_registration()`: Create plot data
- `TestDataFactory.create_alert()`: Create alert data
- `TestDataFactory.create_gee_analysis()`: Create GEE data
- `TestDataFactory.create_sentinel_data()`: Create Sentinel data

#### Helper Classes
- `CoordinateTestHelper`: Coordinate validation and calculations
- `NDVITestHelper`: NDVI classification and validation
- `HobliTestHelper`: Hobli ID validation and grouping
- `PerformanceTestHelper`: Execution time measurement

## Property-Based Testing

Property-based tests validate universal correctness properties across all valid inputs. Each property test:

1. **Generates diverse test cases** using Hypothesis strategies
2. **Validates invariants** that should hold for all inputs
3. **Automatically shrinks** failing examples to minimal cases
4. **Provides counterexamples** when properties fail

### Example Property Test

```python
from hypothesis import given
from tests.conftest import indian_coordinates

@given(coords=indian_coordinates())
def test_coordinate_validation_consistency(coords):
    """
    Property: All valid Indian coordinates should pass validation
    """
    lat, lon = coords
    result = validate_coordinates(lat, lon)
    assert result.is_valid
    assert result.error is None
```

## AWS Service Mocking

The framework uses `moto` to mock AWS services for testing without real AWS resources:

```python
def test_plot_registration(mock_dynamodb_tables):
    """Test plot registration with mocked DynamoDB"""
    plots_table = mock_dynamodb_tables["plots"]
    
    # Write to mocked table
    plots_table.put_item(Item={
        "user_id": "user_001",
        "plot_id": "plot_001",
        "lat": 12.9716,
        "lon": 77.5946,
    })
    
    # Read from mocked table
    response = plots_table.get_item(Key={
        "user_id": "user_001",
        "plot_id": "plot_001",
    })
    
    assert response["Item"]["lat"] == 12.9716
```

## Test Markers

Use markers to categorize and filter tests:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.property`: Property-based tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.aws`: Tests requiring AWS mocking
- `@pytest.mark.dynamodb`: DynamoDB-specific tests
- `@pytest.mark.bedrock`: Bedrock-specific tests
- `@pytest.mark.sns`: SNS-specific tests
- `@pytest.mark.voice`: Voice service tests

## Performance Testing

The framework includes utilities for performance testing:

```python
from tests.test_utils import PerformanceTestHelper

def test_analysis_performance():
    """Test that analysis completes within 8 seconds"""
    result, execution_time = PerformanceTestHelper.measure_execution_time(
        analyze_plot, lat=12.9716, lon=77.5946
    )
    
    PerformanceTestHelper.assert_within_time_limit(
        execution_time, 
        limit=8.0,
        message="Plot analysis"
    )
```

## Best Practices

1. **Use fixtures for setup**: Leverage pytest fixtures for test setup and teardown
2. **Mock external services**: Use moto for AWS services, avoid real API calls
3. **Write property tests**: Validate universal properties, not just specific examples
4. **Test edge cases**: Use Hypothesis to automatically discover edge cases
5. **Measure performance**: Use PerformanceTestHelper for timing-critical code
6. **Categorize tests**: Use markers to organize and filter tests
7. **Keep tests isolated**: Each test should be independent and repeatable
8. **Document properties**: Clearly state what property each test validates

## Continuous Integration

The testing framework is designed for CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    HYPOTHESIS_PROFILE=ci pytest --cov=services --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Hypothesis finds a failing example
1. Hypothesis will automatically shrink the example to the minimal failing case
2. The failing example will be printed in the test output
3. Fix the code or adjust the property if the example reveals a valid edge case
4. Re-run the test to verify the fix

### Tests are too slow
1. Use the `dev` profile for faster feedback during development
2. Use `@pytest.mark.slow` to mark slow tests
3. Run fast tests first: `pytest -m "not slow"`

### Moto mocking issues
1. Ensure `aws_credentials` fixture is used
2. Check that moto decorators are applied correctly
3. Verify AWS service client creation happens within the mock context

## Contributing

When adding new tests:
1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Place property tests in `tests/property/`
4. Add appropriate markers
5. Document what property or behavior is being tested
6. Update this README if adding new utilities or strategies
