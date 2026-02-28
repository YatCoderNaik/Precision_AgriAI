# BrainService Demo

## Overview

The BrainService is the multimodal AI orchestration layer that combines:
- **GEEService**: NDVI data from Google Earth Engine (MODIS/061/MOD13Q1)
- **SentinelService**: Satellite imagery from AWS Open Data Sentinel-2
- **AWS Bedrock**: Claude 3 Sonnet for multimodal reasoning

## Running the Demo

```bash
conda activate agriai
python examples/brain_service_demo.py
```

## Demo Features

### 1. Multimodal Plot Analysis
Combines NDVI numerical data with satellite imagery for comprehensive agricultural analysis:
- Concurrent data fetching (< 6 seconds)
- Risk classification (critical/high/medium/low)
- Farmer-friendly guidance generation
- Confidence scoring

### 2. Cluster Outbreak Detection
Analyzes multiple plots within a jurisdiction to detect regional stress patterns:
- Minimum 3 plots required
- Average NDVI calculation
- Severity assessment (critical/high/medium/low)
- Coordinated intervention recommendations

## Demo Results

### Test Run (February 27, 2026)

**Location**: Bangalore (12.9716, 77.5946)

**Services Initialized**:
- ✅ BrainService with GEE (real mode, not mock)
- ✅ SentinelService (AWS S3 integration)
- ✅ GEEService (Google Earth Engine integration)

**Multimodal Analysis**:
- ⚠️ Sentinel-2 imagery not available for location (no recent imagery within 30 days)
- Note: This is expected for some locations/timeframes
- Production systems should implement fallback logic or use cached imagery

**Cluster Detection** (✅ Success):
```
Cluster Detected: True
Affected Plots: 3
Average NDVI: 0.183
Severity: critical
Recommended Action: immediate_intervention
```

## Architecture

### Concurrent Processing
```
┌─────────────┐
│ BrainService│
└──────┬──────┘
       │
       ├──────────────┬──────────────┐
       │              │              │
       v              v              v
┌──────────┐   ┌──────────┐   ┌──────────┐
│   GEE    │   │ Sentinel │   │ Bedrock  │
│  Service │   │ Service  │   │  Claude  │
└──────────┘   └──────────┘   └──────────┘
    NDVI          Imagery       Reasoning
```

### Risk Classification Thresholds
- **Critical**: NDVI < 0.2
- **High**: NDVI 0.2-0.4
- **Medium**: NDVI 0.4-0.6
- **Low**: NDVI > 0.6

### Cluster Outbreak Criteria
- Minimum 3 plots in jurisdiction
- Average NDVI < 0.3 OR 50%+ high-risk plots
- Severity based on average NDVI and high-risk percentage

## Implementation Notes

### GEE Integration
- Uses MODIS/061/MOD13Q1 for NDVI data
- NDVI scaling: raw_value * 0.0001
- Automatic fallback to mock data when GEE unavailable
- Deterministic mock data using coordinate hashing

### Sentinel Integration
- AWS Open Data Sentinel-2 L2A bucket
- MGRS tile ID conversion from coordinates
- Presigned URL generation for secure image access
- 30-day lookback window for imagery

### Bedrock Integration
- Claude 3 Sonnet for multimodal analysis
- Claude 3 Haiku for farmer guidance (faster, cost-effective)
- Chain-of-Thought prompting for agricultural reasoning
- Fallback to rule-based classification when Bedrock unavailable

## Testing

### Unit Tests
- 26 GEEService tests (81% coverage)
- 26 SentinelService tests (96% coverage)
- 22 BrainService tests (76% coverage)

### Property-Based Tests
- Property 21: Visual Verification Consistency
- Property 22: Concurrent Processing Performance

All tests passing ✅

## Next Steps

1. Implement Sentinel fallback logic for missing imagery
2. Add caching layer for repeated requests
3. Integrate with VoiceService for audio guidance
4. Connect to DbService for alert storage
5. Add Streamlit UI integration

## References

- POC Implementation: `Precision_AgriAI_POC/poc_recommender.py`
- GEE Documentation: https://developers.google.com/earth-engine
- Sentinel-2 AWS: https://registry.opendata.aws/sentinel-2/
- AWS Bedrock: https://aws.amazon.com/bedrock/
