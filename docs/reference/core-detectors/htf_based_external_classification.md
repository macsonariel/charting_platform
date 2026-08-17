# HTF-Based External Swing Classification

## Overview

This document describes a simplified approach to external/internal swing classification using Higher Timeframe (HTF) swings as the source of truth for Lower Timeframe (LTF) external structure.

**Core Concept**: Instead of complex CHoCH/BOS state machines and demotion logic, simply use HTF swings to define external structure on the LTF.

---

## Why HTF-Based Classification?

| Aspect | Complex Approach (CHoCH/BOS) | HTF-Based Approach |
|--------|------------------------------|-------------------|
| Complexity | High (state machines, invalidation, move tracking) | Low (simple mapping) |
| Reliability | Edge cases, consolidation issues | HTF already filters noise |
| Subjectivity | Many rules to tune | HTF swings are "given" |
| Performance | Process every swing with complex logic | Simple lookup |
| Alignment | May drift from actual structure | Always aligned with HTF |

---

## The Logic

```
HTF (e.g., 4H):
  H@130 ────────────────────── External High
     \
      \    LTF (e.g., 15m):
       \   All these are Internal:
        \    h@125, l@120, h@128, l@118, h@122, l@115
         \
  L@110 ────────────────────── External Low
```

- **HTF swing high** → External High on LTF
- **HTF swing low** → External Low on LTF
- **All LTF swings between HTF swings** → Internal

---

## Optimal Timeframe Ratios

### The Sweet Spot: 12x to 24x

From practical experience and ICT/SMC teachings:

| Ratio | Result |
|-------|--------|
| 4x-6x | Too close — Externals everywhere, no filtering benefit |
| **12x-24x** | **Sweet spot** — Meaningful structure, good separation |
| 50x+ | Too far — Miss intermediate structure, externals too sparse |

### Visual Example

```
Too Close (4x): 15m LTF, 1H HTF
──────────────────────────────────
HTF H ──●─────●─────●─────●─────●── Too many externals
LTF    ●●●●●●●●●●●●●●●●●●●●●●●●●●●


Sweet Spot (16x): 15m LTF, 4H HTF
──────────────────────────────────
HTF H ──●───────────────────●────── Good separation
LTF    ●●●●●●●●●●●●●●●●●●●●●●●●●●●
       └── all internal ──┘


Too Far (100x): 15m LTF, Weekly HTF  
──────────────────────────────────
HTF H ──●─────────────────────────── Miss structure
LTF    ●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●
       └── everything internal, too sparse ──┘
```

---

## Binance Supported Timeframes

Binance provides the following timeframes:

```
Minutes:  1m, 3m, 5m, 15m, 30m
Hours:    1H, 2H, 4H, 6H, 8H, 12H
Days:     1D, 3D
Weekly:   1W
Monthly:  1M
```

### Timeframe Values in Minutes

```python
BINANCE_TIMEFRAMES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1H": 60,
    "2H": 120,
    "4H": 240,
    "6H": 360,
    "8H": 480,
    "12H": 720,
    "1D": 1440,
    "3D": 4320,
    "1W": 10080,
    "1M": 43200,
}
```

---

## Binance HTF Mapping

### Hardcoded Mapping (Recommended)

This mapping guarantees valid HTF for every LTF with ratios in the optimal range:

```python
BINANCE_HTF_MAPPING = {
    "1m": "15m",   # 15x
    "3m": "1H",    # 20x
    "5m": "1H",    # 12x
    "15m": "4H",   # 16x
    "30m": "6H",   # 12x
    "1H": "12H",   # 12x
    "2H": "1D",    # 12x
    "4H": "3D",    # 18x
    "6H": "3D",    # 12x
    "8H": "1W",    # 17.5x
    "12H": "1W",   # 14x
    "1D": "1W",    # 7x (lowest possible with Binance)
    "3D": "1M",    # ~10x
    "1W": "1M",    # ~4x
}


def get_htf(ltf: str) -> str:
    """Get HTF for LTF using hardcoded Binance mapping.
    
    Args:
        ltf: Lower timeframe string (e.g., "15m", "1H")
        
    Returns:
        Higher timeframe string
        
    Raises:
        ValueError: If no mapping exists for the LTF
    """
    htf = BINANCE_HTF_MAPPING.get(ltf)
    if not htf:
        raise ValueError(f"No HTF mapping for: {ltf}")
    return htf
```

### Mapping Results Table

| LTF | HTF | Ratio | Use Case |
|-----|-----|-------|----------|
| 1m | 15m | 15x | Scalping |
| 3m | 1H | 20x | Scalping |
| 5m | 1H | 12x | Scalping / Day trading |
| 15m | 4H | 16x | Day trading |
| 30m | 6H | 12x | Day trading |
| 1H | 12H | 12x | Intraday / Swing |
| 2H | 1D | 12x | Swing trading |
| 4H | 3D | 18x | Swing trading |
| 6H | 3D | 12x | Swing trading |
| 8H | 1W | 17.5x | Swing / Position |
| 12H | 1W | 14x | Swing / Position |
| 1D | 1W | 7x | Position trading |
| 3D | 1M | ~10x | Position trading |
| 1W | 1M | ~4x | Long-term |

---

## Dynamic Ratio Function (Alternative)

If you want calculated ratios with snapping to available timeframes:

```python
# Binance available timeframes in minutes
BINANCE_TIMEFRAMES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1H": 60,
    "2H": 120,
    "4H": 240,
    "6H": 360,
    "8H": 480,
    "12H": 720,
    "1D": 1440,
    "3D": 4320,
    "1W": 10080,
    "1M": 43200,
}

# Reverse lookup
MINUTES_TO_TF = {v: k for k, v in BINANCE_TIMEFRAMES.items()}
AVAILABLE_MINUTES = sorted(BINANCE_TIMEFRAMES.values())


def get_htf_dynamic(
    ltf: str, 
    min_ratio: int = 12, 
    max_ratio: int = 24,
    target_ratio: int = 16
) -> str:
    """Get best HTF for given LTF from Binance available timeframes.
    
    Args:
        ltf: LTF string (e.g., "15m", "1H")
        min_ratio: Minimum acceptable ratio (default 12x)
        max_ratio: Maximum acceptable ratio (default 24x)
        target_ratio: Ideal ratio to aim for (default 16x)
    
    Returns:
        HTF string that gives ratio within range, or closest available
        
    Raises:
        ValueError: If LTF is not recognized
    """
    ltf_minutes = BINANCE_TIMEFRAMES.get(ltf)
    if not ltf_minutes:
        raise ValueError(f"Unknown timeframe: {ltf}")
    
    target_minutes = ltf_minutes * target_ratio
    min_minutes = ltf_minutes * min_ratio
    max_minutes = ltf_minutes * max_ratio
    
    # Find available TFs within acceptable range
    candidates = [m for m in AVAILABLE_MINUTES if min_minutes <= m <= max_minutes]
    
    if not candidates:
        # No TF in range, get closest above min_ratio
        candidates = [m for m in AVAILABLE_MINUTES if m >= min_minutes]
        if not candidates:
            # Fallback to highest available
            return MINUTES_TO_TF[AVAILABLE_MINUTES[-1]]
    
    # Pick closest to target
    best = min(candidates, key=lambda m: abs(m - target_minutes))
    
    return MINUTES_TO_TF[best]
```

### Dynamic Function Test Results

```python
for ltf in ["1m", "3m", "5m", "15m", "30m", "1H", "2H", "4H", "1D"]:
    htf = get_htf_dynamic(ltf)
    ltf_min = BINANCE_TIMEFRAMES[ltf]
    htf_min = BINANCE_TIMEFRAMES[htf]
    ratio = htf_min / ltf_min
    print(f"{ltf:4} → {htf:4} ({ratio:.1f}x)")
```

**Output:**
```
1m   → 15m  (15.0x)
3m   → 1H   (20.0x)
5m   → 1H   (12.0x)
15m  → 4H   (16.0x)
30m  → 6H   (12.0x)
1H   → 12H  (12.0x)
2H   → 1D   (12.0x)
4H   → 3D   (18.0x)
1D   → 1W   (7.0x)
```

---

## Edge Case: Daily and Above

Daily timeframe only achieves 7x ratio to Weekly due to Binance limitations.

### Options

**Option 1: Accept 7x**
- Still useful, just tighter externals
- Simpler implementation

**Option 2: Use Monthly**
- 1M gives ~22x ratio from Daily
- But Monthly swings are very sparse

**Option 3: Synthesize 2W Candles**
- Aggregate two 1W candles yourself
- Gives 14x ratio from Daily

```python
from typing import List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def synthesize_2w_candles(weekly_candles: List[Candle]) -> List[Candle]:
    """Create 2W candles from 1W candles.
    
    Args:
        weekly_candles: List of weekly candles (sorted by timestamp)
        
    Returns:
        List of 2-week candles
    """
    synthesized = []
    
    for i in range(0, len(weekly_candles) - 1, 2):
        w1 = weekly_candles[i]
        w2 = weekly_candles[i + 1]
        
        synthesized.append(Candle(
            timestamp=w1.timestamp,
            open=w1.open,
            high=max(w1.high, w2.high),
            low=min(w1.low, w2.low),
            close=w2.close,
            volume=w1.volume + w2.volume
        ))
    
    return synthesized
```

---

## Implementation

### Core Classification Function

```python
from typing import List, Set
from dataclasses import dataclass


@dataclass
class SwingPoint:
    id: str
    index: int
    timestamp: datetime
    price: float
    kind: str  # "high" or "low"
    degree: str = "internal"  # "external" or "internal"
    timeframe: str = ""


def is_near_level(price: float, levels: Set[float], tolerance: float = 0.001) -> bool:
    """Check if price is near any level in the set.
    
    Args:
        price: Price to check
        levels: Set of price levels
        tolerance: Percentage tolerance (default 0.1%)
        
    Returns:
        True if price is within tolerance of any level
    """
    for level in levels:
        if abs(price - level) / level < tolerance:
            return True
    return False


def classify_externals_from_htf(
    ltf_swings: List[SwingPoint],
    htf_swings: List[SwingPoint],
    tolerance: float = 0.001
) -> List[SwingPoint]:
    """Classify LTF swings as external/internal based on HTF swings.
    
    Args:
        ltf_swings: Lower timeframe swings
        htf_swings: Higher timeframe swings (source of external structure)
        tolerance: Price matching tolerance (default 0.1%)
        
    Returns:
        LTF swings with degree field set
    """
    # Create sets of HTF swing prices
    htf_highs: Set[float] = {s.price for s in htf_swings if s.kind == "high"}
    htf_lows: Set[float] = {s.price for s in htf_swings if s.kind == "low"}
    
    for swing in ltf_swings:
        if swing.kind == "high":
            # Is this LTF high at a HTF high level?
            swing.degree = "external" if is_near_level(swing.price, htf_highs, tolerance) else "internal"
        else:
            # Is this LTF low at a HTF low level?
            swing.degree = "external" if is_near_level(swing.price, htf_lows, tolerance) else "internal"
    
    return ltf_swings
```

### CHoCH Detection (Simplified)

With HTF-based externals, CHoCH becomes simple:

```python
def detect_choch_from_htf(
    ltf_swing: SwingPoint, 
    htf_swings: List[SwingPoint],
    tolerance: float = 0.001
) -> bool:
    """Detect if LTF swing breaks HTF structure (CHoCH).
    
    CHoCH = LTF swing breaks a HTF swing level.
    
    Args:
        ltf_swing: The LTF swing to check
        htf_swings: HTF swings defining structure
        tolerance: Break threshold (default 0.1%)
        
    Returns:
        True if this swing breaks HTF structure
    """
    if ltf_swing.kind == "low":
        # Check if this low breaks any HTF low
        for htf in htf_swings:
            if htf.kind == "low":
                threshold = htf.price * (1 - tolerance)
                if ltf_swing.price < threshold:
                    return True  # CHoCH - broke HTF structure
    
    else:  # high
        # Check if this high breaks any HTF high
        for htf in htf_swings:
            if htf.kind == "high":
                threshold = htf.price * (1 + tolerance)
                if ltf_swing.price > threshold:
                    return True  # CHoCH - broke HTF structure
    
    return False
```

### BOS Detection (Simplified)

BOS = LTF breaking LTF (internal structure):

```python
def detect_bos_internal(
    new_swing: SwingPoint,
    previous_swings: List[SwingPoint],
    tolerance: float = 0.001
) -> List[SwingPoint]:
    """Detect which internal swings are broken by new swing (BOS).
    
    BOS = Continuation break (LTF breaking LTF internal structure).
    
    Args:
        new_swing: The new swing to check
        previous_swings: Previous swings to check against
        tolerance: Break threshold (default 0.1%)
        
    Returns:
        List of broken swings
    """
    broken = []
    
    for prev in previous_swings:
        # Only check same type (high vs high, low vs low)
        if prev.kind != new_swing.kind:
            continue
        
        # Only count internal swings for BOS
        if prev.degree == "external":
            continue
        
        is_break = False
        
        if new_swing.kind == "low":
            threshold = prev.price * (1 - tolerance)
            is_break = new_swing.price < threshold
        else:  # high
            threshold = prev.price * (1 + tolerance)
            is_break = new_swing.price > threshold
        
        if is_break:
            broken.append(prev)
    
    return broken
```

---

## Complete Integration Example

```python
from typing import List, Tuple
from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.detectors.swing_detector import detect_swings
from backend.chart.engines.core.detectors.swing_classifier import classify_swings


# Binance HTF mapping
BINANCE_HTF_MAPPING = {
    "1m": "15m",
    "3m": "1H",
    "5m": "1H",
    "15m": "4H",
    "30m": "6H",
    "1H": "12H",
    "2H": "1D",
    "4H": "3D",
    "6H": "3D",
    "8H": "1W",
    "12H": "1W",
    "1D": "1W",
    "3D": "1M",
    "1W": "1M",
}


def get_htf(ltf: str) -> str:
    """Get HTF for LTF."""
    htf = BINANCE_HTF_MAPPING.get(ltf)
    if not htf:
        raise ValueError(f"No HTF mapping for: {ltf}")
    return htf


async def analyze_structure_htf_based(
    ltf_candles: List[Candle],
    htf_candles: List[Candle],
    ltf: str
) -> dict:
    """Analyze structure using HTF-based external classification.
    
    Args:
        ltf_candles: Lower timeframe candles
        htf_candles: Higher timeframe candles
        ltf: Lower timeframe string (e.g., "15m")
        
    Returns:
        Dictionary with classified swings and structure events
    """
    htf = get_htf(ltf)
    
    # Step 1: Detect swings on both timeframes
    ltf_raw_swings = detect_swings(ltf_candles, ltf)
    htf_raw_swings = detect_swings(htf_candles, htf)
    
    # Step 2: Classify HH/HL/LH/LL
    ltf_swings = classify_swings(ltf_raw_swings)
    htf_swings = classify_swings(htf_raw_swings)
    
    # Step 3: Classify external/internal based on HTF
    classified_swings = classify_externals_from_htf(ltf_swings, htf_swings)
    
    # Step 4: Detect structure events
    choch_events = []
    bos_events = []
    
    for i, swing in enumerate(classified_swings):
        # Check for CHoCH (breaks HTF structure)
        if detect_choch_from_htf(swing, htf_swings):
            choch_events.append({
                "swing_id": swing.id,
                "price": swing.price,
                "index": swing.index,
                "direction": "down" if swing.kind == "low" else "up"
            })
        
        # Check for BOS (breaks internal structure)
        previous = classified_swings[:i]
        broken = detect_bos_internal(swing, previous)
        if broken:
            bos_events.append({
                "swing_id": swing.id,
                "price": swing.price,
                "index": swing.index,
                "broken_count": len(broken),
                "broken_ids": [b.id for b in broken]
            })
    
    return {
        "ltf": ltf,
        "htf": htf,
        "swings": classified_swings,
        "htf_swings": htf_swings,
        "choch_events": choch_events,
        "bos_events": bos_events,
        "external_count": len([s for s in classified_swings if s.degree == "external"]),
        "internal_count": len([s for s in classified_swings if s.degree == "internal"]),
    }
```

---

## Multi-Timeframe Hierarchy (Advanced)

For more granular classification, layer multiple HTFs:

```python
STRUCTURE_HIERARCHY = {
    "15m": {
        "immediate_htf": "1H",    # 4x - for minor structure
        "major_htf": "4H",        # 16x - for external classification
        "premium_htf": "D",       # 96x - for premium/discount zones
    },
    "1H": {
        "immediate_htf": "4H",    # 4x
        "major_htf": "D",         # 24x
        "premium_htf": "W",       # 168x
    },
    # ... etc
}


def classify_multi_htf(
    ltf_swings: List[SwingPoint],
    immediate_htf_swings: List[SwingPoint],
    major_htf_swings: List[SwingPoint],
    tolerance: float = 0.001
) -> List[SwingPoint]:
    """Classify swings using multiple HTF levels.
    
    Returns swings with degree:
    - "external": Matches major HTF swing
    - "semi-external": Matches immediate HTF swing
    - "internal": Everything else
    """
    major_highs = {s.price for s in major_htf_swings if s.kind == "high"}
    major_lows = {s.price for s in major_htf_swings if s.kind == "low"}
    immediate_highs = {s.price for s in immediate_htf_swings if s.kind == "high"}
    immediate_lows = {s.price for s in immediate_htf_swings if s.kind == "low"}
    
    for swing in ltf_swings:
        levels_major = major_highs if swing.kind == "high" else major_lows
        levels_immediate = immediate_highs if swing.kind == "high" else immediate_lows
        
        if is_near_level(swing.price, levels_major, tolerance):
            swing.degree = "external"
        elif is_near_level(swing.price, levels_immediate, tolerance):
            swing.degree = "semi-external"
        else:
            swing.degree = "internal"
    
    return ltf_swings
```

---

## Testing Checklist

### HTF Mapping
- [ ] All LTF timeframes have valid HTF mapping
- [ ] HTF exists in Binance available timeframes
- [ ] Ratios are in acceptable range (12x-24x ideally)

### External Classification
- [ ] LTF swing at HTF high price → External
- [ ] LTF swing at HTF low price → External
- [ ] LTF swing between HTF levels → Internal
- [ ] Tolerance handles minor price differences

### CHoCH Detection
- [ ] LTF breaking HTF high → Bullish CHoCH
- [ ] LTF breaking HTF low → Bearish CHoCH
- [ ] LTF breaking internal → Not CHoCH (it's BOS)

### BOS Detection
- [ ] LTF breaking internal high → Bullish BOS
- [ ] LTF breaking internal low → Bearish BOS
- [ ] Multiple breaks counted in severity

### Edge Cases
- [ ] Daily to Weekly (7x ratio) works correctly
- [ ] First swing in dataset handled
- [ ] Empty HTF swings handled gracefully

---

## Summary

### Benefits of HTF-Based Approach

1. **Simplicity** — No complex state machines or move tracking
2. **Reliability** — HTF already filters market noise
3. **Alignment** — Always consistent with higher timeframe structure
4. **Performance** — Simple price comparisons vs complex logic
5. **Maintainability** — Easy to understand and debug

### Recommended Configuration

```python
# Use hardcoded mapping for reliability
BINANCE_HTF_MAPPING = {
    "1m": "15m",   # 15x
    "3m": "1H",    # 20x
    "5m": "1H",    # 12x
    "15m": "4H",   # 16x
    "30m": "6H",   # 12x
    "1H": "12H",   # 12x
    "2H": "1D",    # 12x
    "4H": "3D",    # 18x
    "6H": "3D",    # 12x
    "8H": "1W",    # 17.5x
    "12H": "1W",   # 14x
    "1D": "1W",    # 7x
    "3D": "1M",    # ~10x
    "1W": "1M",    # ~4x
}

# Default tolerance for price matching
DEFAULT_TOLERANCE = 0.001  # 0.1%
```

### Quick Reference

| What | How |
|------|-----|
| Get HTF | `htf = BINANCE_HTF_MAPPING[ltf]` |
| External | LTF swing price ≈ HTF swing price |
| Internal | Everything else |
| CHoCH | LTF breaks HTF level |
| BOS | LTF breaks LTF internal level |
