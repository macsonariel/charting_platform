# Phase Detection Parameters Guide

## Parameters That Control Leniency & Frequency

### 🎯 **Primary Controls (Most Impact)**

#### 1. `min_phase_confidence` (Default: 0.4)
**What it does:** Minimum score required to detect a phase (0.0 - 1.0)

**To make MORE lenient (phases appear more often):**
- **Decrease** value: `0.3` or `0.2`
- Lower threshold = phases detected with weaker signals

**To make LESS lenient (phases appear less often):**
- **Increase** value: `0.5` or `0.6`
- Higher threshold = only strong phases detected

**Location:** Line 61 in `phase_detection.py`

---

#### 2. `min_phase_candles` (Default: 3)
**What it does:** Minimum number of consecutive confirmations before phase transition

**To make phases appear in SHORTER intervals:**
- **Decrease** value: `2` or `1`
- Lower = phases transition faster, more frequent changes

**To make phases appear in LONGER intervals:**
- **Increase** value: `5` or `10`
- Higher = phases persist longer, fewer transitions

**Location:** Line 60 in `phase_detection.py`, also used at lines 875, 878, 896

---

#### 3. `range_window` (Default: 30)
**What it does:** Number of candles to analyze for range/consolidation detection

**To detect phases in SHORTER intervals:**
- **Decrease** value: `15` or `20`
- Smaller window = detects phases in shorter timeframes

**To detect phases in LONGER intervals:**
- **Increase** value: `50` or `60`
- Larger window = requires longer consolidation periods

**Location:** Line 41 in `phase_detection.py`

---

### 🔧 **Secondary Controls (Moderate Impact)**

#### 4. `effort_result_threshold` (Default: 0.7)
**What it does:** Effort/Result ratio threshold for Accumulation/Distribution detection

**To make MORE lenient:**
- **Decrease** value: `0.5` or `0.4`
- Lower = easier to detect CO activity (Accumulation/Distribution)

**To make LESS lenient:**
- **Increase** value: `0.8` or `0.9`
- Higher = requires stronger Effort/Result divergence

**Location:** Line 46 in `phase_detection.py`, used at lines 409, 549

---

#### 5. `relative_volume_threshold` (Default: 1.2)
**What it does:** Volume ratio threshold (up candles vs down candles)

**To make MORE lenient:**
- **Decrease** value: `1.1` or `1.05`
- Lower = easier to detect volume patterns

**To make LESS lenient:**
- **Increase** value: `1.5` or `2.0`
- Higher = requires stronger volume divergence

**Location:** Line 47 in `phase_detection.py`, used at lines 418, 558

---

#### 6. `breakout_strength` (Default: 0.01 = 1%)
**What it does:** Price move percentage required for breakout/breakdown confirmation

**To make transitions MORE frequent:**
- **Decrease** value: `0.005` (0.5%) or `0.003` (0.3%)
- Lower = easier breakouts, faster Mark-Up/Mark-Down transitions

**To make transitions LESS frequent:**
- **Increase** value: `0.02` (2%) or `0.03` (3%)
- Higher = requires stronger breakouts

**Location:** Line 42 in `phase_detection.py`, used at lines 824, 860

---

### 🎨 **Fine-Tuning Controls (Subtle Impact)**

#### 7. `composite_volume_spike` (Default: 1.5 = 50% above average)
**What it does:** Volume spike threshold for Composite Operator detection

**To make MORE lenient:**
- **Decrease** value: `1.3` or `1.2`
- Lower = easier to detect CO activity

**Location:** Line 56 in `phase_detection.py`

---

#### 8. `composite_effort_divergence` (Default: 0.5)
**What it does:** Effort/Result ratio for CO manipulation detection

**To make MORE lenient:**
- **Decrease** value: `0.3` or `0.4`
- Lower = easier to detect manipulation patterns

**Location:** Line 57 in `phase_detection.py`

---

#### 9. `spring_breakdown_percent` (Default: 0.02 = 2%)
**What it does:** Price drop below range low for Spring detection

**To make MORE lenient:**
- **Decrease** value: `0.01` (1%) or `0.005` (0.5%)
- Lower = easier to detect Springs

**Location:** Line 50 in `phase_detection.py`

---

#### 10. `utad_breakout_percent` (Default: 0.02 = 2%)
**What it does:** Price move above range high for UTAD detection

**To make MORE lenient:**
- **Decrease** value: `0.01` (1%) or `0.005` (0.5%)
- Lower = easier to detect UTADs

**Location:** Line 52 in `phase_detection.py`

---

## 📊 Quick Reference: Making Phases Appear More Frequently

### For **SHORTER intervals** (more frequent phase changes):
```python
min_phase_candles = 1  # or 2 (default: 3)
range_window = 15      # or 20 (default: 30)
```

### For **MORE lenient** detection (phases appear more often):
```python
min_phase_confidence = 0.2  # or 0.3 (default: 0.4)
effort_result_threshold = 0.5  # (default: 0.7)
relative_volume_threshold = 1.1  # (default: 1.2)
breakout_strength = 0.005  # 0.5% (default: 0.01 = 1%)
```

### For **LESS lenient** detection (only strong phases):
```python
min_phase_confidence = 0.6  # or 0.7 (default: 0.4)
effort_result_threshold = 0.9  # (default: 0.7)
relative_volume_threshold = 1.5  # (default: 1.2)
breakout_strength = 0.02  # 2% (default: 0.01 = 1%)
```

---

## 🔄 How to Adjust

### Option 1: Via API Options (Recommended)
When calling the phase detection API, pass options:
```javascript
const phases = await detectMarketPhases(swings, chartData, {
    min_phase_candles: 2,        // Shorter intervals
    min_phase_confidence: 0.3,   // More lenient
    range_window: 20,            // Shorter analysis window
    effort_result_threshold: 0.5 // Easier CO detection
});
```

### Option 2: Modify Defaults in Code
Edit `PhaseConfig` dataclass in `phase_detection.py` (lines 37-64)

---

## 📈 Impact Summary

| Parameter | Lower Value = | Higher Value = |
|-----------|---------------|----------------|
| `min_phase_confidence` | More lenient, more phases | Stricter, fewer phases |
| `min_phase_candles` | Shorter intervals, faster transitions | Longer intervals, slower transitions |
| `range_window` | Shorter analysis, more frequent | Longer analysis, less frequent |
| `effort_result_threshold` | Easier Accumulation/Distribution | Harder Accumulation/Distribution |
| `relative_volume_threshold` | Easier volume-based detection | Harder volume-based detection |
| `breakout_strength` | Easier breakouts, faster transitions | Harder breakouts, slower transitions |


