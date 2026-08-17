# Triangle Pattern Detection Logic

**Based on Swing Point Analysis**

---

## Table of Contents

1. [Triangle Pattern Overview](#triangle-pattern-overview)
2. [Core Components](#core-components)
3. [Ascending Triangle Detection](#ascending-triangle-detection)
4. [Descending Triangle Detection](#descending-triangle-detection)
5. [Symmetrical Triangle Detection](#symmetrical-triangle-detection)
6. [Trendline Construction](#trendline-construction)
7. [Pattern Validation](#pattern-validation)
8. [Breakout Detection](#breakout-detection)
9. [Measured Move Targets](#measured-move-targets)
10. [Pattern Invalidation](#pattern-invalidation)
11. [Configuration Parameters](#configuration-parameters)
12. [Implementation Architecture](#implementation-architecture)

---

## Triangle Pattern Overview

### What is a Triangle?

A **triangle** is a consolidation pattern formed by converging trendlines, creating a triangular shape. Price oscillates between these boundaries with decreasing volatility until a breakout occurs.

### Triangle Types

**Ascending Triangle (Bullish Bias):**
- Flat/horizontal resistance at top
- Rising support at bottom
- Typically breaks upward (continuation in uptrend, reversal in downtrend)

**Descending Triangle (Bearish Bias):**
- Flat/horizontal support at bottom
- Declining resistance at top
- Typically breaks downward (continuation in downtrend, reversal in uptrend)

**Symmetrical Triangle (Neutral):**
- Descending resistance at top
- Rising support at bottom
- Can break either direction (continuation pattern)

### Visual Structure

```
Ascending Triangle:
    Resistance _______________  (flat top)
              /  /   /    /
             /  /   /    /
            /  /   /    /   ↑ (breakout up)
  Support /  /   /    /      (rising bottom)

Descending Triangle:
  Resistance \   \    \    \   (declining top)
              \   \    \    \
               \   \    \    \  ↓ (breakout down)
    Support ___\___\____\____\  (flat bottom)

Symmetrical Triangle:
           /\
          /  \
         /    \    (converging lines)
        /      \
       /________\
```

---

## Core Components

### Pattern Structure Requirements

All triangle patterns require:

1. **Minimum swing points**: At least 4 swings (2 highs, 2 lows) to establish both trendlines
2. **Converging trendlines**: Lines must converge to form apex
3. **Decreasing volatility**: Each swing should be smaller than the previous (compression)
4. **Time limit**: Pattern should complete before reaching apex
5. **Clear boundaries**: Multiple touches on both trendlines

### Swing Point Requirements

**For Ascending Triangle:**
```
High_1, High_2, High_3, ... : Form flat resistance (roughly equal heights)
Low_1, Low_2, Low_3, ...    : Form rising support (progressively higher lows)

Minimum: 2 highs + 2 lows = 4 total swings
Ideal: 3 highs + 3 lows = 6 total swings
```

**For Descending Triangle:**
```
High_1, High_2, High_3, ... : Form declining resistance (progressively lower highs)
Low_1, Low_2, Low_3, ...    : Form flat support (roughly equal depths)

Minimum: 2 highs + 2 lows = 4 total swings
Ideal: 3 highs + 3 lows = 6 total swings
```

**For Symmetrical Triangle:**
```
High_1, High_2, High_3, ... : Form declining resistance (lower highs)
Low_1, Low_2, Low_3, ...    : Form rising support (higher lows)

Minimum: 2 highs + 2 lows = 4 total swings
Ideal: 3 highs + 3 lows = 6 total swings
```

---

## Ascending Triangle Detection

### Step-by-Step Detection Logic

```python
class AscendingTrianglePattern:
    """
    Detect and validate ascending triangle patterns
    
    Structure:
    - Flat horizontal resistance (highs at similar level)
    - Rising support (progressively higher lows)
    - Typically bullish (breaks upward)
    """
    
    def __init__(self):
        self.highs = []              # Swing highs forming resistance
        self.lows = []               # Swing lows forming support
        self.resistance_level = None # Horizontal resistance
        self.support_trendline = None # Rising support line
        self.apex = None
        self.status = "forming"
        self.pattern_start_time = None
        
    def add_swing(self, swing):
        """
        Add swing point to pattern
        """
        if swing.type == "high":
            self.highs.append(swing)
        else:
            self.lows.append(swing)
        
        # Set pattern start if first swing
        if self.pattern_start_time is None:
            self.pattern_start_time = swing.time
        
        # Try to construct pattern if enough swings
        if len(self.highs) >= 2 and len(self.lows) >= 2:
            if self.construct_triangle():
                self.status = "complete"
                return True
        
        return False
    
    def construct_triangle(self):
        """
        Construct ascending triangle from swing points
        
        Returns:
            True if valid ascending triangle formed
        """
        # 1. Construct horizontal resistance from highs
        self.resistance_level = self.construct_horizontal_resistance()
        
        if not self.resistance_level:
            return False
        
        # 2. Construct rising support from lows
        self.support_trendline = self.construct_rising_support()
        
        if not self.support_trendline:
            return False
        
        # 3. Validate triangle structure
        if not self.validate_triangle_structure():
            return False
        
        # 4. Calculate apex
        self.apex = self.calculate_apex()
        
        return True
    
    def construct_horizontal_resistance(self):
        """
        Build horizontal resistance from swing highs
        
        Highs should be at roughly the same level (within tolerance)
        """
        if len(self.highs) < 2:
            return None
        
        # Calculate average high
        high_prices = [h.price for h in self.highs]
        avg_high = sum(high_prices) / len(high_prices)
        
        # Check if all highs are within tolerance of average
        tolerance = 0.02  # 2% tolerance
        
        for high_price in high_prices:
            deviation = abs(high_price - avg_high) / avg_high
            if deviation > tolerance:
                # Highs not flat enough - not ascending triangle
                return None
        
        # Use most recent high as resistance level (most relevant)
        # Or use average - both approaches valid
        resistance = max(high_prices)  # Using highest point as resistance
        
        return {
            'price': resistance,
            'type': 'horizontal',
            'touches': len(self.highs),
            'first_touch_time': self.highs[0].time,
            'last_touch_time': self.highs[-1].time
        }
    
    def construct_rising_support(self):
        """
        Build rising support trendline from swing lows
        
        Lows should be progressively higher (ascending)
        """
        if len(self.lows) < 2:
            return None
        
        # Check that lows are progressively higher
        for i in range(1, len(self.lows)):
            if self.lows[i].price <= self.lows[i-1].price:
                # Lows not rising - not ascending triangle
                return None
        
        # Fit trendline through lows
        # Use first and last low for simple method
        first_low = self.lows[0]
        last_low = self.lows[-1]
        
        slope = (last_low.price - first_low.price) / (last_low.time - first_low.time)
        intercept = first_low.price - slope * first_low.time
        
        # Slope must be positive (rising)
        if slope <= 0:
            return None
        
        return {
            'slope': slope,
            'intercept': intercept,
            'type': 'rising',
            'touches': len(self.lows),
            'first_touch': first_low,
            'last_touch': last_low
        }
    
    def validate_triangle_structure(self):
        """
        Validate ascending triangle structure
        
        Requirements:
        - Resistance must be flat (horizontal)
        - Support must be rising
        - Lines must converge (meet at apex)
        - Decreasing volatility (compression)
        - All lows touch or come close to support line
        - All highs touch or come close to resistance
        """
        if not self.resistance_level or not self.support_trendline:
            return False
        
        # 1. Validate lows touch support trendline
        for low in self.lows:
            expected_price = (
                self.support_trendline['slope'] * low.time +
                self.support_trendline['intercept']
            )
            deviation = abs(low.price - expected_price) / expected_price
            
            if deviation > 0.02:  # 2% tolerance
                return False  # Low doesn't touch support line
        
        # 2. Validate highs touch resistance
        for high in self.highs:
            deviation = abs(high.price - self.resistance_level['price']) / self.resistance_level['price']
            
            if deviation > 0.02:  # 2% tolerance
                return False  # High doesn't touch resistance
        
        # 3. Validate convergence (support rises toward resistance)
        # At start of pattern
        start_time = self.lows[0].time
        start_support = self.support_trendline['slope'] * start_time + self.support_trendline['intercept']
        start_gap = self.resistance_level['price'] - start_support
        
        # At end of pattern
        end_time = self.lows[-1].time
        end_support = self.support_trendline['slope'] * end_time + self.support_trendline['intercept']
        end_gap = self.resistance_level['price'] - end_support
        
        # Gap should be narrowing
        if end_gap >= start_gap:
            return False  # Lines not converging
        
        # 4. Validate compression (each swing smaller than previous)
        if not self.validate_compression():
            return False
        
        return True
    
    def validate_compression(self):
        """
        Validate that price swings are getting smaller (compression)
        
        Each high-to-low distance should be smaller than the previous
        """
        if len(self.highs) < 2 or len(self.lows) < 2:
            return True  # Too early to validate
        
        # Calculate swing ranges
        swing_ranges = []
        
        # Match each high with subsequent low
        for i in range(min(len(self.highs), len(self.lows))):
            if i < len(self.highs) and i < len(self.lows):
                swing_range = abs(self.highs[i].price - self.lows[i].price)
                swing_ranges.append(swing_range)
        
        # Check if ranges are generally decreasing
        # Allow some noise - check overall trend
        if len(swing_ranges) >= 3:
            first_third_avg = sum(swing_ranges[:len(swing_ranges)//3]) / max(1, len(swing_ranges)//3)
            last_third_avg = sum(swing_ranges[-len(swing_ranges)//3:]) / max(1, len(swing_ranges)//3)
            
            # Last third should be smaller than first third
            if last_third_avg >= first_third_avg * 0.9:  # Allow 10% tolerance
                return False
        
        return True
    
    def calculate_apex(self):
        """
        Calculate where support trendline meets resistance
        
        This is the theoretical convergence point
        """
        # Resistance is horizontal: y = resistance_price
        # Support: y = slope * t + intercept
        
        # Set equal and solve for t:
        # resistance_price = slope * t + intercept
        # t = (resistance_price - intercept) / slope
        
        resistance_price = self.resistance_level['price']
        slope = self.support_trendline['slope']
        intercept = self.support_trendline['intercept']
        
        if slope == 0:
            return None  # Lines don't converge
        
        apex_time = (resistance_price - intercept) / slope
        apex_price = resistance_price
        
        return {
            'time': apex_time,
            'price': apex_price
        }
```

### Progressive Detection

```python
    def update(self, new_swing):
        """
        Update pattern with new swing point
        
        Progressive detection as pattern forms
        """
        # Add swing to appropriate list
        if new_swing.type == "high":
            self.highs.append(new_swing)
        else:
            self.lows.append(new_swing)
        
        # Check if we have enough swings to attempt construction
        if len(self.highs) >= 2 and len(self.lows) >= 2:
            # Try to construct triangle
            if self.construct_triangle():
                # Check if pattern is ready (not too close to apex)
                if self.is_pattern_ready():
                    self.status = "complete"
                    return True
        
        # Check if pattern has failed
        if self.check_pattern_failure(new_swing):
            self.status = "failed"
            return False
        
        return False
    
    def is_pattern_ready(self):
        """
        Pattern should be complete before reaching apex
        
        Typically breaks at 50-75% of distance to apex
        """
        if not self.apex:
            return False
        
        current_time = self.lows[-1].time
        start_time = self.lows[0].time
        apex_time = self.apex['time']
        
        # Calculate progress to apex
        total_duration = apex_time - start_time
        current_duration = current_time - start_time
        
        progress = current_duration / total_duration if total_duration > 0 else 0
        
        # Should be at least 30% formed but not past 80%
        if progress < 0.3:
            return False  # Too early
        
        if progress > 0.8:
            self.status = "failed_reached_apex"
            return False  # Too late, should have broken by now
        
        return True
    
    def check_pattern_failure(self, new_swing):
        """
        Check if new swing invalidates the pattern
        """
        # If a new low is lower than previous low - support broken
        if new_swing.type == "low" and len(self.lows) >= 2:
            if new_swing.price < self.lows[-2].price:
                return True  # Support not rising anymore
        
        # If highs start rising instead of staying flat
        if new_swing.type == "high" and len(self.highs) >= 2:
            avg_high = sum(h.price for h in self.highs) / len(self.highs)
            if new_swing.price > avg_high * 1.03:  # 3% above average
                return True  # Resistance not flat anymore
        
        return False
```

---

## Descending Triangle Detection

### Descending Triangle Structure

**Opposite of ascending triangle:**

```python
class DescendingTrianglePattern:
    """
    Detect and validate descending triangle patterns
    
    Structure:
    - Flat horizontal support (lows at similar level)
    - Declining resistance (progressively lower highs)
    - Typically bearish (breaks downward)
    """
    
    def __init__(self):
        self.highs = []              # Swing highs forming resistance
        self.lows = []               # Swing lows forming support
        self.support_level = None    # Horizontal support
        self.resistance_trendline = None # Declining resistance line
        self.apex = None
        self.status = "forming"
        self.pattern_start_time = None
    
    def construct_triangle(self):
        """
        Construct descending triangle from swing points
        """
        # 1. Construct horizontal support from lows
        self.support_level = self.construct_horizontal_support()
        
        if not self.support_level:
            return False
        
        # 2. Construct declining resistance from highs
        self.resistance_trendline = self.construct_declining_resistance()
        
        if not self.resistance_trendline:
            return False
        
        # 3. Validate triangle structure
        if not self.validate_triangle_structure():
            return False
        
        # 4. Calculate apex
        self.apex = self.calculate_apex()
        
        return True
    
    def construct_horizontal_support(self):
        """
        Build horizontal support from swing lows
        
        Lows should be at roughly the same level (within tolerance)
        """
        if len(self.lows) < 2:
            return None
        
        # Calculate average low
        low_prices = [l.price for l in self.lows]
        avg_low = sum(low_prices) / len(low_prices)
        
        # Check if all lows are within tolerance of average
        tolerance = 0.02  # 2% tolerance
        
        for low_price in low_prices:
            deviation = abs(low_price - avg_low) / avg_low
            if deviation > tolerance:
                return None  # Lows not flat enough
        
        # Use lowest point as support level
        support = min(low_prices)
        
        return {
            'price': support,
            'type': 'horizontal',
            'touches': len(self.lows),
            'first_touch_time': self.lows[0].time,
            'last_touch_time': self.lows[-1].time
        }
    
    def construct_declining_resistance(self):
        """
        Build declining resistance trendline from swing highs
        
        Highs should be progressively lower (descending)
        """
        if len(self.highs) < 2:
            return None
        
        # Check that highs are progressively lower
        for i in range(1, len(self.highs)):
            if self.highs[i].price >= self.highs[i-1].price:
                return None  # Highs not declining
        
        # Fit trendline through highs
        first_high = self.highs[0]
        last_high = self.highs[-1]
        
        slope = (last_high.price - first_high.price) / (last_high.time - first_high.time)
        intercept = first_high.price - slope * first_high.time
        
        # Slope must be negative (declining)
        if slope >= 0:
            return None
        
        return {
            'slope': slope,
            'intercept': intercept,
            'type': 'declining',
            'touches': len(self.highs),
            'first_touch': first_high,
            'last_touch': last_high
        }
    
    def validate_triangle_structure(self):
        """
        Validate descending triangle structure
        """
        if not self.support_level or not self.resistance_trendline:
            return False
        
        # 1. Validate highs touch resistance trendline
        for high in self.highs:
            expected_price = (
                self.resistance_trendline['slope'] * high.time +
                self.resistance_trendline['intercept']
            )
            deviation = abs(high.price - expected_price) / expected_price
            
            if deviation > 0.02:  # 2% tolerance
                return False
        
        # 2. Validate lows touch support
        for low in self.lows:
            deviation = abs(low.price - self.support_level['price']) / self.support_level['price']
            
            if deviation > 0.02:  # 2% tolerance
                return False
        
        # 3. Validate convergence (resistance declines toward support)
        start_time = self.highs[0].time
        start_resistance = self.resistance_trendline['slope'] * start_time + self.resistance_trendline['intercept']
        start_gap = start_resistance - self.support_level['price']
        
        end_time = self.highs[-1].time
        end_resistance = self.resistance_trendline['slope'] * end_time + self.resistance_trendline['intercept']
        end_gap = end_resistance - self.support_level['price']
        
        # Gap should be narrowing
        if end_gap >= start_gap:
            return False
        
        # 4. Validate compression
        if not self.validate_compression():
            return False
        
        return True
    
    def calculate_apex(self):
        """
        Calculate where resistance trendline meets support
        """
        # Support is horizontal: y = support_price
        # Resistance: y = slope * t + intercept
        
        # Set equal and solve for t:
        # support_price = slope * t + intercept
        # t = (support_price - intercept) / slope
        
        support_price = self.support_level['price']
        slope = self.resistance_trendline['slope']
        intercept = self.resistance_trendline['intercept']
        
        if slope == 0:
            return None
        
        apex_time = (support_price - intercept) / slope
        apex_price = support_price
        
        return {
            'time': apex_time,
            'price': apex_price
        }
```

---

## Symmetrical Triangle Detection

### Symmetrical Triangle Structure

**Both trendlines converge:**

```python
class SymmetricalTrianglePattern:
    """
    Detect and validate symmetrical triangle patterns
    
    Structure:
    - Declining resistance (lower highs)
    - Rising support (higher lows)
    - Neutral - can break either direction
    - Typically continuation pattern
    """
    
    def __init__(self):
        self.highs = []
        self.lows = []
        self.resistance_trendline = None  # Declining
        self.support_trendline = None     # Rising
        self.apex = None
        self.status = "forming"
        self.pattern_start_time = None
    
    def construct_triangle(self):
        """
        Construct symmetrical triangle from swing points
        """
        # 1. Construct declining resistance from highs
        self.resistance_trendline = self.construct_declining_resistance()
        
        if not self.resistance_trendline:
            return False
        
        # 2. Construct rising support from lows
        self.support_trendline = self.construct_rising_support()
        
        if not self.support_trendline:
            return False
        
        # 3. Validate triangle structure
        if not self.validate_triangle_structure():
            return False
        
        # 4. Calculate apex
        self.apex = self.calculate_apex()
        
        return True
    
    def construct_declining_resistance(self):
        """
        Build declining resistance from swing highs
        
        Highs should be progressively lower
        """
        if len(self.highs) < 2:
            return None
        
        # Check that highs are declining
        for i in range(1, len(self.highs)):
            if self.highs[i].price >= self.highs[i-1].price:
                return None
        
        # Fit trendline
        first_high = self.highs[0]
        last_high = self.highs[-1]
        
        slope = (last_high.price - first_high.price) / (last_high.time - first_high.time)
        intercept = first_high.price - slope * first_high.time
        
        # Slope must be negative
        if slope >= 0:
            return None
        
        return {
            'slope': slope,
            'intercept': intercept,
            'type': 'declining',
            'touches': len(self.highs)
        }
    
    def construct_rising_support(self):
        """
        Build rising support from swing lows
        
        Lows should be progressively higher
        """
        if len(self.lows) < 2:
            return None
        
        # Check that lows are rising
        for i in range(1, len(self.lows)):
            if self.lows[i].price <= self.lows[i-1].price:
                return None
        
        # Fit trendline
        first_low = self.lows[0]
        last_low = self.lows[-1]
        
        slope = (last_low.price - first_low.price) / (last_low.time - first_low.time)
        intercept = first_low.price - slope * first_low.time
        
        # Slope must be positive
        if slope <= 0:
            return None
        
        return {
            'slope': slope,
            'intercept': intercept,
            'type': 'rising',
            'touches': len(self.lows)
        }
    
    def validate_triangle_structure(self):
        """
        Validate symmetrical triangle structure
        
        Additional requirement: Lines should converge at similar rate
        (slopes roughly equal in magnitude)
        """
        if not self.resistance_trendline or not self.support_trendline:
            return False
        
        # 1. Validate highs touch resistance
        for high in self.highs:
            expected_price = (
                self.resistance_trendline['slope'] * high.time +
                self.resistance_trendline['intercept']
            )
            deviation = abs(high.price - expected_price) / expected_price
            
            if deviation > 0.02:
                return False
        
        # 2. Validate lows touch support
        for low in self.lows:
            expected_price = (
                self.support_trendline['slope'] * low.time +
                self.support_trendline['intercept']
            )
            deviation = abs(low.price - expected_price) / expected_price
            
            if deviation > 0.02:
                return False
        
        # 3. Validate symmetry (slopes similar magnitude)
        resistance_slope_abs = abs(self.resistance_trendline['slope'])
        support_slope_abs = abs(self.support_trendline['slope'])
        
        slope_ratio = min(resistance_slope_abs, support_slope_abs) / max(resistance_slope_abs, support_slope_abs)
        
        # Slopes should be within 50% of each other for symmetry
        if slope_ratio < 0.5:
            return False  # One line converging much faster - not symmetrical
        
        # 4. Validate convergence
        if not self.validate_convergence():
            return False
        
        # 5. Validate compression
        if not self.validate_compression():
            return False
        
        return True
    
    def validate_convergence(self):
        """
        Ensure lines are actually converging (getting closer)
        """
        # Calculate gap at start and end
        start_time = min(self.highs[0].time, self.lows[0].time)
        end_time = max(self.highs[-1].time, self.lows[-1].time)
        
        # Gap at start
        start_resistance = self.resistance_trendline['slope'] * start_time + self.resistance_trendline['intercept']
        start_support = self.support_trendline['slope'] * start_time + self.support_trendline['intercept']
        start_gap = start_resistance - start_support
        
        # Gap at end
        end_resistance = self.resistance_trendline['slope'] * end_time + self.resistance_trendline['intercept']
        end_support = self.support_trendline['slope'] * end_time + self.support_trendline['intercept']
        end_gap = end_resistance - end_support
        
        # Gap should be decreasing
        if end_gap >= start_gap * 0.95:  # Allow 5% tolerance
            return False
        
        return True
    
    def calculate_apex(self):
        """
        Calculate intersection point of two lines
        
        Resistance: y = slope_r * t + intercept_r
        Support:    y = slope_s * t + intercept_s
        
        At intersection:
        slope_r * t + intercept_r = slope_s * t + intercept_s
        t = (intercept_s - intercept_r) / (slope_r - slope_s)
        """
        slope_r = self.resistance_trendline['slope']
        slope_s = self.support_trendline['slope']
        intercept_r = self.resistance_trendline['intercept']
        intercept_s = self.support_trendline['intercept']
        
        if slope_r == slope_s:
            return None  # Lines parallel, don't converge
        
        apex_time = (intercept_s - intercept_r) / (slope_r - slope_s)
        apex_price = slope_r * apex_time + intercept_r
        
        return {
            'time': apex_time,
            'price': apex_price
        }
```

---

## Trendline Construction

### Advanced Trendline Fitting

**Method 1: Regression-Based (Most Accurate)**

```python
def construct_trendline_regression(swings, line_type):
    """
    Fit trendline using linear regression through all swing points
    
    Args:
        swings: List of swing points
        line_type: 'rising', 'declining', or 'horizontal'
    
    Returns:
        Trendline dictionary with slope, intercept, R-squared
    """
    if len(swings) < 2:
        return None
    
    # Prepare data
    times = [s.time for s in swings]
    prices = [s.price for s in swings]
    n = len(swings)
    
    # Calculate linear regression
    sum_t = sum(times)
    sum_p = sum(prices)
    sum_tp = sum(t * p for t, p in zip(times, prices))
    sum_t2 = sum(t ** 2 for t in times)
    
    # Slope and intercept
    slope = (n * sum_tp - sum_t * sum_p) / (n * sum_t2 - sum_t ** 2)
    intercept = (sum_p - slope * sum_t) / n
    
    # Validate slope matches expected line type
    if line_type == 'rising' and slope <= 0:
        return None
    elif line_type == 'declining' and slope >= 0:
        return None
    elif line_type == 'horizontal' and abs(slope) > 0.001:
        return None
    
    # Calculate R-squared (goodness of fit)
    mean_price = sum_p / n
    ss_tot = sum((p - mean_price) ** 2 for p in prices)
    ss_res = sum((p - (slope * t + intercept)) ** 2 for p, t in zip(prices, times))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_squared,
        'method': 'regression',
        'touches': n
    }
```

**Method 2: Touch-Optimized (Maximizes Touches)**

```python
def construct_trendline_touch_optimized(swings, line_type):
    """
    Find trendline that maximizes number of touches
    while minimizing average deviation
    
    This often produces better trendlines for triangles
    """
    if len(swings) < 2:
        return None
    
    best_line = None
    best_score = -float('inf')
    
    # Try all possible pairs as anchor points
    for i in range(len(swings)):
        for j in range(i + 1, len(swings)):
            # Calculate line through swings[i] and swings[j]
            slope = (swings[j].price - swings[i].price) / (swings[j].time - swings[i].time)
            intercept = swings[i].price - slope * swings[i].time
            
            # Validate slope direction
            if line_type == 'rising' and slope <= 0:
                continue
            elif line_type == 'declining' and slope >= 0:
                continue
            elif line_type == 'horizontal' and abs(slope) > 0.001:
                continue
            
            # Score this line
            score = score_trendline(swings, slope, intercept)
            
            if score > best_score:
                best_score = score
                best_line = {
                    'slope': slope,
                    'intercept': intercept,
                    'method': 'touch_optimized',
                    'score': score
                }
    
    return best_line

def score_trendline(swings, slope, intercept):
    """
    Score trendline based on touches and deviations
    
    Formula: (touches * 15) - (average_deviation * 100)
    """
    touches = 0
    total_deviation = 0
    tolerance = 0.015  # 1.5% counts as touch
    
    for swing in swings:
        expected_price = slope * swing.time + intercept
        deviation_pct = abs(swing.price - expected_price) / expected_price
        
        if deviation_pct <= tolerance:
            touches += 1
        
        total_deviation += deviation_pct
    
    avg_deviation = total_deviation / len(swings)
    
    # Score heavily rewards touches, penalizes deviations
    score = (touches * 15) - (avg_deviation * 100)
    
    return score
```

**Method 3: Horizontal Line Detection**

```python
def construct_horizontal_line(swings, tolerance=0.02):
    """
    Detect if swings form a horizontal line
    
    Args:
        swings: List of swing points
        tolerance: Maximum % deviation to consider horizontal
    
    Returns:
        Horizontal line dict or None
    """
    if len(swings) < 2:
        return None
    
    # Calculate average price
    prices = [s.price for s in swings]
    avg_price = sum(prices) / len(prices)
    
    # Check if all swings are within tolerance of average
    for price in prices:
        deviation = abs(price - avg_price) / avg_price
        if deviation > tolerance:
            return None  # Not horizontal
    
    # Use extreme (max for resistance, min for support) as level
    # This ensures all prices touch or are inside the line
    return {
        'price': avg_price,
        'type': 'horizontal',
        'touches': len(swings),
        'deviation': max(abs(p - avg_price) / avg_price for p in prices)
    }
```

---

## Pattern Validation

### Comprehensive Triangle Validation

```python
class TriangleValidator:
    """
    Comprehensive validation for all triangle types
    """
    
    def validate_triangle(self, pattern):
        """
        Full validation of triangle pattern
        
        Returns:
            (is_valid, validation_details, quality_score)
        """
        validations = {}
        
        # 1. Minimum swing requirements
        validations['sufficient_swings'] = (
            len(pattern.highs) >= 2 and len(pattern.lows) >= 2
        )
        
        # 2. Trendline validity
        validations['valid_trendlines'] = self.validate_trendlines(pattern)
        
        # 3. Convergence validation
        validations['converging'] = self.validate_convergence(pattern)
        
        # 4. Compression (decreasing volatility)
        validations['compression'] = self.validate_compression(pattern)
        
        # 5. Touch quality (swings touch trendlines)
        validations['touch_quality'] = self.validate_touches(pattern)
        
        # 6. Time validation (not too long/short)
        validations['time_constraints'] = self.validate_timing(pattern)
        
        # 7. Apex distance (not too close/far from apex)
        validations['apex_distance'] = self.validate_apex_distance(pattern)
        
        # 8. Volume pattern (if available)
        if pattern.has_volume_data:
            validations['volume_pattern'] = self.validate_volume(pattern)
        
        # Overall validity
        is_valid = all(validations.values())
        
        # Quality score
        quality_score = self.calculate_quality_score(pattern, validations)
        
        return is_valid, validations, quality_score
    
    def validate_trendlines(self, pattern):
        """
        Validate that trendlines are properly formed
        """
        if pattern.type == 'ascending':
            return (
                pattern.resistance_level is not None and
                pattern.support_trendline is not None and
                pattern.support_trendline['slope'] > 0
            )
        
        elif pattern.type == 'descending':
            return (
                pattern.support_level is not None and
                pattern.resistance_trendline is not None and
                pattern.resistance_trendline['slope'] < 0
            )
        
        elif pattern.type == 'symmetrical':
            return (
                pattern.resistance_trendline is not None and
                pattern.support_trendline is not None and
                pattern.resistance_trendline['slope'] < 0 and
                pattern.support_trendline['slope'] > 0
            )
        
        return False
    
    def validate_convergence(self, pattern):
        """
        Ensure trendlines are actually converging
        """
        if not pattern.apex:
            return False
        
        # Calculate gap at multiple points
        start_time = pattern.get_start_time()
        mid_time = pattern.get_mid_time()
        end_time = pattern.get_end_time()
        
        start_gap = pattern.get_gap_at_time(start_time)
        mid_gap = pattern.get_gap_at_time(mid_time)
        end_gap = pattern.get_gap_at_time(end_time)
        
        # Gaps should be progressively smaller
        if not (start_gap > mid_gap > end_gap):
            return False
        
        # End gap should be significantly smaller than start
        compression_ratio = end_gap / start_gap
        
        if compression_ratio > 0.7:  # Less than 30% compression
            return False
        
        return True
    
    def validate_compression(self, pattern):
        """
        Validate decreasing volatility (compression)
        
        Each swing should be smaller than previous
        """
        # Calculate swing sizes
        swing_sizes = []
        
        for i in range(min(len(pattern.highs), len(pattern.lows))):
            if i < len(pattern.highs) and i < len(pattern.lows):
                size = abs(pattern.highs[i].price - pattern.lows[i].price)
                swing_sizes.append(size)
        
        if len(swing_sizes) < 2:
            return True  # Too early to validate
        
        # Check if swings are generally decreasing
        # Compare first half to second half
        mid_point = len(swing_sizes) // 2
        first_half_avg = sum(swing_sizes[:mid_point]) / max(1, mid_point)
        second_half_avg = sum(swing_sizes[mid_point:]) / max(1, len(swing_sizes) - mid_point)
        
        # Second half should be smaller
        if second_half_avg >= first_half_avg * 0.85:  # Allow 15% tolerance
            return False
        
        return True
    
    def validate_touches(self, pattern):
        """
        Validate that swings properly touch trendlines
        """
        touch_tolerance = 0.02  # 2%
        
        # Count valid touches
        valid_touches = 0
        total_swings = len(pattern.highs) + len(pattern.lows)
        
        # Check highs
        for high in pattern.highs:
            expected = pattern.get_resistance_at_time(high.time)
            if expected:
                deviation = abs(high.price - expected) / expected
                if deviation <= touch_tolerance:
                    valid_touches += 1
        
        # Check lows
        for low in pattern.lows:
            expected = pattern.get_support_at_time(low.time)
            if expected:
                deviation = abs(low.price - expected) / expected
                if deviation <= touch_tolerance:
                    valid_touches += 1
        
        # At least 75% of swings should touch
        touch_ratio = valid_touches / total_swings
        
        return touch_ratio >= 0.75
    
    def validate_timing(self, pattern):
        """
        Pattern shouldn't be too short or too long
        """
        duration = pattern.get_duration()
        
        min_duration = pattern.config['min_triangle_duration']
        max_duration = pattern.config['max_triangle_duration']
        
        if duration < min_duration:
            return False  # Too quick, might be noise
        
        if duration > max_duration:
            return False  # Too long, lost relevance
        
        return True
    
    def validate_apex_distance(self, pattern):
        """
        Pattern should be neither too close nor too far from apex
        
        Ideal: 30-75% of distance to apex
        """
        if not pattern.apex:
            return False
        
        current_time = pattern.get_current_time()
        start_time = pattern.get_start_time()
        apex_time = pattern.apex['time']
        
        total_duration = apex_time - start_time
        current_duration = current_time - start_time
        
        if total_duration <= 0:
            return False
        
        progress = current_duration / total_duration
        
        # Should be between 30% and 80%
        if progress < 0.3:
            return False  # Too early
        
        if progress > 0.8:
            return False  # Too close to apex (should have broken by now)
        
        return True
    
    def validate_volume(self, pattern):
        """
        Ideal volume pattern for triangles:
        - Declining volume during consolidation
        - Increasing volume on breakout
        """
        # Volume should generally decline during pattern
        early_volume = pattern.get_volume_in_range(
            pattern.get_start_time(),
            pattern.get_mid_time()
        )
        
        late_volume = pattern.get_volume_in_range(
            pattern.get_mid_time(),
            pattern.get_end_time()
        )
        
        # Late volume should be lower (consolidation)
        volume_declining = late_volume < early_volume * 0.85
        
        return volume_declining
    
    def calculate_quality_score(self, pattern, validations):
        """
        Calculate 0-1 quality score
        """
        score = 0
        
        # Trendline quality (30 points)
        trendline_quality = self.calculate_trendline_quality(pattern)
        score += trendline_quality * 30
        
        # Touch quality (25 points)
        touch_quality = self.calculate_touch_quality(pattern)
        score += touch_quality * 25
        
        # Compression quality (20 points)
        if validations.get('compression', False):
            compression_quality = self.calculate_compression_quality(pattern)
            score += compression_quality * 20
        
        # Convergence quality (15 points)
        if validations.get('converging', False):
            convergence_quality = self.calculate_convergence_quality(pattern)
            score += convergence_quality * 15
        
        # Volume quality (10 points)
        if pattern.has_volume_data and validations.get('volume_pattern', False):
            score += 10
        elif not pattern.has_volume_data:
            score += 5  # Partial credit
        
        return score / 100
    
    def calculate_trendline_quality(self, pattern):
        """
        Score trendline fit quality (0-1)
        
        Based on R-squared if using regression
        Or based on touch count if using touch method
        """
        if hasattr(pattern.resistance_trendline, 'r_squared'):
            resistance_quality = pattern.resistance_trendline['r_squared']
        else:
            resistance_touches = pattern.resistance_trendline.get('touches', 0)
            resistance_quality = min(1.0, resistance_touches / 4)  # 4+ touches = perfect
        
        if hasattr(pattern.support_trendline, 'r_squared'):
            support_quality = pattern.support_trendline['r_squared']
        elif pattern.support_level:  # Horizontal support
            support_touches = pattern.support_level.get('touches', 0)
            support_quality = min(1.0, support_touches / 4)
        else:
            support_touches = pattern.support_trendline.get('touches', 0)
            support_quality = min(1.0, support_touches / 4)
        
        return (resistance_quality + support_quality) / 2
```

---

## Breakout Detection

### Triangle Breakout Logic

```python
class TriangleBreakoutDetector:
    """
    Detect and confirm breakouts from triangle patterns
    """
    
    def detect_breakout(self, pattern, current_price, current_time):
        """
        Detect breakout from triangle
        
        Triangle can break upward or downward
        Pattern type suggests direction but both are possible
        """
        if pattern.status != "complete":
            return False, None
        
        # Get resistance and support prices at current time
        resistance_price = pattern.get_resistance_at_time(current_time)
        support_price = pattern.get_support_at_time(current_time)
        
        # Check for upward breakout
        if current_price > resistance_price:
            return self.process_upward_breakout(
                pattern, current_price, current_time, resistance_price
            )
        
        # Check for downward breakout
        elif current_price < support_price:
            return self.process_downward_breakout(
                pattern, current_price, current_time, support_price
            )
        
        return False, None
    
    def process_upward_breakout(self, pattern, price, time, resistance):
        """
        Process potential upward breakout
        """
        if not pattern.upward_break_started:
            pattern.upward_break_started = True
            pattern.break_start_time = time
            pattern.break_start_price = price
            pattern.break_direction = "upward"
            return False, "upward_break_started"
        
        # Check for confirmation
        confirmations = self.check_breakout_confirmations(
            pattern, price, time, resistance, "upward"
        )
        
        if confirmations >= pattern.config['confirmations_required']:
            pattern.break_confirmed = True
            pattern.status = "broken_upward"
            return True, "upward"
        
        return False, "awaiting_confirmation"
    
    def process_downward_breakout(self, pattern, price, time, support):
        """
        Process potential downward breakout
        """
        if not pattern.downward_break_started:
            pattern.downward_break_started = True
            pattern.break_start_time = time
            pattern.break_start_price = price
            pattern.break_direction = "downward"
            return False, "downward_break_started"
        
        # Check for confirmation
        confirmations = self.check_breakout_confirmations(
            pattern, price, time, support, "downward"
        )
        
        if confirmations >= pattern.config['confirmations_required']:
            pattern.break_confirmed = True
            pattern.status = "broken_downward"
            return True, "downward"
        
        return False, "awaiting_confirmation"
    
    def check_breakout_confirmations(self, pattern, price, time, boundary, direction):
        """
        Check multiple confirmation criteria
        
        Returns count of confirmations met
        """
        confirmations = 0
        
        # 1. Close beyond boundary
        if direction == "upward" and price > boundary:
            confirmations += 1
        elif direction == "downward" and price < boundary:
            confirmations += 1
        
        # 2. Percentage breakout (clear break)
        if direction == "upward":
            breakout_distance = price - boundary
            breakout_pct = breakout_distance / boundary
        else:
            breakout_distance = boundary - price
            breakout_pct = breakout_distance / boundary
        
        if breakout_pct >= 0.02:  # 2% beyond boundary
            confirmations += 1
        
        # 3. Time confirmation (sustained)
        bars_since_break = time - pattern.break_start_time
        
        if bars_since_break >= 2:  # 2+ bars beyond
            confirmations += 1
        
        # 4. Volume confirmation (if available)
        if pattern.has_volume_data:
            breakout_volume = pattern.get_current_volume()
            avg_triangle_volume = pattern.get_average_volume()
            
            if breakout_volume > avg_triangle_volume * 1.5:
                confirmations += 1
        
        return confirmations
```

### Breakout Direction Bias

```python
def calculate_breakout_bias(pattern):
    """
    Calculate which direction pattern is likely to break
    
    Returns:
        ('upward', confidence) or ('downward', confidence) or ('neutral', 0)
    """
    # Ascending triangle: Bullish bias (70% break upward)
    if pattern.type == 'ascending':
        return 'upward', 0.70
    
    # Descending triangle: Bearish bias (70% break downward)
    elif pattern.type == 'descending':
        return 'downward', 0.70
    
    # Symmetrical triangle: Check context
    elif pattern.type == 'symmetrical':
        # Check prior trend
        trend_before = pattern.get_trend_before_pattern()
        
        if trend_before == 'uptrend':
            return 'upward', 0.60  # Continuation bias
        elif trend_before == 'downtrend':
            return 'downward', 0.60  # Continuation bias
        else:
            return 'neutral', 0.50  # No bias
    
    return 'neutral', 0.50
```

---

## Measured Move Targets

### Target Calculation Methods

```python
def calculate_triangle_targets(pattern, breakout_direction):
    """
    Calculate price targets for triangle breakout
    
    Method: Measure triangle height at base, project from breakout
    """
    # Find triangle height (widest point, usually at start)
    triangle_height = pattern.get_triangle_height_at_base()
    
    # Get breakout price
    breakout_price = pattern.break_start_price
    
    if breakout_direction == "upward":
        # Project height upward
        primary_target = breakout_price + triangle_height
        conservative_target = breakout_price + (triangle_height * 0.5)
        extended_target = breakout_price + (triangle_height * 1.5)
    
    else:  # downward
        # Project height downward
        primary_target = breakout_price - triangle_height
        conservative_target = breakout_price - (triangle_height * 0.5)
        extended_target = breakout_price - (triangle_height * 1.5)
    
    return {
        'primary': primary_target,
        'conservative': conservative_target,
        'extended': extended_target,
        'triangle_height': triangle_height,
        'breakout_price': breakout_price
    }

def get_triangle_height_at_base(self):
    """
    Calculate triangle height at widest point (base)
    
    For most triangles, this is near the start
    """
    # Get prices at start of pattern
    start_time = self.get_start_time()
    
    resistance_at_start = self.get_resistance_at_time(start_time)
    support_at_start = self.get_support_at_time(start_time)
    
    height = resistance_at_start - support_at_start
    
    return height
```

### Alternative Target Method: Apex Projection

```python
def calculate_apex_based_targets(pattern, breakout_direction):
    """
    Alternative method: Project from apex
    
    Some traders use apex as starting point for projection
    """
    if not pattern.apex:
        return None
    
    apex_price = pattern.apex['price']
    breakout_price = pattern.break_start_price
    
    # Distance from apex to breakout
    breakout_distance = abs(breakout_price - apex_price)
    
    if breakout_direction == "upward":
        target = breakout_price + breakout_distance
    else:
        target = breakout_price - breakout_distance
    
    return {
        'apex_based_target': target,
        'method': 'apex_projection'
    }
```

---

## Pattern Invalidation

### Triangle Invalidation Scenarios

```python
class TriangleInvalidation:
    """
    Detect triangle pattern invalidation
    """
    
    def check_invalidation(self, pattern, current_price, current_time):
        """
        Check if pattern is invalidated
        
        Returns:
            (is_invalidated, invalidation_reason)
        """
        # 1. Reached apex without breaking
        if self.check_apex_reached(pattern, current_time):
            return True, "reached_apex_without_break"
        
        # 2. Exceeded max duration
        if self.check_max_duration_exceeded(pattern, current_time):
            return True, "pattern_too_long"
        
        # 3. Broke opposite trendline during formation
        if self.check_wrong_line_broken(pattern, current_price, current_time):
            return True, "broke_wrong_trendline"
        
        # 4. Failed breakout (returned inside triangle)
        if self.check_failed_breakout(pattern, current_price, current_time):
            return True, "failed_breakout"
        
        # 5. Trendline invalidated (new swing doesn't fit)
        if self.check_trendline_invalidation(pattern):
            return True, "trendline_broken"
        
        # 6. Expansion instead of compression
        if self.check_expansion(pattern):
            return True, "volatility_expanding"
        
        return False, None
    
    def check_apex_reached(self, pattern, current_time):
        """
        Pattern invalid if price reaches apex without breaking
        """
        if not pattern.apex:
            return False
        
        apex_time = pattern.apex['time']
        
        # If current time past apex time
        if current_time >= apex_time * 0.95:  # 95% to apex
            if pattern.status == "complete":  # Not broken yet
                return True
        
        return False
    
    def check_max_duration_exceeded(self, pattern, current_time):
        """
        Pattern loses relevance if too long
        """
        start_time = pattern.get_start_time()
        duration = current_time - start_time
        
        max_duration = pattern.config['max_triangle_duration']
        
        return duration > max_duration
    
    def check_wrong_line_broken(self, pattern, price, time):
        """
        During formation, if price breaks opposite expected direction
        
        For ascending triangle: Breaking support invalidates
        For descending triangle: Breaking resistance invalidates
        """
        if pattern.status != "forming":
            return False
        
        resistance = pattern.get_resistance_at_time(time)
        support = pattern.get_support_at_time(time)
        
        if pattern.type == 'ascending':
            # Support should hold during formation
            if price < support * 0.98:  # 2% below support
                return True
        
        elif pattern.type == 'descending':
            # Resistance should hold during formation
            if price > resistance * 1.02:  # 2% above resistance
                return True
        
        # Symmetrical can break either way
        
        return False
    
    def check_failed_breakout(self, pattern, price, time):
        """
        After breaking out, price should continue
        If it returns inside triangle, breakout failed
        """
        if pattern.status not in ["broken_upward", "broken_downward"]:
            return False
        
        resistance = pattern.get_resistance_at_time(time)
        support = pattern.get_support_at_time(time)
        
        # Price returned inside triangle
        if support < price < resistance:
            return True
        
        # If broke upward but now below support
        if pattern.status == "broken_upward" and price < support:
            return True
        
        # If broke downward but now above resistance
        if pattern.status == "broken_downward" and price > resistance:
            return True
        
        return False
    
    def check_trendline_invalidation(self, pattern):
        """
        New swing points don't fit established trendlines
        """
        if pattern.status != "forming":
            return False
        
        # For ascending triangle
        if pattern.type == 'ascending':
            # Check if latest low is lower than previous
            if len(pattern.lows) >= 2:
                if pattern.lows[-1].price < pattern.lows[-2].price:
                    return True  # Support not rising anymore
        
        # For descending triangle
        elif pattern.type == 'descending':
            # Check if latest high is higher than previous
            if len(pattern.highs) >= 2:
                if pattern.highs[-1].price > pattern.highs[-2].price:
                    return True  # Resistance not declining anymore
        
        # For symmetrical triangle
        elif pattern.type == 'symmetrical':
            # Check highs still declining and lows still rising
            if len(pattern.highs) >= 2:
                if pattern.highs[-1].price >= pattern.highs[-2].price:
                    return True
            
            if len(pattern.lows) >= 2:
                if pattern.lows[-1].price <= pattern.lows[-2].price:
                    return True
        
        return False
    
    def check_expansion(self, pattern):
        """
        Triangle should show compression
        If volatility is expanding instead, pattern invalid
        """
        if len(pattern.highs) < 3 or len(pattern.lows) < 3:
            return False
        
        # Calculate recent swing size vs earlier swing size
        recent_swings = []
        for i in range(max(len(pattern.highs) - 2, 0), len(pattern.highs)):
            if i < len(pattern.lows):
                swing = abs(pattern.highs[i].price - pattern.lows[i].price)
                recent_swings.append(swing)
        
        early_swings = []
        for i in range(min(2, len(pattern.highs))):
            if i < len(pattern.lows):
                swing = abs(pattern.highs[i].price - pattern.lows[i].price)
                early_swings.append(swing)
        
        if recent_swings and early_swings:
            recent_avg = sum(recent_swings) / len(recent_swings)
            early_avg = sum(early_swings) / len(early_swings)
            
            # Recent swings should be smaller
            if recent_avg > early_avg * 1.1:  # 10% larger
                return True  # Expanding, not compressing
        
        return False
```

### Invalidation Details by Type

**Ascending Triangle Invalidation:**

```python
# 1. Support breaks during formation
if price < rising_support * 0.98:
    status = "INVALIDATED - support broken"
    # Now likely continuation downward or range

# 2. Highs start rising instead of staying flat
if new_high > resistance * 1.03:
    status = "INVALIDATED - resistance broken upward during formation"
    # Might be breakaway move, not triangle

# 3. Lows stop rising (go sideways or down)
if new_low <= previous_low:
    status = "INVALIDATED - support not rising"
    # Becoming rectangle or descending triangle
```

**Why these invalidate:**
- **Support break**: Pattern structure destroyed, bullish bias lost
- **Rising resistance**: No longer a triangle, may be upward continuation
- **Lows not rising**: Pattern morphing into different structure

**Descending Triangle Invalidation:**

```python
# 1. Resistance breaks during formation
if price > declining_resistance * 1.02:
    status = "INVALIDATED - resistance broken"
    # Now likely continuation upward or range

# 2. Lows start falling instead of staying flat
if new_low < support * 0.97:
    status = "INVALIDATED - support broken downward during formation"
    # Might be breakdown, not triangle

# 3. Highs stop declining (go sideways or up)
if new_high >= previous_high:
    status = "INVALIDATED - resistance not declining"
    # Becoming rectangle or ascending triangle
```

**Why these invalidate:**
- **Resistance break**: Pattern structure destroyed, bearish bias lost
- **Falling support**: No longer a triangle, may be downward continuation
- **Highs not declining**: Pattern morphing into different structure

**Symmetrical Triangle Invalidation:**

```python
# 1. Highs stop declining
if new_high >= previous_high:
    status = "INVALIDATED - resistance not declining"

# 2. Lows stop rising
if new_low <= previous_low:
    status = "INVALIDATED - support not rising"

# 3. Either line breaks during formation
# (Less critical than other types since direction ambiguous)
```

**Why these invalidate:**
- **Highs/lows stop converging**: Loses triangle structure
- **Becomes ranging**: No longer compression pattern

**Common to All Types:**

```python
# 1. Apex reached without breakout
if current_time >= apex_time:
    status = "INVALIDATED - reached apex"
    # Pattern expired, lost coiling energy

# 2. Pattern too long
if duration > max_duration:
    status = "INVALIDATED - too extended"
    # Market conditions changed, pattern stale

# 3. Failed breakout
if broke_out_but_returned_inside:
    status = "INVALIDATED - failed breakout"
    # False signal, often leads to opposite move

# 4. Volatility expanding
if recent_swings > early_swings:
    status = "INVALIDATED - expansion not compression"
    # Should compress toward apex, not expand
```

**Trading Implications of Invalidations:**

1. **Failed upward breakout from ascending triangle** → Often strong bearish signal
2. **Failed downward breakout from descending triangle** → Often strong bullish signal
3. **Support break in ascending triangle during formation** → Turn bearish
4. **Resistance break in descending triangle during formation** → Turn bullish
5. **Apex reached** → Pattern neutral, wait for new structure

---

## Configuration Parameters

### Recommended Starting Values

```python
TRIANGLE_PATTERN_CONFIG = {
    # Swing Requirements
    'min_highs': 2,                      # Minimum swing highs needed
    'min_lows': 2,                       # Minimum swing lows needed
    'ideal_highs': 3,                    # Ideal number of highs
    'ideal_lows': 3,                     # Ideal number of lows
    
    # Trendline Requirements
    'touch_tolerance': 0.02,             # 2% deviation counts as touch
    'horizontal_tolerance': 0.02,        # 2% for horizontal line
    'min_trendline_r_squared': 0.85,     # If using regression
    
    # Triangle Structure
    'min_compression_ratio': 0.30,       # End gap / start gap < 0.7
    'max_slope_asymmetry': 0.50,         # For symmetrical triangles
    'min_triangle_height_pct': 0.03,     # 3% minimum height
    
    # Timing Requirements
    'min_triangle_duration': 10,         # Minimum bars
    'max_triangle_duration': 100,        # Maximum bars
    'min_apex_progress': 0.30,           # 30% to apex minimum
    'max_apex_progress': 0.80,           # 80% to apex maximum
    
    # Breakout Requirements
    'breakout_percentage': 0.02,         # 2% beyond trendline
    'breakout_time_bars': 2,             # Bars sustained
    'breakout_volume_multiplier': 1.5,   # Volume vs average
    'confirmations_required': 2,         # Confirmations needed
    
    # Quality Scoring Weights
    'weight_trendline_fit': 0.30,
    'weight_touch_quality': 0.25,
    'weight_compression': 0.20,
    'weight_convergence': 0.15,
    'weight_volume': 0.10,
    
    # Context
    'min_quality_score': 0.60,           # Minimum to consider valid
}
```

### Timeframe Adjustments

```python
def adjust_for_timeframe(base_config, timeframe):
    """
    Scale parameters for different timeframes
    """
    config = base_config.copy()
    
    multipliers = {
        '1m': 0.4,
        '5m': 0.6,
        '15m': 1.0,  # baseline
        '1h': 1.4,
        '4h': 2.0,
        '1d': 3.0,
    }
    
    m = multipliers.get(timeframe, 1.0)
    
    # Scale time-based parameters
    config['min_triangle_duration'] = int(config['min_triangle_duration'] * m)
    config['max_triangle_duration'] = int(config['max_triangle_duration'] * m)
    config['breakout_time_bars'] = int(config['breakout_time_bars'] * m)
    
    return config
```

### Market-Specific Adjustments

```python
def adjust_for_market(base_config, market_type):
    """
    Adjust parameters based on market characteristics
    """
    config = base_config.copy()
    
    if market_type == 'crypto':
        # Crypto more volatile
        config['touch_tolerance'] = 0.03           # 3% tolerance
        config['horizontal_tolerance'] = 0.03      # 3% for horizontal
        config['min_triangle_height_pct'] = 0.05   # 5% minimum height
        config['breakout_percentage'] = 0.03       # 3% breakout
        
    elif market_type == 'forex':
        # Forex less volatile
        config['touch_tolerance'] = 0.015          # 1.5% tolerance
        config['horizontal_tolerance'] = 0.015     # 1.5% for horizontal
        config['min_triangle_height_pct'] = 0.02   # 2% minimum height
        config['breakout_percentage'] = 0.015      # 1.5% breakout
        
    elif market_type == 'stocks':
        # Moderate volatility
        config['touch_tolerance'] = 0.02           # 2% tolerance (baseline)
        
    return config
```

---

## Implementation Architecture

### Unified Triangle Detector

```python
class TrianglePatternDetector:
    """
    Unified detector for all triangle types
    """
    
    def __init__(self, swing_points, config):
        self.swing_points = swing_points
        self.config = config
        self.active_patterns = []
        self.completed_patterns = []
        self.broken_patterns = []
        self.failed_patterns = []
    
    def scan_for_patterns(self):
        """
        Scan swing points for all triangle types
        """
        for i in range(4, len(self.swing_points)):
            # Try to detect each type
            ascending = self.detect_ascending_triangle(i)
            if ascending:
                self.active_patterns.append(ascending)
            
            descending = self.detect_descending_triangle(i)
            if descending:
                self.active_patterns.append(descending)
            
            symmetrical = self.detect_symmetrical_triangle(i)
            if symmetrical:
                self.active_patterns.append(symmetrical)
        
        # Remove duplicates/overlaps
        self.deduplicate_patterns()
    
    def detect_ascending_triangle(self, end_index):
        """
        Attempt to construct ascending triangle ending at index
        """
        # Collect swings in window
        window_size = 10  # Look back 10 swings
        start_index = max(0, end_index - window_size)
        window_swings = self.swing_points[start_index:end_index+1]
        
        # Separate highs and lows
        highs = [s for s in window_swings if s.type == "high"]
        lows = [s for s in window_swings if s.type == "low"]
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        # Try to construct pattern
        pattern = AscendingTrianglePattern()
        
        for swing in window_swings:
            pattern.add_swing(swing)
        
        # Validate
        if pattern.status == "complete":
            is_valid, validations, quality = self.validate_pattern(pattern)
            
            if is_valid and quality >= self.config['min_quality_score']:
                pattern.quality_score = quality
                return pattern
        
        return None
    
    def detect_descending_triangle(self, end_index):
        """
        Attempt to construct descending triangle ending at index
        """
        window_size = 10
        start_index = max(0, end_index - window_size)
        window_swings = self.swing_points[start_index:end_index+1]
        
        highs = [s for s in window_swings if s.type == "high"]
        lows = [s for s in window_swings if s.type == "low"]
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        pattern = DescendingTrianglePattern()
        
        for swing in window_swings:
            pattern.add_swing(swing)
        
        if pattern.status == "complete":
            is_valid, validations, quality = self.validate_pattern(pattern)
            
            if is_valid and quality >= self.config['min_quality_score']:
                pattern.quality_score = quality
                return pattern
        
        return None
    
    def detect_symmetrical_triangle(self, end_index):
        """
        Attempt to construct symmetrical triangle ending at index
        """
        window_size = 10
        start_index = max(0, end_index - window_size)
        window_swings = self.swing_points[start_index:end_index+1]
        
        highs = [s for s in window_swings if s.type == "high"]
        lows = [s for s in window_swings if s.type == "low"]
        
        if len(highs) < 2 or len(lows) < 2:
            return None
        
        pattern = SymmetricalTrianglePattern()
        
        for swing in window_swings:
            pattern.add_swing(swing)
        
        if pattern.status == "complete":
            is_valid, validations, quality = self.validate_pattern(pattern)
            
            if is_valid and quality >= self.config['min_quality_score']:
                pattern.quality_score = quality
                return pattern
        
        return None
    
    def update_with_new_swing(self, new_swing):
        """
        Update active patterns with new swing
        """
        for pattern in self.active_patterns[:]:
            pattern.update(new_swing)
            
            if pattern.status == "complete":
                self.completed_patterns.append(pattern)
                self.active_patterns.remove(pattern)
            
            elif pattern.status.startswith("failed"):
                self.failed_patterns.append(pattern)
                self.active_patterns.remove(pattern)
    
    def update_with_price(self, current_price, current_time):
        """
        Update completed patterns for breakout detection
        """
        for pattern in self.completed_patterns[:]:
            broken, direction = pattern.detect_breakout(current_price, current_time)
            
            if broken:
                self.broken_patterns.append(pattern)
                self.completed_patterns.remove(pattern)
            
            # Check invalidation
            invalid, reason = pattern.check_invalidation(current_price, current_time)
            if invalid:
                pattern.invalidation_reason = reason
                self.failed_patterns.append(pattern)
                self.completed_patterns.remove(pattern)
    
    def deduplicate_patterns(self):
        """
        Remove overlapping patterns
        Keep highest quality pattern when multiple overlap
        """
        # Group patterns by time overlap
        groups = self.group_overlapping_patterns()
        
        # Keep only best from each group
        self.active_patterns = [
            max(group, key=lambda p: p.quality_score)
            for group in groups
        ]
    
    def group_overlapping_patterns(self):
        """
        Group patterns that overlap in time
        """
        groups = []
        used = set()
        
        for i, pattern1 in enumerate(self.active_patterns):
            if i in used:
                continue
                
            group = [pattern1]
            used.add(i)
            
            for j, pattern2 in enumerate(self.active_patterns):
                if j in used or i == j:
                    continue
                
                if self.patterns_overlap(pattern1, pattern2):
                    group.append(pattern2)
                    used.add(j)
            
            groups.append(group)
        
        return groups
    
    def patterns_overlap(self, pattern1, pattern2):
        """
        Check if two patterns overlap in time
        """
        start1 = pattern1.get_start_time()
        end1 = pattern1.get_end_time()
        start2 = pattern2.get_start_time()
        end2 = pattern2.get_end_time()
        
        # Check for overlap
        return not (end1 < start2 or end2 < start1)
```

### Integration Example

```python
# Initialize with swing points
swing_detector = SwingPointDetector(price_data, strength=5)
swings = swing_detector.detect_swings()

# Initialize triangle detector
triangle_detector = TrianglePatternDetector(swings, TRIANGLE_PATTERN_CONFIG)

# Scan for patterns
triangle_detector.scan_for_patterns()

# Real-time updates
def on_new_swing(swing):
    triangle_detector.update_with_new_swing(swing)

def on_price_update(price, time):
    triangle_detector.update_with_price(price, time)

# Query patterns
active = triangle_detector.active_patterns
completed = triangle_detector.completed_patterns
broken = triangle_detector.broken_patterns
```

---

## Summary

This comprehensive guide provides complete triangle pattern detection logic for:

**Pattern Types:**
- Ascending triangles (bullish bias)
- Descending triangles (bearish bias)
- Symmetrical triangles (neutral, continuation)

**Key Features:**
- Swing-point-based detection
- Progressive formation tracking
- Multiple trendline construction methods
- Comprehensive validation (structure, compression, convergence, touches)
- Quality scoring system
- Breakout detection with multiple confirmations
- Measured move target calculation
- Detailed invalidation rules

**Critical Success Factors:**
1. Proper trendline fitting (regression or touch-based)
2. Convergence validation (lines must meet at apex)
3. Compression validation (decreasing volatility)
4. Apex timing (break before reaching apex)
5. Touch quality (swings must respect boundaries)
6. Breakout confirmation (multiple criteria)

The system is designed to integrate with your existing swing point infrastructure and can be combined with H&S and flag pattern detection for a comprehensive pattern recognition system.

---

## Implementation Checklist

### Core Components
- [ ] Swing point collector for triangles
- [ ] Horizontal line detection (for ascending/descending)
- [ ] Rising trendline construction (for ascending/symmetrical)
- [ ] Declining trendline construction (for descending/symmetrical)
- [ ] Apex calculation (intersection point)
- [ ] Convergence validation
- [ ] Compression validation
- [ ] Touch quality validation

### Pattern-Specific Detection
- [ ] Ascending triangle detector
- [ ] Descending triangle detector
- [ ] Symmetrical triangle detector
- [ ] Pattern type identification

### Validation & Quality
- [ ] Comprehensive validation system
- [ ] Quality scoring algorithm
- [ ] Timeframe adjustments
- [ ] Market-specific adjustments

### Breakout & Targets
- [ ] Upward breakout detection
- [ ] Downward breakout detection
- [ ] Multiple confirmation system
- [ ] Measured move calculation
- [ ] Apex-based target (alternative)

### Invalidation
- [ ] Apex reached without break
- [ ] Duration exceeded
- [ ] Wrong trendline broken
- [ ] Failed breakout detection
- [ ] Trendline invalidation
- [ ] Expansion detection

### Integration
- [ ] Unified triangle detector
- [ ] Real-time swing updates
- [ ] Real-time price updates
- [ ] Pattern deduplication
- [ ] Overlap detection

