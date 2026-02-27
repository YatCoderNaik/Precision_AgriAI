# Precision AgriAI - Setup Guide

This guide will help you set up the development environment for Precision AgriAI, a Service-Based Monolith application for AI-driven agricultural monitoring.

## Prerequisites

- **Python 3.10 or higher** (required for modern type hints and async features)
- **AWS Account** with access to:
  - DynamoDB
  - AWS Bedrock (Claude 3)
  - AWS Transcribe
  - AWS Polly
  - AWS SNS
  - S3
- **Google Earth Engine Account** (for satellite data)
- **Git** for version control

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd precision-agriai
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install all dependencies including development tools
pip install -e .[dev]

# Or install from requirements.txt
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
# Use your preferred text editor
```

**Required Environment Variables:**

```env
# AWS Configuration
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key

# DynamoDB Tables
AWS__DYNAMODB_PLOTS_TABLE=PrecisionAgri_Plots
AWS__DYNAMODB_ALERTS_TABLE=PrecisionAgri_Alerts

# AWS Bedrock Models
AWS__BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AWS__BEDROCK_HAIKU_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Google Earth Engine
GEE__SERVICE_ACCOUNT_EMAIL=your-service-account@project.iam.gserviceaccount.com
GEE__PRIVATE_KEY_PATH=/path/to/gee-private-key.json
```

### 5. Set Up AWS Credentials

**Option A: Environment Variables (Recommended for Development)**

Already configured in `.env` file above.

**Option B: AWS CLI Configuration**

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
```

Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (ap-south-1)
- Default output format (json)

### 6. Set Up Google Earth Engine

```bash
# Authenticate with Google Earth Engine
earthengine authenticate

# Follow the browser authentication flow
# This will create credentials in ~/.config/earthengine/
```

**For Service Account (Production):**

1. Create a service account in Google Cloud Console
2. Download the private key JSON file
3. Set the path in `.env`:
   ```env
   GEE__SERVICE_ACCOUNT_EMAIL=your-service-account@project.iam.gserviceaccount.com
   GEE__PRIVATE_KEY_PATH=/path/to/gee-private-key.json
   ```

### 7. Create DynamoDB Tables

```bash
# Create both tables (PrecisionAgri_Plots and PrecisionAgri_Alerts)
python scripts/create_dynamodb_tables.py --action create

# Optional: Specify custom table names or region
python scripts/create_dynamodb_tables.py \
  --action create \
  --region ap-south-1 \
  --plots-table PrecisionAgri_Plots \
  --alerts-table PrecisionAgri_Alerts
```

**Table Management Commands:**

```bash
# Delete tables (WARNING: Deletes all data!)
python scripts/create_dynamodb_tables.py --action delete

# Recreate tables (WARNING: Deletes and recreates!)
python scripts/create_dynamodb_tables.py --action recreate
```

### 8. Validate Environment Setup

```bash
# Run the setup validation script
python scripts/setup_environment.py
```

This script checks:
- ✓ Python version (3.10+)
- ✓ Environment file (.env)
- ✓ AWS credentials
- ✓ Google Earth Engine credentials
- ✓ Required packages
- ✓ Directory structure
- ✓ AWS connection

### 9. Run the Application

```bash
# Start the Streamlit application
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## Project Structure

```
precision-agriai/
├── app.py                      # Main Streamlit application
├── pyproject.toml              # Project configuration and dependencies
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
├── .env.example                # Example environment configuration
├── README.md                   # Project overview
├── SETUP.md                    # This setup guide
│
├── services/                   # Internal services (Service-Based Monolith)
│   ├── __init__.py
│   ├── map_service.py         # ISRO Bhuvan integration
│   ├── voice_service.py       # AWS Transcribe/Polly
│   ├── brain_service.py       # Multimodal AI orchestration
│   └── db_service.py          # DynamoDB operations
│
├── config/                     # Configuration management
│   ├── __init__.py
│   └── settings.py            # Pydantic settings models
│
├── scripts/                    # Setup and utility scripts
│   ├── __init__.py
│   ├── create_dynamodb_tables.py
│   └── setup_environment.py
│
└── tests/                      # Test suite (to be created in Task 1.2)
    ├── __init__.py
    ├── unit/
    ├── integration/
    └── property/
```

## AWS Services Configuration

### DynamoDB Tables

**PrecisionAgri_Plots:**
- Partition Key: `user_id` (String)
- Sort Key: `plot_id` (String)
- GSI: `hobli_id-registration_date-index`

**PrecisionAgri_Alerts:**
- Partition Key: `hobli_id` (String)
- Sort Key: `timestamp` (String)
- GSI: `risk_level-timestamp-index`

### AWS Bedrock

Ensure you have access to:
- `anthropic.claude-3-sonnet-20240229-v1:0` (multimodal analysis)
- `anthropic.claude-3-haiku-20240307-v1:0` (faster responses)

Request model access in AWS Console:
1. Go to AWS Bedrock console
2. Navigate to "Model access"
3. Request access to Anthropic Claude 3 models

### AWS S3

Create an S3 bucket for audio files:
```bash
aws s3 mb s3://precision-agriai-audio --region ap-south-1
```

### AWS SNS

Create an SNS topic for SMS notifications:
```bash
aws sns create-topic --name precision-agriai-alerts --region ap-south-1
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov-report=html

# Run specific test file
pytest tests/unit/test_map_service.py

# Run property-based tests
pytest tests/property/
```

### Code Formatting

```bash
# Format code with black
black .

# Sort imports
isort .

# Check code style
flake8 services/ config/

# Type checking
mypy services/ config/
```

### Running in Development Mode

```bash
# Enable debug mode in .env
DEBUG=true

# Run with auto-reload
streamlit run app.py --server.runOnSave true
```

## Troubleshooting

### AWS Credentials Not Found

**Error:** `NoCredentialsError: Unable to locate credentials`

**Solution:**
1. Verify `.env` file has AWS credentials
2. Or run `aws configure` to set up `~/.aws/credentials`
3. Check environment variables: `echo $AWS_ACCESS_KEY_ID`

### Google Earth Engine Authentication Failed

**Error:** `EEException: Please authenticate using earthengine authenticate`

**Solution:**
```bash
earthengine authenticate
```
Follow the browser authentication flow.

### DynamoDB Table Already Exists

**Error:** `ResourceInUseException: Table already exists`

**Solution:**
This is expected if tables were created previously. You can:
- Continue with existing tables
- Delete and recreate: `python scripts/create_dynamodb_tables.py --action recreate`

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'streamlit'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -e .[dev]
```

### Port Already in Use

**Error:** `OSError: [Errno 48] Address already in use`

**Solution:**
```bash
# Kill process on port 8501
# macOS/Linux:
lsof -ti:8501 | xargs kill -9

# Windows:
netstat -ano | findstr :8501
taskkill /PID <PID> /F

# Or use a different port
streamlit run app.py --server.port 8502
```

## Next Steps

After completing the setup:

1. **Explore the UI Personas:**
   - Farmer View: Voice-first interaction with ISRO Bhuvan mapping
   - Officer View: Jurisdiction-wide monitoring and alert management
   - Admin View: Simulation controls and system monitoring

2. **Review the Architecture:**
   - Read `design.md` in `.kiro/specs/precision-agriai/`
   - Understand the Service-Based Monolith pattern
   - Review the four core services

3. **Start Development:**
   - Follow the implementation plan in `tasks.md`
   - Begin with Task 1.2: Set up testing framework
   - Implement services incrementally

4. **Test the System:**
   - Run unit tests for each service
   - Execute property-based tests
   - Validate end-to-end workflows

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Google Earth Engine Python API](https://developers.google.com/earth-engine/guides/python_install)
- [ISRO Bhuvan WMS Services](https://bhuvan.nrsc.gov.in/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the design document in `.kiro/specs/precision-agriai/design.md`
3. Consult the requirements document in `.kiro/specs/precision-agriai/requirements.md`

---

**Ready to start?** Run `python scripts/setup_environment.py` to validate your setup!
