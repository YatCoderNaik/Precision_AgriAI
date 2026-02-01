# Requirements Document

## Introduction

Precision AgriAI is a **Neuro-Symbolic Generative AI system** designed to solve the "Last Mile" problem in agriculture. Unlike traditional rule-based dashboards that rely on rigid thresholds, this system uses **AWS Bedrock (Claude 3)** to reason over multi-dimensional data (Satellite Math + Visuals + Weather). It acts as an empathetic, automated agronomist that converts raw sensory data into hyper-personalized, voice-first guidance for rural farmers, while providing Extension Officers with jurisdiction-wide sustainability insights and coordinated intervention capabilities.

## Glossary

- **Neuro-Symbolic_AI**: A hybrid architecture where deterministic data (GEE Math) acts as sensory input, and Generative AI (Bedrock) acts as the reasoning brain
- **RAG_Context**: The "Retrieval" layer consisting of live satellite stats, weather forecasts, and soil maps fed into the LLM
- **Multimodal_Analysis**: The AI's ability to process both numerical data (NDVI) and visual data (Sentinel-2 RGB images) simultaneously
- **Proactive_Sentry**: An automated background agent that scans plots daily and pushes alerts only when AI reasoning confirms high urgency
- **System**: The Precision AgriAI neuro-symbolic generative AI system
- **Plot**: A specific rural agricultural land area identified by latitude and longitude coordinates
- **Extension_Officer**: Primary user who provides agricultural guidance, makes intervention decisions, and monitors sustainability metrics for their jurisdiction (Hobli)
- **Farmer**: Primary user who interacts via voice in local dialect
- **Hobli**: Administrative subdivision in Karnataka; the jurisdictional unit for Extension Officers
- **Jurisdiction_Directory**: Mapping system that associates plots with specific Hoblis and Extension Officers
- **Chain-of-Thought**: Prompt strategy that guides AWS Bedrock through structured reasoning steps
- **Contextual_Awareness**: AI's ability to distinguish context-dependent agricultural conditions
- **Visual_Trust**: Multimodal verification using satellite imagery to validate mathematical analysis
- **Deep_Link**: URL that opens the Streamlit app directly to a specific plot's analysis results

## Requirements

### Requirement 1: Plot-Level Input Management

**User Story:** As an extension officer, I want to input plot coordinates for rural agricultural areas, so that I can assess stress conditions for specific locations.

#### Acceptance Criteria

1. WHEN a user provides latitude and longitude coordinates, THE System SHALL validate the coordinates are within supported geographic regions
2. WHEN invalid coordinates are provided, THE System SHALL return a descriptive error message with format requirements
3. WHEN coordinates are outside supported geographic regions, THE System SHALL inform the user of geographic limitations
4. THE System SHALL accept decimal degree format coordinates with at least 4 decimal places precision
5. WHEN coordinates are successfully validated, THE System SHALL proceed to retrieve satellite and environmental data for the location

### Requirement 2: Neuro-Symbolic Data Ingestion

**User Story:** As a farmer, I want the AI to understand my farm using multiple data sources, so that I get comprehensive advice.

#### Acceptance Criteria

1. THE System SHALL retrieve Google Earth Engine analytics (NDVI, weather data) for the specified coordinates
2. THE System SHALL fetch AWS Sentinel-2 RGB imagery from AWS Open Data for visual analysis
3. THE System SHALL compile weather forecasts and soil data as RAG context for the AI
4. THE System SHALL prepare all data sources in a structured format for AWS Bedrock ingestion
5. THE System SHALL complete concurrent data fetching within 6 seconds to meet performance requirements

### Requirement 8: System Performance & Architecture

**User Story:** As a developer, I need a robust system that delivers AI-driven insights quickly.

#### Acceptance Criteria

1. THE System SHALL complete end-to-end analysis (Coordinate -> GenAI Reasoning -> Audio Response) within **8 seconds**
2. THE System SHALL be implemented using **Python 3.10+** (Monolithic Streamlit Architecture) to leverage native geospatial libraries
3. THE System SHALL use **concurrent processing** to fetch Google Earth Engine analytics and AWS Sentinel-2 imagery simultaneously
4. THE System SHALL prioritize mobile responsiveness in the UI layout
5. THE System SHALL maintain deterministic behavior when LLM assistance is disabled
6. WHEN LLM prompts are used, THE System SHALL make prompt content visible for trust and auditability
7. THE System SHALL provide clear attribution for AlphaEarth data usage following CC-BY 4.0 requirements
8. WHEN processing fails at any stage, THE System SHALL provide specific error messages indicating which component failed and why

### Requirement 3: Voice & Multimodal Interaction

**User Story:** As a farmer who cannot type easily, I want to speak to the app in my local language so that I can get advice without using a keyboard.

#### Acceptance Criteria

1. THE System SHALL accept audio input and convert it to text using AWS Transcribe
2. THE System SHALL detect the user's intent (e.g., "Check my crop", "Register plot") using AWS Bedrock
3. THE System SHALL generate spoken audio responses using AWS Polly in the user's detected language
4. THE System SHALL allow users to register a plot by tapping a geolocation on ISRO Bhuvan maps

### Requirement 12: Data Persistence and Extension Officer Dashboard

**User Story:** As an Extension Officer, I want to track and manage all plots and alerts within my jurisdiction, so that I can provide coordinated agricultural support across my assigned Hobli.

#### Acceptance Criteria

1. THE System SHALL persist all user plots and alert data in **Amazon DynamoDB** for durability and scalability
2. THE System SHALL maintain plot registration data including farmer contact information, coordinates, and alert history
3. THE System SHALL provide an Extension Officer dashboard showing all plots within their jurisdiction
4. THE System SHALL store alert metadata including urgency levels, timestamps, and resolution status
5. THE System SHALL support data retrieval and filtering by jurisdiction (Hobli) for Extension Officer access
6. THE System SHALL maintain data consistency across concurrent access by multiple Extension Officers

### Requirement 4: Data Privacy and Security

**User Story:** As an extension officer, I want assurance that farmer data is protected while maintaining necessary operational data for jurisdiction management, so that I can use the system effectively without compromising farmer privacy.

#### Acceptance Criteria

1. THE System SHALL store only essential operational data (plot coordinates, alert history, jurisdiction mapping) in Amazon DynamoDB while avoiding personally identifiable farmer information beyond contact details necessary for alerts
2. THE System SHALL implement secure data transmission for all external API calls and database operations
3. THE System SHALL provide role-based access control ensuring Extension Officers can only access plots within their assigned jurisdiction (Hobli)
4. THE System SHALL maintain data encryption at rest and in transit for all persistent storage
5. THE System SHALL be designed for advisory use and not automate actions without human oversight
6. THE System SHALL implement data retention policies that automatically purge old alert data while maintaining operational history for trend analysis

### Requirement 14: Cognitive Reasoning Engine (GenAI Core)

**User Story:** As a farmer, I need advice that understands context (season, weather, visuals), not just generic rules.

#### Acceptance Criteria

1. THE System SHALL use **AWS Bedrock (Claude 3 Haiku/Sonnet)** as the primary decision-maker, using a "Chain-of-Thought" prompt strategy
2. THE System SHALL ingest **Multimodal Inputs**: Satellite Embeddings (GEE), Weather Forecasts, and Visual Satellite Imagery (AWS S3)
3. THE System SHALL demonstrate **Contextual Awareness** (e.g., distinguishing between 'harvest drying' and 'drought stress' based on season)
4. THE System SHALL generate empathetic, dialect-specific responses via **AWS Polly**, adapting the tone to the urgency of the situation

### Requirement 15: Hybrid Data Verification (Visual Trust)

**User Story:** As a user, I want the AI to "look" at my farm to verify the math.

#### Acceptance Criteria

1. THE System SHALL fetch the latest available cloud-free RGB image from **AWS Open Data (Sentinel-2)**
2. THE System SHALL pass this image to the **Bedrock Multimodal Agent** to detect visible anomalies (clouds, flooding, browning)
3. THE System SHALL flag a "Confidence Warning" if the Visual Input contradicts the Mathematical Input (GEE)

### Requirement 17: Raitha Setu - Government Bridge System

**User Story:** As an Extension Officer, I want to receive real-time validated alerts for my specific jurisdiction (Hobli), so that I can coordinate agricultural interventions effectively across my assigned region.

#### Acceptance Criteria

1. THE System SHALL maintain a **Jurisdiction Directory** that maps individual plots to specific Hoblis and assigns them to Extension Officers
2. THE System SHALL automatically route **"High Urgency"** alerts to the specific Extension Officer's dashboard based on plot location and jurisdiction mapping
3. THE System SHALL aggregate individual plot alerts into a **"Cluster Outbreak"** heatmap showing regional stress patterns within each Hobli
4. THE System SHALL provide Extension Officers with jurisdiction-wide sustainability metrics and intervention recommendations
5. THE System SHALL support real-time alert notifications to Extension Officers via dashboard updates and SMS when multiple plots in their jurisdiction show coordinated stress patterns
6. THE System SHALL maintain audit trails of Extension Officer responses and interventions for government reporting and accountability

### Requirement 16: Proactive Sentry Mode (The "Push" System)

**User Story:** As a farmer, I want to be notified automatically if my crop is in danger, so I don't have to check the app daily.

#### Acceptance Criteria

1. THE System SHALL include a "Daily Scan Simulation" mode that iterates through registered plots
2. THE System SHALL run the full Bedrock Analysis in the background
3. THE System SHALL only trigger an alert if the AI classifies the risk as **"High Urgency"** (filtering out noise)
4. THE System SHALL send an SMS notification via **AWS SNS** with a summary of the AI's diagnosis
5. THE System SHALL provide a "Deep Link" in the SMS that opens the Streamlit app directly to the affected plot