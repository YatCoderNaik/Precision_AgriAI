# Fallback Handling Flow Diagram

## Complete User Flow with Fallback

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INITIATES ANALYSIS                       │
│                  (Clicks "Analyze Plot Health")                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SERVICEINTEGRATION                             │
│              analyze_and_store_plot()                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MAPSERVICE                                  │
│              validate_coordinates()                              │
│                                                                  │
│  ✅ Coordinates Valid                                            │
│  ✅ Jurisdiction Identified                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BRAINSERVICE                                 │
│                 analyze_plot()                                   │
│                                                                  │
│  Concurrent Data Fetching:                                       │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │   GEEService     │  │ SentinelService  │                    │
│  │  get_ndvi()      │  │  get_image()     │                    │
│  └────────┬─────────┘  └────────┬─────────┘                    │
│           │                      │                               │
│           ▼                      ▼                               │
│      ✅ SUCCESS              ❌ FAILURE                          │
│      NDVI: 0.275            No imagery found                     │
│                                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────┴────────┐
                    │  Sentinel OK?   │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
        ┌───────────────┐       ┌───────────────────┐
        │  YES - NORMAL │       │  NO - FALLBACK    │
        │     MODE      │       │      MODE         │
        └───────┬───────┘       └───────┬───────────┘
                │                       │
                ▼                       ▼
    ┌───────────────────────┐  ┌──────────────────────────┐
    │ Multimodal Analysis   │  │ NDVI-Only Analysis       │
    │ - NDVI + Image        │  │ - NDVI thresholds        │
    │ - Bedrock reasoning   │  │ - Rule-based             │
    │ - Visual verification │  │ - No visual verification │
    │ - Confidence: 90%+    │  │ - Confidence: 70-85%     │
    │                       │  │                          │
    │ Create SentinelData:  │  │ Create Mock SentinelData:│
    │ - image_url: <url>    │  │ - image_url: ""          │
    │ - tile_id: "43PPGP"   │  │ - tile_id: "unavailable" │
    │ - fallback_mode: false│  │ - fallback_mode: TRUE    │
    │                       │  │ - error: <reason>        │
    └───────┬───────────────┘  └──────────┬───────────────┘
            │                             │
            └──────────┬──────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   Return AnalysisResult      │
        │   - gee_data                 │
        │   - sentinel_data            │
        │   - bedrock_reasoning        │
        │   - risk_level               │
        │   - confidence               │
        └──────────────┬───────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DBSERVICE                                   │
│                                                                  │
│  ✅ Register Plot (if new)                                       │
│  ✅ Create Alert (if high/critical risk)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RETURN TO FRONTEND                              │
│                                                                  │
│  result = {                                                      │
│    'success': True,                                              │
│    'analysis': AnalysisResult,                                   │
│    'response_time': 6.5s,                                        │
│    ...                                                           │
│  }                                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────┴────────┐
                    │  Fallback Mode? │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
        ┌───────────────┐       ┌───────────────────────────┐
        │  NO - NORMAL  │       │  YES - FALLBACK           │
        └───────┬───────┘       └───────┬───────────────────┘
                │                       │
                ▼                       ▼
    ┌───────────────────────┐  ┌──────────────────────────────────┐
    │ DISPLAY NORMAL        │  │ DISPLAY FALLBACK WARNINGS        │
    │                       │  │                                  │
    │ 1. Success message    │  │ 1. 🔔 Toast Notification         │
    │    ✅ Analysis        │  │    ⚠️ NDVI data only             │
    │    completed in 8s    │  │                                  │
    │                       │  │ 2. ⚠️ Warning Message            │
    │ 2. Pipeline Status    │  │    Limited mode active           │
    │    ✅ Complete        │  │                                  │
    │                       │  │ 3. 🚨 Error Banner               │
    │ 3. Results Display    │  │    IMPORTANT: Limited Mode       │
    │    🟢 LOW RISK        │  │    Imagery unavailable           │
    │    NDVI: 0.72         │  │    Reason: No imagery found      │
    │    Confidence: 92%    │  │    Impact: NDVI still accurate   │
    │                       │  │                                  │
    │ 4. Guidance           │  │ 4. Pipeline Status               │
    │    Keep up current    │  │    ⚠️ Partial                    │
    │    practices          │  │                                  │
    │                       │  │ 5. Results Display               │
    │                       │  │    🟠 HIGH RISK                  │
    │                       │  │    NDVI: 0.28                    │
    │                       │  │    Confidence: 75% (NDVI-only)   │
    │                       │  │                                  │
    │                       │  │ 6. Guidance                      │
    │                       │  │    Check irrigation immediately  │
    │                       │  │                                  │
    │                       │  │ 7. 💻 Console Logging            │
    │                       │  │    WARNING: Fallback detected    │
    │                       │  │    Reason: <error message>       │
    └───────────────────────┘  └──────────────────────────────────┘
```

## Fallback Detection Logic (Frontend)

```python
# Multiple checks for robustness
is_fallback = False

# Check 1: metadata flag
if analysis.sentinel_data.metadata.get('fallback_mode'):
    is_fallback = True
    
# Check 2: tile_id
if analysis.sentinel_data.tile_id == "unavailable":
    is_fallback = True
    
# Check 3: empty image_url
if not analysis.sentinel_data.image_url:
    is_fallback = True
```

## User Touchpoints Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER SEES (Fallback Mode)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 🔔 TOAST (Top-Right, 5 seconds)                             │
│     ⚠️ Analysis completed using NDVI data only                  │
│                                                                  │
│  2. ⚠️ WARNING MESSAGE (Below button)                           │
│     Analysis completed in 6.5s (Limited mode)                   │
│                                                                  │
│  3. 🚨 ERROR BANNER (Top of results)                            │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ IMPORTANT: Limited Analysis Mode Active             │    │
│     │ Satellite imagery unavailable                       │    │
│     │ Analysis based on NDVI only                         │    │
│     │                                                      │    │
│     │ Reason: No imagery found within 30 days             │    │
│     │                                                      │    │
│     │ Impact:                                              │    │
│     │ ✅ NDVI assessment still accurate                    │    │
│     │ ⚠️ Visual verification unavailable                   │    │
│     │ ℹ️ Confidence may be slightly lower                  │    │
│     └─────────────────────────────────────────────────────┘    │
│                                                                  │
│  4. 📊 PIPELINE STATUS                                          │
│     AI Analysis: ⚠️ Partial                                     │
│                                                                  │
│  5. 📈 RESULTS                                                  │
│     🟠 HIGH RISK                                                │
│     NDVI: 0.28                                                  │
│     Confidence: 75% (NDVI-only) ← Suffix added                 │
│                                                                  │
│  6. 📋 TECHNICAL DETAILS (Expandable)                           │
│     {                                                            │
│       "fallback_mode": true,                                    │
│       "tile_id": "unavailable",                                 │
│       "image_url": "",                                          │
│       "error": "No imagery found..."                            │
│     }                                                            │
│                                                                  │
│  7. 💻 CONSOLE (Developer view)                                 │
│     WARNING: Fallback mode detected                             │
│     WARNING: Displaying warning to user                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Decision Tree

```
                    Start Analysis
                         │
                         ▼
                 Fetch GEE + Sentinel
                         │
                         ▼
                  ┌──────┴──────┐
                  │             │
            GEE Success?    Sentinel Success?
                  │             │
            ┌─────┴─────┐       │
            │           │       │
           YES         NO       │
            │           │       │
            │           └───────┼──────► FAIL
            │                   │        (No analysis)
            │              ┌────┴────┐
            │              │         │
            │             YES       NO
            │              │         │
            │              ▼         ▼
            │         MULTIMODAL  FALLBACK
            │           MODE       MODE
            │              │         │
            └──────────────┴─────────┘
                         │
                         ▼
                  Store Results
                         │
                         ▼
                  Display to User
                         │
                         ▼
                  ┌──────┴──────┐
                  │             │
            Fallback Mode?      │
                  │             │
            ┌─────┴─────┐       │
            │           │       │
           YES         NO       │
            │           │       │
            ▼           ▼       │
    Show 7 Warnings  Show Normal
    (Multi-touchpoint) (Success)
```

## Performance Comparison

```
NORMAL MODE (Multimodal)
├─ GEE Fetch: 2-3s
├─ Sentinel Fetch: 3-4s (concurrent)
├─ Bedrock Analysis: 2-3s
└─ Total: 8-12s
   Confidence: 90-95%

FALLBACK MODE (NDVI-only)
├─ GEE Fetch: 2-3s
├─ Sentinel Fetch: 3-4s (fails, concurrent)
├─ Rule-based Analysis: <1s
└─ Total: 4-6s ⚡ FASTER
   Confidence: 70-85%
```

## Key Takeaways

1. **Fallback is Automatic**: System detects Sentinel failure and switches modes
2. **User is Informed**: 7 different touchpoints ensure clarity
3. **Analysis Continues**: NDVI-only analysis is still reliable
4. **Performance Improves**: Fallback mode is actually faster
5. **Trust is Maintained**: Clear communication builds confidence

---

**Visual Guide**: This diagram shows the complete flow from user action to final display, highlighting where fallback detection occurs and how users are informed.
