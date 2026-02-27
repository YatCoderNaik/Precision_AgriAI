# Configuration Guide

This directory contains the configuration management system for Precision AgriAI.

## Overview

The configuration system uses Pydantic for validation and supports environment variables through `.env` files. All service configurations are centralized in `settings.py`.

## Configuration Files

- **settings.py**: Main configuration module with Pydantic models for all services
- **.env**: Environment-specific configuration (not in version control)
- **.env.example**: Template for environment configuration

## Service Configurations

### AWSConfig
AWS service configuration including:
- Region selection
- DynamoDB table names
- Bedrock model IDs
- S3 bucket names
- SNS topic ARN

### MapServiceConfig
ISRO Bhuvan integration configuration:
- Bhuvan WMS base URL
- Default layer selection
- India coordinate bounds validation
- Coordinate precision requirements

### GEEConfig
Google Earth Engine configuration:
- Service account credentials
- NDVI collection selection
- Cloud cover thresholds

### SentinelConfig
Sentinel-2 AWS Open Data configuration:
- S3 bucket name
- Image resolution
- Presigned URL expiry

### VoiceServiceConfig
AWS Transcribe/Polly configuration:
- Default language
- Transcription timeout
- Polly voice ID
- Audio format

### DbServiceConfig
DynamoDB service configuration:
- Read/write capacity units
- Point-in-time recovery
- Encryption settings
- Query limits

### BrainServiceConfig
Multimodal AI configuration:
- Bedrock model parameters (max tokens, temperature)
- NDVI risk thresholds
- Cluster outbreak detection settings

### PerformanceConfig
System performance configuration:
- Maximum response time
- Concurrent processing settings
- Cache TTL
- Request limits

## Setup Instructions

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Configure AWS credentials:**
   
   Option A - Environment variables:
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_REGION=ap-south-1
   ```
   
   Option B - AWS credentials file:
   ```bash
   aws configure
   ```

3. **Configure Google Earth Engine (optional):**
   ```bash
   earthengine authenticate
   ```
   
   Or use service account:
   ```bash
   export GEE__SERVICE_ACCOUNT_EMAIL=your-service-account@project.iam.gserviceaccount.com
   export GEE__PRIVATE_KEY_PATH=/path/to/private-key.json
   ```

4. **Validate configuration:**
   ```bash
   python scripts/validate_config.py
   ```

## Environment Variable Naming

Environment variables use double underscore (`__`) for nested configuration:

```bash
# Top-level setting
ENVIRONMENT=production

# Nested setting (aws.region)
AWS__REGION=ap-south-1

# Deeply nested setting (map_service.india_lat_bounds)
MAP_SERVICE__INDIA_LAT_BOUNDS=(6.0, 37.0)
```

## Configuration Validation

The system includes comprehensive validation:

1. **Credential validation**: Checks AWS and GEE credentials
2. **Bounds validation**: Ensures coordinate bounds are valid
3. **Threshold validation**: Validates NDVI thresholds are in range [-1, 1]
4. **Temperature validation**: Ensures Bedrock temperature is in range [0, 1]

Run validation:
```bash
python scripts/validate_config.py
```

## Usage in Code

```python
from config.settings import get_settings

# Get settings instance
settings = get_settings()

# Access configuration
region = settings.aws.region
ndvi_threshold = settings.brain_service.ndvi_threshold_high
bhuvan_url = settings.map_service.bhuvan_base_url

# Validate credentials
from config.settings import validate_aws_credentials, validate_gee_credentials

aws_valid, aws_msg = validate_aws_credentials()
gee_valid, gee_msg = validate_gee_credentials()
```

## Security Best Practices

1. **Never commit .env files** - They contain sensitive credentials
2. **Use IAM roles** when running on AWS (EC2, ECS, Lambda)
3. **Rotate credentials regularly**
4. **Use AWS Secrets Manager** for production deployments
5. **Enable encryption** for DynamoDB tables (enabled by default)
6. **Use least-privilege IAM policies**

## Required AWS Permissions

The application requires the following AWS permissions:

### DynamoDB
- `dynamodb:CreateTable`
- `dynamodb:DescribeTable`
- `dynamodb:PutItem`
- `dynamodb:GetItem`
- `dynamodb:Query`
- `dynamodb:UpdateItem`
- `dynamodb:DeleteItem`

### Bedrock
- `bedrock:InvokeModel`

### S3
- `s3:GetObject`
- `s3:PutObject`
- `s3:ListBucket`

### Transcribe
- `transcribe:StartTranscriptionJob`
- `transcribe:GetTranscriptionJob`

### Polly
- `polly:SynthesizeSpeech`

### SNS (optional)
- `sns:Publish`

## Troubleshooting

### AWS Credentials Not Found
```
✗ aws_credentials: No AWS credentials found
```
**Solution**: Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables or run `aws configure`

### GEE Credentials Not Found
```
✗ gee_credentials: No GEE credentials found
```
**Solution**: Run `earthengine authenticate` or configure service account credentials

### Invalid Configuration Values
```
ValueError: Temperature must be between 0.0 and 1.0
```
**Solution**: Check your .env file and ensure all values are within valid ranges

### DynamoDB Tables Not Found
```
✗ Table PrecisionAgri_Plots does not exist
```
**Solution**: Run `python scripts/create_dynamodb_tables.py --action create`

## Production Deployment

For production deployments:

1. Set `ENVIRONMENT=production` in .env
2. Set `DEBUG=false`
3. Use IAM roles instead of access keys
4. Enable point-in-time recovery for DynamoDB
5. Enable encryption at rest
6. Configure CloudWatch logging
7. Set appropriate capacity units for DynamoDB based on load

## Support

For configuration issues, check:
1. Configuration validation output
2. Application logs
3. AWS CloudWatch logs
4. Service-specific error messages
