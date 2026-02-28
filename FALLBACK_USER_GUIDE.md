# User Guide: Understanding Limited Analysis Mode

## What is Limited Analysis Mode?

When you analyze a plot, Precision AgriAI normally uses two data sources:
1. **NDVI data** from Google Earth Engine (vegetation health index)
2. **Satellite imagery** from Sentinel-2 (visual verification)

Sometimes, recent satellite imagery isn't available for your location. When this happens, the system automatically switches to **Limited Analysis Mode**, using only NDVI data.

## How Will I Know If I'm in Limited Analysis Mode?

You'll see **multiple clear indicators**:

### 1. Toast Notification (Top-Right Corner)
```
⚠️ Analysis completed using NDVI data only (satellite imagery unavailable)
```
This appears immediately after analysis completes and stays visible for 5 seconds.

### 2. Warning Message (Below Analyze Button)
```
⚠️ Analysis completed in 6.5s (Limited mode: Satellite imagery unavailable)
```
This replaces the normal green success message with a yellow warning.

### 3. Prominent Banner (Top of Results)
```
🚨 IMPORTANT: Limited Analysis Mode Active

Satellite imagery is currently unavailable for this location.
Analysis is based on NDVI (vegetation index) data only.

Reason: No Sentinel-2 imagery found for coordinates within 30 days

Impact:
- ✅ NDVI health assessment is still accurate
- ⚠️ Visual satellite verification unavailable  
- ℹ️ Confidence scores may be slightly lower

This is normal for some locations and time periods. 
The NDVI-based analysis remains reliable for crop health monitoring.
```
This large red banner provides detailed information about what happened and why.

### 4. Pipeline Status
In the "Pipeline Status" section, you'll see:
- **AI Analysis**: ⚠️ Partial (instead of ✅ Complete)

### 5. Confidence Label
The confidence metric will show:
- **Confidence**: 75% (NDVI-only)

The "(NDVI-only)" suffix indicates limited mode.

## Why Does This Happen?

Limited Analysis Mode occurs when:

1. **Recent imagery not available**: Sentinel-2 satellites haven't captured your location recently
2. **Cloud cover**: All recent satellite passes had too much cloud cover
3. **Coverage gaps**: Your location is temporarily outside the satellite coverage area
4. **Data processing delays**: Recent imagery hasn't been processed yet

This is **completely normal** and happens for many locations, especially:
- Remote areas
- Regions with frequent cloud cover
- During monsoon season
- For very recent time periods

## Is the Analysis Still Reliable?

**YES!** The NDVI-based analysis is still highly reliable:

✅ **NDVI is accurate**: The vegetation health index is calculated from satellite data and is very reliable

✅ **Risk classification works**: The system uses proven NDVI thresholds to classify crop health

✅ **Recommendations are valid**: The guidance provided is based on solid agricultural science

⚠️ **What's missing**: Visual verification from high-resolution imagery

The main difference is that we can't show you the actual satellite image or perform visual analysis. However, the NDVI data alone is sufficient for crop health monitoring.

## What Should I Do?

### If Risk is Low or Medium
- **Continue normal monitoring**: The NDVI assessment is reliable
- **Follow recommendations**: The guidance provided is still valid
- **No immediate action needed**: Your crop is doing fine

### If Risk is High or Critical
- **Take action immediately**: The NDVI data clearly shows stress
- **Inspect your field**: Visual inspection is recommended
- **Follow recommendations**: Check irrigation, look for pests, etc.
- **Contact extension officer**: If you need assistance

The lack of satellite imagery doesn't change the urgency of high-risk situations.

## Confidence Scores Explained

| Mode | Typical Confidence | Meaning |
|------|-------------------|---------|
| **Full Multimodal** | 90-95% | NDVI + Visual verification |
| **Limited (NDVI-only)** | 70-85% | NDVI only, no visual verification |

The confidence is slightly lower in Limited Mode because we're using one data source instead of two. However, 70-85% confidence is still very good for agricultural monitoring.

## Technical Details (For Advanced Users)

If you expand the "Technical Details" section, you'll see:

```json
{
  "fallback_mode": true,
  "tile_id": "unavailable",
  "image_url": "",
  "error": "No Sentinel-2 imagery found for coordinates within 30 days"
}
```

This confirms the system is in fallback mode and shows the specific reason.

## Frequently Asked Questions

### Q: Will imagery be available later?
**A**: Possibly. Sentinel-2 satellites revisit each location every 5-10 days. Try analyzing again in a few days.

### Q: Can I trust the NDVI-only analysis?
**A**: Yes! NDVI is a proven metric used worldwide for crop monitoring. It's the foundation of precision agriculture.

### Q: Should I wait for imagery before taking action?
**A**: No! If the analysis shows high or critical risk, take action immediately. Don't wait for imagery.

### Q: Why don't you use older imagery?
**A**: We want to give you the most current assessment. Older imagery might not reflect current conditions.

### Q: Can I request imagery for my location?
**A**: Satellite coverage is automatic and global. We can't request specific imagery, but coverage is generally good.

### Q: Will this affect my plot registration?
**A**: No! Plot registration and alert creation work normally in Limited Mode.

## Example Scenarios

### Scenario 1: Healthy Crop in Limited Mode
```
⚠️ Limited Analysis Mode Active

🟢 LOW RISK
NDVI: 0.72
Confidence: 85% (NDVI-only)

💡 Good news! Your crop is healthy. Keep up your current farming practices.
```
**Action**: Continue normal monitoring. No concerns.

### Scenario 2: Stressed Crop in Limited Mode
```
⚠️ Limited Analysis Mode Active

🟠 HIGH RISK
NDVI: 0.28
Confidence: 75% (NDVI-only)

💡 IMPORTANT: Your crop shows signs of stress. Check irrigation and look for pest damage within 2-3 days.
```
**Action**: Inspect field immediately. The NDVI data clearly shows stress, even without imagery.

## Summary

- ✅ Limited Analysis Mode is **normal and expected** for some locations
- ✅ NDVI-based analysis is **still reliable** for crop health monitoring
- ✅ You'll see **multiple clear warnings** so you're always informed
- ✅ **Take action** based on risk level, regardless of mode
- ✅ Confidence is slightly lower but **still very good** (70-85%)

**Bottom line**: Trust the analysis, follow the recommendations, and don't worry about the lack of imagery. The NDVI data tells us what we need to know about your crop's health.

---

**Need Help?**
- Contact your extension officer
- Check the Technical Details section for more information
- Try analyzing again in a few days for updated imagery

**Questions?**
- Email: support@precisionagriai.example.com
- Phone: +91 1800-XXX-XXXX
