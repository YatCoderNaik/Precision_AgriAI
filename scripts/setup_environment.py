"""
Environment Setup Script

Validates and configures the development environment for Precision AgriAI.
Checks AWS credentials, ISRO Bhuvan access, and Google Earth Engine setup.
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_python_version():
    """Verify Python version is 3.10 or higher"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        logger.error(f"❌ Python 3.10+ required, found {version.major}.{version.minor}")
        return False
    logger.info(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def check_env_file():
    """Check if .env file exists"""
    env_path = Path(".env")
    if not env_path.exists():
        logger.warning("⚠️  .env file not found")
        logger.info("Creating .env from .env.example...")
        
        example_path = Path(".env.example")
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
            logger.info("✓ Created .env file - please configure your credentials")
            return False
        else:
            logger.error("❌ .env.example not found")
            return False
    
    logger.info("✓ .env file exists")
    return True


def check_aws_credentials():
    """Verify AWS credentials are configured"""
    # Check environment variables
    has_env_vars = (
        os.getenv("AWS_ACCESS_KEY_ID") is not None and
        os.getenv("AWS_SECRET_ACCESS_KEY") is not None
    )
    
    # Check AWS credentials file
    aws_creds_path = Path.home() / ".aws" / "credentials"
    has_credentials_file = aws_creds_path.exists()
    
    if has_env_vars:
        logger.info("✓ AWS credentials found in environment variables")
        return True
    elif has_credentials_file:
        logger.info("✓ AWS credentials found in ~/.aws/credentials")
        return True
    else:
        logger.warning("⚠️  AWS credentials not found")
        logger.info("Configure AWS credentials using one of these methods:")
        logger.info("  1. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        logger.info("  2. Run 'aws configure' to set up ~/.aws/credentials")
        return False


def check_gee_credentials():
    """Verify Google Earth Engine credentials"""
    # Check for GEE credentials file
    gee_creds_path = Path.home() / ".config" / "earthengine" / "credentials"
    
    if gee_creds_path.exists():
        logger.info("✓ Google Earth Engine credentials found")
        return True
    else:
        logger.warning("⚠️  Google Earth Engine credentials not found")
        logger.info("To authenticate with Google Earth Engine:")
        logger.info("  1. Install earthengine-api: pip install earthengine-api")
        logger.info("  2. Run: earthengine authenticate")
        logger.info("  3. Follow the authentication flow")
        return False


def check_required_packages():
    """Check if required packages are installed"""
    required_packages = [
        'streamlit',
        'boto3',
        'pydantic',
        'folium',
        'earthengine',
        'httpx'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✓ {package} installed")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"⚠️  {package} not installed")
    
    if missing_packages:
        logger.info("\nInstall missing packages with:")
        logger.info("  pip install -e .[dev]")
        return False
    
    return True


def check_directory_structure():
    """Verify project directory structure"""
    required_dirs = [
        'services',
        'config',
        'scripts',
        'tests'
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            logger.info(f"✓ {dir_name}/ directory exists")
        else:
            logger.warning(f"⚠️  {dir_name}/ directory missing")
            all_exist = False
    
    return all_exist


def test_aws_connection():
    """Test AWS connection"""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        
        # Try to list DynamoDB tables
        dynamodb = boto3.client('dynamodb', region_name='ap-south-1')
        response = dynamodb.list_tables()
        
        logger.info("✓ AWS connection successful")
        logger.info(f"  Found {len(response.get('TableNames', []))} DynamoDB tables")
        return True
        
    except NoCredentialsError:
        logger.error("❌ AWS credentials not configured")
        return False
    except ClientError as e:
        logger.error(f"❌ AWS connection failed: {e}")
        return False
    except ImportError:
        logger.warning("⚠️  boto3 not installed - skipping AWS connection test")
        return False


def main():
    """Main setup validation"""
    logger.info("=" * 60)
    logger.info("Precision AgriAI - Environment Setup Validation")
    logger.info("=" * 60)
    logger.info("")
    
    checks = {
        "Python Version": check_python_version(),
        "Environment File": check_env_file(),
        "AWS Credentials": check_aws_credentials(),
        "GEE Credentials": check_gee_credentials(),
        "Required Packages": check_required_packages(),
        "Directory Structure": check_directory_structure(),
        "AWS Connection": test_aws_connection()
    }
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Setup Validation Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    for check_name, result in checks.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {check_name}")
    
    logger.info("")
    logger.info(f"Passed: {passed}/{total} checks")
    
    if passed == total:
        logger.info("")
        logger.info("🎉 Environment setup complete!")
        logger.info("You can now run: streamlit run app.py")
        return 0
    else:
        logger.info("")
        logger.info("⚠️  Some checks failed - please review the output above")
        logger.info("Refer to README.md for detailed setup instructions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
