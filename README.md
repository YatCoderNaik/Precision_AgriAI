# Precision AgriAI

**A Service-Based Monolith for AI-Driven Agricultural Monitoring and Intervention Coordination**

Precision AgriAI is a Neuro-Symbolic Generative AI system designed to solve the "Last Mile" problem in agriculture. Unlike traditional rule-based dashboards, this system uses AWS Bedrock (Claude 3) to reason over multi-dimensional data (Satellite Math + Visuals + Weather), acting as an empathetic, automated agronomist that converts raw sensory data into hyper-personalized, voice-first guidance for rural farmers.

## 🌾 Key Features

### 🗺️ **ISRO Bhuvan Integration**
- Native integration with ISRO Bhuvan WMS (LISS III/Vector) for localized Indian mapping
- Hobli-based jurisdiction management for Extension Officers
- GPS location services with privacy controls

### 🧠 **Multimodal AI Analysis**
- **GEEService**: Google Earth Engine integration for NDVI float data
- **SentinelService**: AWS Open Data Sentinel-2 imagery URLs
- **BrainService**: AWS Bedrock multimodal analysis combining numerical and visual data

### 🎤 **Voice-First Farmer Interface**
- AWS Transcribe for speech-to-text in multiple Indian languages (Hindi, Tamil, Telugu, English)
- AWS Polly for text-to-speech with dialect-specific voices
- Intent detection using AWS Bedrock for natural language commands

### 🏛️ **Raitha Setu - Government Bridge**
- Jurisdiction Directory mapping plots to Hoblis and Extension Officers
- Automatic alert routing for "High Urgency" classifications
- Cluster Outbreak heatmaps for coordinated intervention
- SMS notifications via AWS SNS with deep links

### 📊 **Three UI Personas**
1. **Farmer View**: Big Mic Button + ISRO Bhuvan Map + Audio Response Card
2. **Officer View**: Hobli Heatmap + Aggregated Stats + Alert Management
3. **Admin View**: Simulation Controls + System Monitoring

## 🏗️ Architecture

### Service-Based Monolith on AWS
```
Streamlit Monolith Application
├── MapService (ISRO Bhuvan Integration)
├── VoiceService (Transcribe/Polly)
├── BrainService (Multimodal AI)
│   ├── GEEService (NDVI Float Data)
│   ├── SentinelService (Image URLs)
│   └── Bedrock Reasoning (Multimodal Analysis)
└── DbService (DynamoDB Operations)
```

### AWS Infrastructure
- **Compute**: ECS Fargate for containerized deployment
- **Database**: DynamoDB two-table design for plots and alerts
- **AI/ML**: Bedrock, Transcribe, Polly for multimodal reasoning
- **Notifications**: SNS for SMS alerts to farmers and officers
- **Storage**: S3 for audio files and logs
- **CDN**: CloudFront for global content delivery

## 📋 Database Schema

### DynamoDB Two-Table Design

#### Table 1: PrecisionAgri_Plots
```
PK: user_id (String)
SK: plot_id (String)
Attributes: lat, lon, crop, hobli_id, farmer_name, phone_number
GSI-1: hobli_id (PK), registration_date (SK)
```

#### Table 2: PrecisionAgri_Alerts
```
PK: hobli_id (String)
SK: timestamp (String)
Attributes: plot_id, risk_level, message, gee_proof, bedrock_reasoning
GSI-1: risk_level (PK), timestamp (SK)
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- AWS Account with appropriate permissions
- ISRO Bhuvan API access
- Google Earth Engine account

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/YatCoderNaik/Precision_AgriAI.git
cd Precision_AgriAI
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure AWS credentials**
```bash
aws configure
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. **Initialize DynamoDB tables**
```bash
python scripts/setup_dynamodb.py
```

6. **Run the application**
```bash
streamlit run app.py
```

## 🧪 Testing

### Property-Based Testing
The system includes 23 property-based tests that validate universal correctness properties:

```bash
# Run all property-based tests
pytest tests/property/ -v

# Run specific property test
pytest tests/property/test_coordinate_validation.py::test_coordinate_validation_consistency -v
```

### Integration Testing
```bash
# Run service integration tests
pytest tests/integration/ -v

# Run end-to-end tests
pytest tests/e2e/ -v
```

## 📁 Project Structure

```
Precision_AgriAI/
├── .kiro/specs/precision-agriai/    # Specification documents
│   ├── requirements.md             # System requirements
│   ├── design.md                   # Architecture design
│   └── tasks.md                    # Implementation tasks
├── services/                       # Internal services
│   ├── map_service.py              # ISRO Bhuvan integration
│   ├── voice_service.py            # AWS Transcribe/Polly
│   ├── brain_service.py            # Multimodal AI orchestrator
│   │   ├── gee_service.py          # Google Earth Engine
│   │   └── sentinel_service.py     # AWS Sentinel-2 data
│   └── db_service.py               # DynamoDB operations
├── ui/                             # Streamlit UI components
│   ├── farmer_view.py              # Farmer interface
│   ├── officer_view.py             # Extension Officer dashboard
│   └── admin_view.py               # System administration
├── tests/                          # Test suites
│   ├── property/                   # Property-based tests
│   ├── integration/                # Service integration tests
│   └── e2e/                        # End-to-end tests
├── scripts/                        # Deployment and setup scripts
├── docs/                           # Documentation
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Container configuration
└── README.md                       # This file
```

## 🌍 Supported Regions

- **Primary**: India (Karnataka, Tamil Nadu, Telangana, Andhra Pradesh)
- **Languages**: Hindi, Tamil, Telugu, English
- **Mapping**: ISRO Bhuvan WMS coverage areas

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow the Service-Based Monolith architecture
- Write property-based tests for new features
- Ensure AWS service integration follows best practices
- Maintain mobile-responsive UI design

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **ISRO Bhuvan** for providing localized Indian mapping services
- **Google Earth Engine** for satellite analytics and NDVI data
- **AWS Open Data** for Sentinel-2 imagery access
- **Indian Agricultural Extension Services** for domain expertise

## 📞 Support

For support and questions:
- Create an issue in this repository
- Contact the development team
- Check the [documentation](docs/) for detailed guides

## 🎯 Roadmap

- [ ] **Phase 1**: Core Service-Based Monolith (Q1 2024)
- [ ] **Phase 2**: Multimodal AI Integration (Q2 2024)
- [ ] **Phase 3**: Government Bridge & Voice Interface (Q3 2024)
- [ ] **Phase 4**: Multi-state Expansion (Q4 2024)

---

**Built with ❤️ for Indian Agriculture**

*Empowering farmers with AI-driven insights while supporting Extension Officers with jurisdiction-wide coordination capabilities.*