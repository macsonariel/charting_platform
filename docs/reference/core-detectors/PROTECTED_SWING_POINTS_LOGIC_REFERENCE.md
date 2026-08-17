# Protected Swing Points Logic Reference

## Document Purpose
This document defines the logic for "protected" swing points - swing points that remain valid and relevant until specific invalidation conditions are met. This prevents premature removal of important structural levels and maintains clean market structure analysis.

---

## Core Concept

### What is a Protected Swing Point?

A **protected swing point** is a swing high or low that has been confirmed and should remain on the chart until it is definitively invalidated by price action. Not every swing point deserves protection - only those that represent meaningful structural levels.

**Why Protect Swing Points?**
- Prevents clutter from minor, insignificant swings
- Maintains clear structural levels for analysis
- Enables proper CHoCH and BOS detection
- Shows only actionable support/resistance levels
- Reduces noise in market structure visualization

---

## Swing Point Lifecycle

### States
1. **Detected**: A potential swing point is identified (local high/low)
2. **Confirmed**: Swing point meets confirmation criteria
3. **Protected**: Swing point becomes a reference level
4. **Invalidated**: Protection is removed when conditions are met
5. **Removed**: Swing point is cleared from active display

### Flow
```
Price Action → Detection → Confirmation → Protection → Invalidation → Removal
                  ↓            ↓             ↓            ↓
              Tentative    Add to Array   Display    Remove from Array
```

---

## Protection Criteria

### When to Protect a Swing Point

A swing point should be protected when it represents a **structural level** in the market. Use these criteria:

#### 1. **Confirmation by Opposite Swing**
The most reliable method:

**For a HIGH to be protected:**
- A confirmed LOW must form AFTER the high
- The low confirms the high was a legitimate turning point

**For a LOW to be protected:**
- A confirmed HIGH must form AFTER the low
- The high confirms the low was a legitimate turning point

**Logic:**
```python
# Protecting a high
if new_swing.type == "L":  # New low formed
    if last_unprotected_high exists:
        protect_swing(last_unprotected_high)

# Protecting a low
if new_swing.type == "H":  # New high formed
    if last_unprotected_low exists:
        protect_swing(last_unprotected_low)
```

**Visual Example:**
```
    H2 (unconfirmed)
   /  \
  /    \         H3 ← When H3 forms...
H1     L1 ← L1 gets protected (confirmed by H3)
        \    /
         \  /
          L2
```

#### 2. **Classification-Based Protection**
Protect swings that have structural significance:

**Always Protect:**
- HH (Higher High) - Bullish structure continuation
- LL (Lower Low) - Bearish structure continuation
- HL (Higher Low) - First bullish reversal signal
- LH (Lower High) - First bearish reversal signal

**Optional Protection:**
- Unclassified swings in ranging markets
- Minor swings within larger structures (based on settings)

#### 3. **Price Movement Threshold**
Only protect swings that show meaningful price movement:

```python
def should_protect_by_magnitude(swing, previous_swing):
    """Protect if price movement exceeds threshold"""
    price_change = abs(swing.price - previous_swing.price)
    percentage_change = (price_change / previous_swing.price) * 100
    
    # Require minimum 0.5% move for protection
    return percentage_change >= 0.5
```

#### 4. **Time-Based Confirmation**
Protect swings that persist for a minimum duration:

```python
def should_protect_by_time(swing, current_time):
    """Protect if swing lasted minimum bars/time"""
    bars_since_swing = current_time - swing.timestamp
    
    # Require at least 3-5 bars before protection
    return bars_since_swing >= 3
```

---

## Invalidation Rules

### When to Remove Protection

Protected swing points should be invalidated when they are no longer relevant to current market structure.

### Rule 1: Price Violation (Definitive Break)

**For Protected HIGH:**
```python
if protected_high.is_protected:
    if close_price > protected_high.price:
        # Price closed above the high
        invalidate_swing(protected_high)
```

**For Protected LOW:**
```python
if protected_low.is_protected:
    if close_price < protected_low.price:
        # Price closed below the low
        invalidate_swing(protected_low)
```

**Important**: Use **close** price, not wicks. Wicks are false breakouts; closes are confirmations.

**Visual:**
```
Protected H at 110
         |
         | [Close at 112] ← HIGH is invalidated
    110 -|---------------- (protection removed)
         |
    105 -|

Protected L at 100
         |
     105-|
         |
    100 -|---------------- (protection removed)
         | [Close at 98] ← LOW is invalidated
         |
```

### Rule 2: Structural Replacement

When a new swing forms that supersedes the old one:

**For Protected HIGH in Bullish Structure:**
```python
# If new HH forms, old high can be invalidated
if current_structure == "BULLISH":
    if new_swing.type == "H" and new_swing.classification == "HH":
        # New higher high replaces old structural high
        invalidate_swing(previous_structure_high)
        protect_swing(new_swing)
```

**For Protected LOW in Bearish Structure:**
```python
# If new LL forms, old low can be invalidated
if current_structure == "BEARISH":
    if new_swing.type == "L" and new_swing.classification == "LL":
        # New lower low replaces old structural low
        invalidate_swing(previous_structure_low)
        protect_swing(new_swing)
```

**Visual Example:**
```
BEFORE:
    H1 (protected)
   /  \
  /    \
L1      L2

NEW HH FORMS:
              H2 (new, becomes protected) ← Higher high
             /
    H1 (invalidated) ← Old high no longer relevant
   /  \    /
  /    \  /
L1      L2
```

### Rule 3: Maximum Retention Count

Prevent infinite accumulation:

```python
MAX_PROTECTED_HIGHS = 5
MAX_PROTECTED_LOWS = 5

def enforce_protection_limits():
    """Keep only the most recent N protected swings"""
    if len(protected_highs) > MAX_PROTECTED_HIGHS:
        # Remove oldest protected high
        oldest = protected_highs[0]
        invalidate_swing(oldest)
    
    if len(protected_lows) > MAX_PROTECTED_LOWS:
        # Remove oldest protected low
        oldest = protected_lows[0]
        invalidate_swing(oldest)
```

### Rule 4: Age-Based Expiration

Remove very old protected swings:

```python
def check_swing_age(protected_swing, current_time):
    """Remove protection after certain time period"""
    MAX_AGE_BARS = 100  # or based on timeframe
    
    age = current_time - protected_swing.timestamp
    if age > MAX_AGE_BARS:
        invalidate_swing(protected_swing)
```

### Rule 5: Structure Change Invalidation

When market structure changes dramatically:

```python
def on_structure_change(new_structure):
    """Handle structure transition"""
    
    if new_structure != previous_structure:
        # Keep only the most recent 2-3 swings from old structure
        # Invalidate older ones
        
        if new_structure == "BULLISH":
            # Keep recent lows, remove old highs
            keep_recent_lows(count=2)
            invalidate_old_highs()
        
        elif new_structure == "BEARISH":
            # Keep recent highs, remove old lows
            keep_recent_highs(count=2)
            invalidate_old_lows()
```

---

## Implementation Algorithm

### Data Structures

```python
class SwingPoint:
    def __init__(self, price, index, swing_type, classification=None):
        self.price = price
        self.index = index
        self.type = swing_type  # "H" or "L"
        self.classification = classification  # "HH", "LL", "HL", "LH", None
        self.timestamp = index
        self.is_protected = False
        self.protection_timestamp = None
        self.invalidation_reason = None

# Storage arrays
all_swings = []           # Every detected swing
protected_highs = []      # Currently protected highs
protected_lows = []       # Currently protected lows
unprotected_swings = []   # Waiting for confirmation
```

### Core Functions

#### 1. Detecting Swing Points
```python
def detect_swing_point(candles, lookback=5):
    """
    Detect if current position is a swing high or low
    using a lookback/lookahead window
    """
    if len(candles) < lookback * 2 + 1:
        return None
    
    center_index = lookback
    center_candle = candles[center_index]
    
    # Check for swing high
    is_high = True
    for i in range(lookback * 2 + 1):
        if i == center_index:
            continue
        if candles[i].high >= center_candle.high:
            is_high = False
            break
    
    if is_high:
        return SwingPoint(
            price=center_candle.high,
            index=center_index,
            swing_type="H"
        )
    
    # Check for swing low
    is_low = True
    for i in range(lookback * 2 + 1):
        if i == center_index:
            continue
        if candles[i].low <= center_candle.low:
            is_low = False
            break
    
    if is_low:
        return SwingPoint(
            price=center_candle.low,
            index=center_index,
            swing_type="L"
        )
    
    return None
```

#### 2. Confirming and Protecting Swings
```python
def process_new_swing(swing):
    """Process a newly detected swing point"""
    
    # Add to all swings
    all_swings.append(swing)
    
    # Classify the swing (HH, LL, HL, LH)
    classify_swing(swing)
    
    # Check if previous opposite swing should be protected
    if swing.type == "H":
        # New high confirms previous low
        protect_last_unconfirmed_low()
    elif swing.type == "L":
        # New low confirms previous high
        protect_last_unconfirmed_high()
    
    # Add to unprotected list (will be protected later)
    unprotected_swings.append(swing)
    
    # Check invalidation conditions for existing protected swings
    check_invalidations(swing)


def protect_last_unconfirmed_high():
    """Protect the most recent unprotected high"""
    for swing in reversed(unprotected_swings):
        if swing.type == "H" and not swing.is_protected:
            protect_swing(swing)
            break


def protect_last_unconfirmed_low():
    """Protect the most recent unprotected low"""
    for swing in reversed(unprotected_swings):
        if swing.type == "L" and not swing.is_protected:
            protect_swing(swing)
            break


def protect_swing(swing):
    """Mark a swing as protected"""
    if swing.is_protected:
        return  # Already protected
    
    swing.is_protected = True
    swing.protection_timestamp = current_timestamp
    
    if swing.type == "H":
        protected_highs.append(swing)
    else:
        protected_lows.append(swing)
    
    # Remove from unprotected list
    if swing in unprotected_swings:
        unprotected_swings.remove(swing)
    
    print(f"Protected {swing.type} at {swing.price}")
```

#### 3. Checking Invalidations
```python
def check_invalidations(new_swing):
    """Check if new swing invalidates any protected swings"""
    
    current_close = get_current_close_price()
    
    # Check all protected highs
    for high in protected_highs[:]:  # Use slice to allow modification during iteration
        if should_invalidate_high(high, current_close, new_swing):
            invalidate_swing(high, "price_violation")
    
    # Check all protected lows
    for low in protected_lows[:]:
        if should_invalidate_low(low, current_close, new_swing):
            invalidate_swing(low, "price_violation")
    
    # Enforce maximum count
    enforce_protection_limits()


def should_invalidate_high(high, current_close, new_swing):
    """Determine if a protected high should be invalidated"""
    
    # Rule 1: Price closed above the high
    if current_close > high.price:
        return True
    
    # Rule 2: New HH replaces old high in bullish structure
    if current_structure == "BULLISH":
        if new_swing.type == "H" and new_swing.classification == "HH":
            if new_swing.price > high.price:
                return True
    
    # Rule 3: Age limit exceeded
    if current_timestamp - high.protection_timestamp > MAX_AGE_BARS:
        return True
    
    return False


def should_invalidate_low(low, current_close, new_swing):
    """Determine if a protected low should be invalidated"""
    
    # Rule 1: Price closed below the low
    if current_close < low.price:
        return True
    
    # Rule 2: New LL replaces old low in bearish structure
    if current_structure == "BEARISH":
        if new_swing.type == "L" and new_swing.classification == "LL":
            if new_swing.price < low.price:
                return True
    
    # Rule 3: Age limit exceeded
    if current_timestamp - low.protection_timestamp > MAX_AGE_BARS:
        return True
    
    return False


def invalidate_swing(swing, reason):
    """Remove protection from a swing point"""
    if not swing.is_protected:
        return
    
    swing.is_protected = False
    swing.invalidation_reason = reason
    
    if swing.type == "H":
        protected_highs.remove(swing)
    else:
        protected_lows.remove(swing)
    
    print(f"Invalidated {swing.type} at {swing.price} - Reason: {reason}")
```

---

## Protection Strategies

### Strategy 1: Conservative (Fewer Protected Swings)

**When to use**: Clean charts, major structure only, reduced noise

```python
CONFIRMATION_BARS = 5
MIN_PRICE_MOVE = 1.0  # 1% minimum
MAX_PROTECTED_HIGHS = 3
MAX_PROTECTED_LOWS = 3
PROTECT_ONLY_CLASSIFIED = True  # Only HH, LL, HL, LH

def should_protect_conservative(swing):
    """Conservative protection - only major swings"""
    if swing.classification is None:
        return False  # Must have classification
    
    if swing.classification not in ["HH", "LL", "HL", "LH"]:
        return False
    
    # Must show significant price movement
    if not exceeds_price_threshold(swing, MIN_PRICE_MOVE):
        return False
    
    return True
```

**Result**: 3-6 protected swings visible at any time

### Strategy 2: Moderate (Balanced Approach)

**When to use**: General trading, balanced view

```python
CONFIRMATION_BARS = 3
MIN_PRICE_MOVE = 0.5  # 0.5% minimum
MAX_PROTECTED_HIGHS = 5
MAX_PROTECTED_LOWS = 5
PROTECT_ONLY_CLASSIFIED = False

def should_protect_moderate(swing):
    """Moderate protection - balanced approach"""
    # Protect classified swings immediately
    if swing.classification in ["HH", "LL", "HL", "LH"]:
        return True
    
    # Protect unclassified if price move significant
    if exceeds_price_threshold(swing, MIN_PRICE_MOVE):
        return True
    
    return False
```

**Result**: 5-10 protected swings visible at any time

### Strategy 3: Aggressive (More Protected Swings)

**When to use**: Scalping, detailed analysis, multiple timeframe references

```python
CONFIRMATION_BARS = 2
MIN_PRICE_MOVE = 0.2  # 0.2% minimum
MAX_PROTECTED_HIGHS = 8
MAX_PROTECTED_LOWS = 8
PROTECT_ONLY_CLASSIFIED = False

def should_protect_aggressive(swing):
    """Aggressive protection - more swings retained"""
    # Protect almost all detected swings
    if swing.classification is not None:
        return True
    
    # Even minor swings get protected
    if exceeds_price_threshold(swing, MIN_PRICE_MOVE):
        return True
    
    return False
```

**Result**: 10-16 protected swings visible at any time

---

## Special Cases

### Case 1: Double Top / Double Bottom

When price reaches the same level twice:

```python
def handle_equal_levels(new_swing, tolerance=0.1):
    """Handle swings at equal price levels"""
    
    if new_swing.type == "H":
        for high in protected_highs:
            price_diff_pct = abs(new_swing.price - high.price) / high.price * 100
            
            if price_diff_pct <= tolerance:
                # Equal highs detected
                # Keep the older one, mark new one as "double top"
                new_swing.is_double_top = True
                # Don't protect the new one
                return False
    
    elif new_swing.type == "L":
        for low in protected_lows:
            price_diff_pct = abs(new_swing.price - low.price) / low.price * 100
            
            if price_diff_pct <= tolerance:
                # Equal lows detected
                new_swing.is_double_bottom = True
                return False
    
    return True  # Proceed with normal protection
```

### Case 2: Ranging Market

In ranging markets, protect outer boundaries:

```python
def protect_range_boundaries():
    """In ranging market, keep range high and low protected"""
    
    if current_structure == "RANGING":
        # Identify range high and low
        range_high = max(protected_highs, key=lambda x: x.price)
        range_low = min(protected_lows, key=lambda x: x.price)
        
        # These should never be invalidated until range breaks
        range_high.is_range_boundary = True
        range_low.is_range_boundary = True
        
        # Invalidate interior swings more aggressively
        for high in protected_highs:
            if not high.is_range_boundary:
                if age_exceeds(high, 20):  # Shorter age limit
                    invalidate_swing(high, "range_interior")
```

### Case 3: Structure Transition

When structure changes, manage swing protection carefully:

```python
def on_structure_change(old_structure, new_structure):
    """Handle structure change - selective invalidation"""
    
    if old_structure == "BULLISH" and new_structure == "BEARISH":
        # Keep the high that caused CHoCH (it's now structure high)
        # Invalidate older highs
        most_recent_high = protected_highs[-1]  # Keep this
        
        for high in protected_highs[:-1]:
            invalidate_swing(high, "structure_change")
        
        # Keep recent 2 lows for context
        if len(protected_lows) > 2:
            for low in protected_lows[:-2]:
                invalidate_swing(low, "structure_change")
    
    elif old_structure == "BEARISH" and new_structure == "BULLISH":
        # Keep the low that caused CHoCH
        most_recent_low = protected_lows[-1]
        
        for low in protected_lows[:-1]:
            invalidate_swing(low, "structure_change")
        
        # Keep recent 2 highs for context
        if len(protected_highs) > 2:
            for high in protected_highs[:-2]:
                invalidate_swing(high, "structure_change")
```

---

## Visual Display Guidelines

### How to Display Protected Swings

```javascript
// On chart, show protected swings differently
function renderSwingPoint(swing) {
    if (swing.is_protected) {
        // Draw horizontal line extending right
        drawHorizontalLine({
            y: swing.price,
            x_start: swing.index,
            x_end: current_index,
            color: swing.type === "H" ? "red" : "green",
            width: 2,
            style: "solid"
        });
        
        // Add label
        drawLabel({
            text: swing.classification || swing.type,
            x: swing.index,
            y: swing.price,
            color: swing.type === "H" ? "red" : "green"
        });
    } else {
        // Unprotected swings shown with lighter styling
        drawPoint({
            x: swing.index,
            y: swing.price,
            color: "gray",
            size: 3,
            opacity: 0.5
        });
    }
}
```

### Visual Hierarchy

1. **Protected Highs**: Red horizontal lines
2. **Protected Lows**: Green horizontal lines
3. **Structure High/Low**: Thicker lines or different color
4. **Recent CHoCH/BOS**: Markers on the lines
5. **Unprotected Swings**: Faint dots or not shown

---

## Integration with CHoCH/BOS Logic

Protected swings are the foundation for CHoCH and BOS detection:

```python
def detect_choch_bos_with_protected_swings():
    """Use only protected swings for structure analysis"""
    
    # Get the relevant protected level
    if current_structure == "BULLISH":
        structure_high = get_most_recent_protected_high()
    elif current_structure == "BEARISH":
        structure_low = get_most_recent_protected_low()
    
    # Check new swing against protected level
    if new_swing.type == "H":
        if current_structure == "BULLISH":
            if new_swing.price > structure_high.price:
                emit_bos("BULLISH")
                # Invalidate old structure high
                invalidate_swing(structure_high, "bos_replacement")
                # Protect new swing as new structure high
                protect_swing(new_swing)
```

**Benefits:**
- CHoCH/BOS only fires on meaningful breaks
- Reduces false signals from minor swings
- Clear reference levels for traders
- Automatic cleanup of invalidated levels

---

## Common Implementation Errors

### Error 1: Protecting Every Swing
❌ **WRONG:**
```python
# Protecting every detected swing
def on_swing_detected(swing):
    protect_swing(swing)  # Too many swings!
```

✅ **CORRECT:**
```python
# Protect only after confirmation
def on_swing_detected(swing):
    add_to_unconfirmed(swing)
    # Wait for opposite swing to confirm

def on_opposite_swing_detected():
    protect_last_unconfirmed_swing()
```

### Error 2: Never Invalidating
❌ **WRONG:**
```python
# Once protected, never removed
protected_swings.append(swing)
# Results in hundreds of lines on chart
```

✅ **CORRECT:**
```python
# Regular invalidation checks
def on_price_update():
    check_all_invalidations()
    enforce_protection_limits()
```

### Error 3: Wrong Invalidation Trigger
❌ **WRONG:**
```python
# Invalidating on wick touch
if high_of_candle > protected_high:
    invalidate(protected_high)
```

✅ **CORRECT:**
```python
# Invalidating on close beyond level
if close_of_candle > protected_high:
    invalidate(protected_high)
```

### Error 4: Not Updating References
❌ **WRONG:**
```python
# Keeping invalidated swing as structure reference
if new_swing breaks structure_high:
    emit_bos()
    # Missing: update structure_high reference
```

✅ **CORRECT:**
```python
if new_swing breaks structure_high:
    invalidate_swing(structure_high)
    protect_swing(new_swing)
    structure_high = new_swing  # Update reference
```

### Error 5: Ignoring Structure Context
❌ **WRONG:**
```python
# Same protection rules regardless of structure
protect_swing(swing)
```

✅ **CORRECT:**
```python
# Protection based on structure relevance
if current_structure == "BULLISH" and swing.type == "L":
    # Lows more important in bullish structure
    protect_swing(swing)
elif current_structure == "BEARISH" and swing.type == "H":
    # Highs more important in bearish structure
    protect_swing(swing)
```

---

## Test Cases

### Test 1: Basic Protection Flow
```
Swings detected:
1. H at 110 (unprotected)
2. L at 100 (detected)
   → Protect H at 110 (confirmed by opposite swing)
3. H at 115 (detected)
   → Protect L at 100 (confirmed by opposite swing)

Expected:
- H at 110 is protected
- L at 100 is protected
- H at 115 waiting for confirmation
```

### Test 2: Price Invalidation
```
Protected: H at 110
Price action:
- Close at 108 → H still protected
- Close at 111 → H invalidated (close above level)

Expected:
- H at 110 removed from protected_highs
```

### Test 3: Structural Replacement
```
Structure: BULLISH
Protected: H at 110 (structure high)

New swing: HH at 120
Expected:
- Emit Bullish BOS
- Invalidate H at 110
- Protect H at 120 as new structure high
```

### Test 4: Maximum Count Enforcement
```
MAX_PROTECTED_HIGHS = 3
Protected highs: [100, 105, 110]

New high detected at 115:
Expected:
- Invalidate oldest (100)
- Protect new high (115)
- Protected highs: [105, 110, 115]
```

### Test 5: Structure Change Cleanup
```
Structure: BULLISH
Protected highs: [95, 100, 105, 110]
Protected lows: [90, 92, 94]

CHoCH to BEARISH occurs:
Expected:
- Keep most recent high (110) as structure high
- Invalidate old highs [95, 100, 105]
- Keep recent 2 lows [92, 94]
- Invalidate oldest low [90]
```

---

## Configuration Options

### Settings for User Customization

```python
class ProtectionSettings:
    # Confirmation
    CONFIRMATION_METHOD = "opposite_swing"  # or "time", "bars", "price_move"
    CONFIRMATION_BARS = 3
    
    # Protection criteria
    MIN_PRICE_MOVE_PCT = 0.5
    PROTECT_ONLY_CLASSIFIED = False
    
    # Limits
    MAX_PROTECTED_HIGHS = 5
    MAX_PROTECTED_LOWS = 5
    
    # Invalidation
    INVALIDATE_ON_CLOSE = True  # vs wick
    MAX_AGE_BARS = 100
    ENABLE_AGE_INVALIDATION = True
    
    # Structure-based
    INVALIDATE_ON_STRUCTURE_CHANGE = True
    KEEP_CONTEXT_SWINGS = 2  # How many old swings to keep after structure change
    
    # Visual
    SHOW_UNPROTECTED_SWINGS = False
    EXTEND_LINES_TO_CURRENT = True
```

---

## Debugging Checklist

When protected swings aren't working correctly:

### Visual Issues
- [ ] Are too many swings showing? → Reduce MAX_PROTECTED count
- [ ] Are swings disappearing too quickly? → Check invalidation logic
- [ ] Are old swings never removed? → Enable age-based invalidation
- [ ] Are swings not appearing? → Check protection confirmation logic

### Logic Issues
- [ ] Are swings being protected immediately? → Should wait for opposite swing
- [ ] Are invalidations happening on wicks? → Should use close price
- [ ] Are structure levels being removed? → Check structure_high/low invalidation
- [ ] Are swings accumulating infinitely? → Enforce maximum count

### Integration Issues
- [ ] Are CHoCH/BOS not firing? → Check if using protected swings as reference
- [ ] Are structure levels incorrect? → Verify protection of structure-defining swings
- [ ] Are reference levels stale? → Update on BOS/CHoCH events

---

## Summary Algorithm

```
SWING DETECTION:
1. Detect local high/low using lookback window
2. Classify swing (HH, LL, HL, LH)
3. Add to unconfirmed swings list

PROTECTION TRIGGER:
4. When opposite swing forms:
   - Protect the previous unconfirmed swing
   - Add to protected_highs or protected_lows array

INVALIDATION CHECK (on every new candle/swing):
5. For each protected high:
   - If close > high.price → invalidate
   - If new HH replaces it → invalidate
   - If age exceeds limit → invalidate

6. For each protected low:
   - If close < low.price → invalidate
   - If new LL replaces it → invalidate
   - If age exceeds limit → invalidate

7. Enforce maximum count limits
8. Update structure references

DISPLAY:
9. Draw protected swings as horizontal lines
10. Show classifications as labels
11. Highlight structure levels differently
```

---

## Quick Reference

| Scenario | Action |
|----------|--------|
| New H detected | Add to unconfirmed, wait for L to protect it |
| New L detected | Add to unconfirmed, wait for H to protect it |
| Close above protected H | Invalidate that H |
| Close below protected L | Invalidate that L |
| HH forms in bullish | Invalidate old structure high, protect new one |
| LL forms in bearish | Invalidate old structure low, protect new one |
| CHoCH occurs | Invalidate opposite structure swings, keep relevant ones |
| Max count exceeded | Invalidate oldest protected swing |
| Swing age exceeds limit | Invalidate for staleness |

---

## Integration Summary

Protected swing points work together with CHoCH/BOS detection:

1. **Detection** → Swing points are identified
2. **Classification** → Swings labeled as HH/LL/HL/LH  
3. **Protection** → Meaningful swings are protected
4. **Structure Analysis** → Protected swings define market structure
5. **CHoCH/BOS** → Structural breaks detected using protected levels
6. **Invalidation** → Old levels removed when no longer relevant
7. **Display** → Clean chart showing only actionable levels

This creates a self-maintaining system where the chart always shows relevant structural levels without manual cleanup.

---

**End of Reference Document**

Use this to implement a robust protected swing point system that keeps charts clean while maintaining all structurally significant levels.
