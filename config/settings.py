"""
Application Settings and Configuration

Centralized configuration management for all services using Pydantic.
Supports environment variables and AWS credentials management.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
import os


class AWSConfig(BaseModel):
    """AWS service configuration"""
    region: str = Field(default="ap-south-1", description="AWS region for services")
    access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    
    # DynamoDB configuration
    dynamodb_plots_table: str = Field(
        default="PrecisionAgri_Plots",
        description="DynamoDB table for plot data"
    )
    dynamodb_alerts_table: str = Field(
        default="PrecisionAgri_Alerts",
        description="DynamoDB table for alert data"
    )
    
    # Bedrock configuration
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        description="AWS Bedrock model ID for multimodal analysis"
    )
    bedrock_haiku_model_id: str = Field(
        default="anthropic.claude-3-haiku-20240307-v1:0",
        description="AWS Bedrock Haiku model for faster responses"
    )
    
    # S3 configuration
    s3_audio_bucket: str = Field(
        default="precision-agriai-audio",
        description="S3 bucket for audio files"
    )
    
    # SNS configuration
    sns_topic_arn: Optional[str] = Field(
        default=None,
        description="SNS topic ARN for SMS notifications"
    )


class MapServiceConfig(BaseModel):
    """MapService configuration"""
    bhuvan_base_url: str = Field(
        default="https://bhuvan-vec1.nrsc.gov.in/bhuvan/gwc/service/wms",
        description="ISRO Bhuvan WMS base URL"
    )
    bhuvan_default_layer: str = Field(
        default="LISS3",
        description="Default Bhuvan layer"
    )
    india_lat_bounds: tuple[float, float] = Field(
        default=(6.0, 37.0),
        description="Valid latitude bounds for India"
    )
    india_lon_bounds: tuple[float, float] = Field(
        default=(68.0, 97.0),
        description="Valid longitude bounds for India"
    )
    coordinate_precision: int = Field(
        default=4,
        description="Minimum decimal places for coordinates"
    )
    
    @field_validator('india_lat_bounds', 'india_lon_bounds')
    @classmethod
    def validate_bounds(cls, v):
        """Validate that bounds are in correct order"""
        if v[0] >= v[1]:
            raise ValueError(f"Invalid bounds: min ({v[0]}) must be less than max ({v[1]})")
        return v


class GEEConfig(BaseModel):
    """Google Earth Engine configuration"""
    service_account_email: Optional[str] = Field(
        default=None,
        description="GEE service account email"
    )
    private_key_path: Optional[str] = Field(
        default=None,
        description="Path to GEE private key file"
    )
    ndvi_collection: str = Field(
        default="LANDSAT/LC08/C02/T1_L2",
        description="Default satellite collection for NDVI"
    )
    cloud_cover_threshold: float = Field(
        default=20.0,
        description="Maximum cloud cover percentage"
    )


class SentinelConfig(BaseModel):
    """Sentinel-2 AWS Open Data configuration"""
    s3_bucket: str = Field(
        default="sentinel-s2-l2a",
        description="AWS Open Data Sentinel-2 bucket"
    )
    default_resolution: str = Field(
        default="60m",
        description="Default image resolution"
    )
    presigned_url_expiry: int = Field(
        default=3600,
        description="Presigned URL expiry in seconds"
    )


class VoiceServiceConfig(BaseModel):
    """VoiceService configuration"""
    default_language: str = Field(
        default="en-IN",
        description="Default language for voice interaction"
    )
    transcribe_timeout: int = Field(
        default=30,
        description="Transcription timeout in seconds"
    )
    polly_voice_id: str = Field(
        default="Aditi",
        description="Default AWS Polly voice ID"
    )
    audio_format: str = Field(
        default="mp3",
        description="Audio output format"
    )


class DbServiceConfig(BaseModel):
    """DbService configuration"""
    read_capacity_units: int = Field(
        default=5,
        description="DynamoDB read capacity units"
    )
    write_capacity_units: int = Field(
        default=5,
        description="DynamoDB write capacity units"
    )
    enable_point_in_time_recovery: bool = Field(
        default=True,
        description="Enable point-in-time recovery for tables"
    )
    enable_encryption: bool = Field(
        default=True,
        description="Enable encryption at rest"
    )
    query_limit: int = Field(
        default=100,
        description="Default query result limit"
    )
    batch_write_size: int = Field(
        default=25,
        description="Maximum batch write size"
    )


class BrainServiceConfig(BaseModel):
    """BrainService configuration"""
    max_tokens: int = Field(
        default=1000,
        description="Maximum tokens for Bedrock responses"
    )
    temperature: float = Field(
        default=0.7,
        description="Temperature for Bedrock model"
    )
    enable_multimodal: bool = Field(
        default=True,
        description="Enable multimodal analysis with images"
    )
    ndvi_threshold_critical: float = Field(
        default=0.2,
        description="NDVI threshold for critical risk"
    )
    ndvi_threshold_high: float = Field(
        default=0.3,
        description="NDVI threshold for high risk"
    )
    ndvi_threshold_medium: float = Field(
        default=0.5,
        description="NDVI threshold for medium risk"
    )
    cluster_outbreak_min_plots: int = Field(
        default=3,
        description="Minimum plots for cluster outbreak detection"
    )
    
    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        """Validate temperature is in valid range"""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Temperature must be between 0.0 and 1.0, got {v}")
        return v
    
    @field_validator('ndvi_threshold_critical', 'ndvi_threshold_high', 'ndvi_threshold_medium')
    @classmethod
    def validate_ndvi_threshold(cls, v):
        """Validate NDVI threshold is in valid range"""
        if not -1.0 <= v <= 1.0:
            raise ValueError(f"NDVI threshold must be between -1.0 and 1.0, got {v}")
        return v


class PerformanceConfig(BaseModel):
    """Performance and optimization configuration"""
    max_response_time_seconds: int = Field(
        default=8,
        description="Maximum end-to-end response time"
    )
    concurrent_fetch_enabled: bool = Field(
        default=True,
        description="Enable concurrent data fetching"
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache TTL for repeated requests"
    )
    max_concurrent_requests: int = Field(
        default=10,
        description="Maximum concurrent requests"
    )


class Settings(BaseSettings):
    """Main application settings"""
    
    # Application metadata
    app_name: str = Field(default="Precision AgriAI", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    debug: bool = Field(default=True, description="Debug mode")
    
    # Service configurations
    aws: AWSConfig = Field(default_factory=AWSConfig)
    map_service: MapServiceConfig = Field(default_factory=MapServiceConfig)
    gee: GEEConfig = Field(default_factory=GEEConfig)
    sentinel: SentinelConfig = Field(default_factory=SentinelConfig)
    voice_service: VoiceServiceConfig = Field(default_factory=VoiceServiceConfig)
    db_service: DbServiceConfig = Field(default_factory=DbServiceConfig)
    brain_service: BrainServiceConfig = Field(default_factory=BrainServiceConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings instance
    
    Returns:
        Settings instance
    """
    return settings


def validate_aws_credentials() -> tuple[bool, str]:
    """
    Validate AWS credentials are configured
    
    Returns:
        Tuple of (is_valid, message)
    """
    # Check environment variables or AWS credentials file
    has_env_vars = (
        os.getenv("AWS_ACCESS_KEY_ID") is not None and
        os.getenv("AWS_SECRET_ACCESS_KEY") is not None
    )
    
    has_credentials_file = os.path.exists(
        os.path.expanduser("~/.aws/credentials")
    )
    
    if has_env_vars:
        return True, "AWS credentials found in environment variables"
    elif has_credentials_file:
        return True, "AWS credentials found in ~/.aws/credentials"
    else:
        return False, "No AWS credentials found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables or configure ~/.aws/credentials"


def validate_gee_credentials() -> tuple[bool, str]:
    """
    Validate Google Earth Engine credentials are configured
    
    Returns:
        Tuple of (is_valid, message)
    """
    settings = get_settings()
    
    if settings.gee.service_account_email and settings.gee.private_key_path:
        if os.path.exists(settings.gee.private_key_path):
            return True, f"GEE service account credentials found at {settings.gee.private_key_path}"
        else:
            return False, f"GEE private key file not found at {settings.gee.private_key_path}"
    
    # Check for default GEE credentials
    default_creds = os.path.expanduser("~/.config/earthengine/credentials")
    if os.path.exists(default_creds):
        return True, f"GEE credentials found at {default_creds}"
    
    return False, "No GEE credentials found. Run 'earthengine authenticate' or configure service account"


def validate_configuration() -> dict[str, tuple[bool, str]]:
    """
    Validate all configuration requirements
    
    Returns:
        Dictionary of validation results with component names as keys
    """
    results = {}
    
    # Validate AWS credentials
    results["aws_credentials"] = validate_aws_credentials()
    
    # Validate GEE credentials
    results["gee_credentials"] = validate_gee_credentials()
    
    # Validate AWS region
    settings = get_settings()
    if settings.aws.region:
        results["aws_region"] = (True, f"AWS region set to {settings.aws.region}")
    else:
        results["aws_region"] = (False, "AWS region not configured")
    
    # Validate coordinate bounds
    lat_bounds = settings.map_service.india_lat_bounds
    lon_bounds = settings.map_service.india_lon_bounds
    if lat_bounds[0] < lat_bounds[1] and lon_bounds[0] < lon_bounds[1]:
        results["coordinate_bounds"] = (True, f"Coordinate bounds configured: lat {lat_bounds}, lon {lon_bounds}")
    else:
        results["coordinate_bounds"] = (False, "Invalid coordinate bounds configuration")
    
    # Validate DynamoDB table names
    if settings.aws.dynamodb_plots_table and settings.aws.dynamodb_alerts_table:
        results["dynamodb_tables"] = (True, f"DynamoDB tables: {settings.aws.dynamodb_plots_table}, {settings.aws.dynamodb_alerts_table}")
    else:
        results["dynamodb_tables"] = (False, "DynamoDB table names not configured")
    
    # Validate Bedrock model IDs
    if settings.aws.bedrock_model_id and settings.aws.bedrock_haiku_model_id:
        results["bedrock_models"] = (True, f"Bedrock models configured: {settings.aws.bedrock_model_id}, {settings.aws.bedrock_haiku_model_id}")
    else:
        results["bedrock_models"] = (False, "Bedrock model IDs not configured")
    
    return results


def print_configuration_status():
    """
    Print configuration validation status to console
    """
    print("\n" + "="*60)
    print("Precision AgriAI Configuration Status")
    print("="*60 + "\n")
    
    results = validate_configuration()
    
    all_valid = True
    for component, (is_valid, message) in results.items():
        status = "✓" if is_valid else "✗"
        print(f"{status} {component}: {message}")
        if not is_valid:
            all_valid = False
    
    print("\n" + "="*60)
    if all_valid:
        print("✓ All configuration checks passed")
    else:
        print("✗ Some configuration checks failed - please review above")
    print("="*60 + "\n")
    
    return all_valid
