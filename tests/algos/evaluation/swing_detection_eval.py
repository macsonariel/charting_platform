"""
Improved Swing Detection Evaluation
Fixed version addressing all identified logic flaws

This module takes swings from swing_detection and adds quality scores based on:
- Dominance: How much higher/lower the swing is compared to surrounding candles
- Volume: Higher volume at swing point = higher quality, with absorption detection
- Momentum: Stronger momentum reaction after swing = higher quality
- Key Level Proximity: Closer to key levels = higher quality
- Clarity: Weighted by candle size and cleanliness
- Structure: Based on swing's own properties (no forward bias)
"""

from typing import Dict, List, Optional, Any, Tuple
import math
from testing.algos.swing_scanner import detect_swing_structure
from testing.algos.volatility_scanner import average_true_range
from testing.algos.momentum_scanner import calculate_momentum
from testing.algos.key_levels_scanner import detect_key_levels, KeyLevelsConfig


class AdaptiveWindows:
    """
    Adaptive time windows based on timeframe and volatility
    """
    
    TIMEFRAME_MULTIPLIERS = {
        '1m': 0.5, '3m': 0.6, '5m': 0.7, '15m': 1.0,
        '30m': 1.2, '1h': 1.5, '2h': 1.7, '4h': 2.0,
        '6h': 2.5, '12h': 3.0, '1d': 3.5, '1w': 5.0
    }
    
    VOLATILITY_MULTIPLIERS = {
        'compression': 0.8,
        'normal': 1.0,
        'expansion': 1.3
    }
    
    def __init__(self, timeframe: str, volatility_regime: str = 'normal'):
        self.timeframe = timeframe
        self.volatility_regime = volatility_regime
        self.multiplier = self._calculate_multiplier()
    
    def _calculate_multiplier(self) -> float:
        """Calculate combined multiplier"""
        tf_mult = self.TIMEFRAME_MULTIPLIERS.get(self.timeframe, 1.0)
        vol_mult = self.VOLATILITY_MULTIPLIERS.get(self.volatility_regime, 1.0)
        return tf_mult * vol_mult
    
    def get_immediate_reaction_window(self) -> int:
        """Immediate reaction window (default 4 candles)"""
        return max(2, int(4 * self.multiplier))
    
    def get_expanding_start(self) -> int:
        """Start of expanding window (default 5 candles)"""
        return max(3, int(5 * self.multiplier))
    
    def get_expanding_end(self) -> int:
        """End of expanding window (default 10 candles)"""
        return max(5, int(10 * self.multiplier))
    
    def get_clarity_window(self) -> int:
        """Clarity analysis window (default 5 candles)"""
        return max(3, int(5 * self.multiplier))


def calculate_adaptive_sigmoid(ratio: float, context: str = 'moderate') -> float:
    """
    Adaptive sigmoid function for reaction strength calculation
    
    Args:
        ratio: The ratio to convert to 0-1 score (e.g., post/pre volume)
        context: 'gentle', 'moderate', 'steep', or 'extreme'
    
    Returns:
        Score from 0.0 to 1.0
    """
    k_values = {
        'gentle': 2.0,      # More spread out
        'moderate': 3.0,    # Standard
        'steep': 4.5,       # More sensitive
        'extreme': 6.0      # Very sensitive
    }
    
    k = k_values.get(context, 3.0)
    base_ratio = ratio - 1.0  # Center at 0
    
    # Standard sigmoid
    score = 1.0 / (1.0 + math.exp(-k * base_ratio))
    
    # For extreme values (ratio > 3.0), add linear bonus
    if ratio > 3.0:
        excess = ratio - 3.0
        bonus = min(0.05, excess * 0.01)  # Cap at +5%
        score = min(1.0, score + bonus)
    
    return max(0.0, min(1.0, score))


def calculate_volume_reaction_enhanced(
    swing_index: int,
    chart_data: Dict,
    swing_type: str,
    windows: AdaptiveWindows
) -> Dict[str, float]:
    """
    FIXED: Enhanced volume reaction with absorption detection
    
    Now considers opposing volume (absorption/rejection patterns)
    """
    volumes = chart_data.get("volume", [])
    opens = chart_data.get("open", [])
    closes = chart_data.get("close", [])
    
    if not volumes or swing_index < 0 or swing_index >= len(volumes):
        return {'score': 0.5, 'absorption_detected': False}
    
    window = windows.get_immediate_reaction_window()
    
    # Pre-swing volumes
    pre_start = max(0, swing_index - window)
    pre_volumes = [v for v in volumes[pre_start:swing_index] if v > 0]
    
    if not pre_volumes:
        return {'score': 0.5, 'absorption_detected': False}
    
    pre_avg = sum(pre_volumes) / len(pre_volumes)
    
    # Post-swing volumes (split by direction)
    post_start = swing_index + 1
    post_end = min(len(volumes), swing_index + 1 + window)
    
    supporting_volumes = []  # Volume in expected direction
    testing_volumes = []     # Volume in opposite direction
    
    for i in range(post_start, post_end):
        if i >= len(volumes) or volumes[i] <= 0:
            continue
        
        if i >= len(opens) or i >= len(closes):
            continue
        
        is_bullish_candle = closes[i] > opens[i]
        
        if swing_type == "low":
            # Swing low expects bullish follow-through
            if is_bullish_candle:
                supporting_volumes.append(volumes[i])
            else:
                testing_volumes.append(volumes[i])  # Bears testing the low
        else:  # high
            # Swing high expects bearish follow-through
            if not is_bullish_candle:
                supporting_volumes.append(volumes[i])
            else:
                testing_volumes.append(volumes[i])  # Bulls testing the high
    
    if not supporting_volumes and not testing_volumes:
        return {'score': 0.5, 'absorption_detected': False}
    
    # Calculate total volume
    total_post_volume = sum(supporting_volumes) + sum(testing_volumes)
    supporting_avg = sum(supporting_volumes) / len(supporting_volumes) if supporting_volumes else 0
    testing_avg = sum(testing_volumes) / len(testing_volumes) if testing_volumes else 0
    
    # Check for absorption pattern
    # High testing volume but price holds = strong level (absorption)
    absorption_detected = False
    absorption_bonus = 0.0
    
    if testing_volumes and supporting_volumes:
        testing_total = sum(testing_volumes)
        supporting_total = sum(supporting_volumes)
        
        # If testing volume is significant but swing held
        if testing_total > supporting_total * 0.5:
            # Check if swing price held
            swing_price = chart_data['close'][swing_index] if swing_index < len(chart_data.get('close', [])) else None
            if swing_price is not None:
                post_prices = chart_data['close'][post_start:post_end] if post_start < len(chart_data.get('close', [])) else []
                
                if swing_type == "low":
                    # Low held if no closes significantly below it
                    held = all(p >= swing_price * 0.995 for p in post_prices) if post_prices else False
                else:
                    # High held if no closes significantly above it
                    held = all(p <= swing_price * 1.005 for p in post_prices) if post_prices else False
                
                if held:
                    absorption_detected = True
                    # Bonus proportional to testing volume
                    test_ratio = testing_total / (testing_total + supporting_total)
                    absorption_bonus = test_ratio * 0.2  # Up to +20%
    
    # Calculate base reaction strength using combined volume
    if pre_avg > 0:
        volume_ratio = total_post_volume / (pre_avg * window)
        base_score = calculate_adaptive_sigmoid(volume_ratio, 'moderate')
    else:
        base_score = 0.5
    
    # Apply absorption bonus
    final_score = min(1.0, base_score + absorption_bonus)
    
    return {
        'score': final_score,
        'absorption_detected': absorption_detected,
        'supporting_volume': supporting_avg,
        'testing_volume': testing_avg,
        'absorption_bonus': absorption_bonus
    }


def calculate_clarity_weighted(
    swing: Dict,
    swing_index: int,
    chart_data: Dict,
    windows: AdaptiveWindows
) -> Dict[str, float]:
    """
    FIXED: Weighted clarity score considering candle size and cleanliness
    
    No longer just counts direction - weighs by candle significance
    """
    opens = chart_data.get("open", [])
    closes = chart_data.get("close", [])
    highs = chart_data.get("high", [])
    lows = chart_data.get("low", [])
    
    if swing_index < 0 or not opens or not closes:
        return {'score': 0.5, 'breakdown': {}}
    
    swing_type = swing.get("type", "")
    is_bullish_swing = (swing_type == "low")
    
    window = windows.get_clarity_window()
    start_idx = swing_index + 1
    end_idx = min(start_idx + window, len(closes))
    
    if start_idx >= len(closes):
        return {'score': 0.5, 'breakdown': {}}
    
    total_weight = 0
    agreeing_weight = 0
    candle_details = []
    
    for i in range(start_idx, end_idx):
        if i >= len(opens) or i >= len(closes) or i >= len(highs) or i >= len(lows):
            continue
            
        candle_open = opens[i]
        candle_close = closes[i]
        candle_high = highs[i]
        candle_low = lows[i]
        
        if None in [candle_open, candle_close, candle_high, candle_low]:
            continue
        
        # Candle body size (bigger = more important)
        body_size = abs(candle_close - candle_open)
        
        # Total candle range
        total_range = candle_high - candle_low
        if total_range == 0:
            continue
        
        # Candle direction
        is_bullish = candle_close > candle_open
        
        # Body-to-range ratio (cleaner move = higher ratio)
        body_ratio = body_size / total_range
        
        # Clean factor: combines body size and body ratio
        # Large bodies with small wicks = very clean
        clean_factor = body_ratio ** 0.5  # Square root to reduce penalty
        
        # Weight by body size and cleanliness
        candle_weight = body_size * (0.3 + 0.7 * clean_factor)
        total_weight += candle_weight
        
        # Check if direction agrees
        direction_agrees = (is_bullish_swing and is_bullish) or \
                          (not is_bullish_swing and not is_bullish)
        
        if direction_agrees:
            agreeing_weight += candle_weight
        
        candle_details.append({
            'index': i,
            'body_size': body_size,
            'body_ratio': body_ratio,
            'clean_factor': clean_factor,
            'weight': candle_weight,
            'agrees': direction_agrees
        })
    
    if total_weight == 0:
        return {'score': 0.5, 'breakdown': {}}
    
    clarity_score = agreeing_weight / total_weight
    
    return {
        'score': clarity_score,
        'breakdown': {
            'total_candles': len(candle_details),
            'avg_body_ratio': sum(c['body_ratio'] for c in candle_details) / len(candle_details) if candle_details else 0,
            'agreeing_candles': sum(1 for c in candle_details if c['agrees'])
        }
    }


def calculate_structure_score_fixed(
    swing: Dict,
    all_swings: List[Dict],
    current_swing_index: int
) -> Dict[str, float]:
    """
    FIXED: Structure score based on THIS swing's properties
    
    No longer looks at next swing - evaluates current swing's significance
    """
    # Check this swing's own structure properties
    if swing.get("choch") is True:
        return {
            'score': 1.0,
            'reason': 'CHOCH',
            'description': 'This swing changed market character'
        }
    
    if swing.get("bos") is True:
        return {
            'score': 0.9,
            'reason': 'BOS',
            'description': 'This swing broke market structure'
        }
    
    # Check swing structure pattern
    structure = swing.get("structure", "")
    
    if structure in ["HH", "LL"]:
        # New extreme in trend
        return {
            'score': 0.75,
            'reason': 'New Extreme',
            'description': f'Created new {structure}'
        }
    
    if structure in ["HL", "LH"]:
        # Healthy retracement
        return {
            'score': 0.65,
            'reason': 'Retracement',
            'description': f'Created {structure} retracement'
        }
    
    # Check if this is a higher timeframe swing
    if swing.get("isHigherTF") or swing.get("swingType") == "macro":
        return {
            'score': 0.80,
            'reason': 'Higher Timeframe',
            'description': 'Significant multi-timeframe swing'
        }
    
    # Default: neutral structure
    return {
        'score': 0.5,
        'reason': 'Neutral',
        'description': 'No significant structure event'
    }


def calculate_key_level_proximity_fixed(
    swing_price: float,
    swing_index: Optional[int],
    key_levels_data: Dict,
    atr_value: Optional[float],
    range_multiplier: float = 0.25,
    is_backtesting: bool = True
) -> Dict[str, float]:
    """
    FIXED: Key level proximity with proper level filtering
    
    Args:
        is_backtesting: If True, considers all levels (known chart)
                       If False, only considers levels before swing (live trading)
    """
    # Guard against None swing_index
    if swing_index is None or swing_index < 0:
        return {'score': 0.0, 'nearest_level': None}
    
    # Guard against None atr_value
    if atr_value is None or atr_value <= 0:
        return {'score': 0.0, 'nearest_level': None}
    
    if not key_levels_data or "keyLevels" not in key_levels_data:
        return {'score': 0.0, 'nearest_level': None}
    
    key_levels = key_levels_data["keyLevels"]
    
    # Collect all levels
    all_levels = []
    for category in ["immediateResistance", "immediateSupport", 
                     "structuralHigh", "structuralLow"]:
        if category in key_levels:
            all_levels.extend(key_levels[category])
    
    if not all_levels:
        return {'score': 0.0, 'nearest_level': None}
    
    # Filter levels based on context
    filtered_levels = []
    for level in all_levels:
        level_price = level.get("price")
        level_index = level.get("index")
        
        if level_price is None:
            continue
        
        # In backtesting, we know all levels
        # In live trading, only use levels formed before this swing
        if is_backtesting:
            # Use all levels
            filtered_levels.append(level)
        else:
            # Only levels that formed before this swing
            # FIXED: Check both level_index and swing_index are not None before comparison
            if level_index is not None and swing_index is not None and level_index < swing_index:
                filtered_levels.append(level)
    
    if not filtered_levels:
        return {'score': 0.0, 'nearest_level': None}
    
    # Find nearest level with bonuses
    # atr_value is already validated at function start
    range_offset = atr_value * range_multiplier
    
    nearest_distance = float('inf')
    nearest_level = None
    
    for level in filtered_levels:
        level_price = level.get("price")
        distance = abs(swing_price - level_price)
        
        # Calculate bonus factors
        level_type = level.get("levelType", "")
        source = level.get("source", "")
        
        is_structural = level_type in ["structural_high", "structural_low"]
        is_role_reversed = "(reversed)" in str(source)
        
        # Apply distance weights (makes level "appear closer")
        if is_structural:
            weighted_distance = distance * 0.70  # 30% closer
        elif is_role_reversed:
            weighted_distance = distance * 0.80  # 20% closer
        else:
            weighted_distance = distance
        
        if weighted_distance < nearest_distance:
            nearest_distance = weighted_distance
            nearest_level = level
    
    if nearest_level is None:
        return {'score': 0.0, 'nearest_level': None}
    
    # Calculate proximity score
    distance = abs(swing_price - nearest_level["price"])
    
    # Within range?
    if distance <= range_offset:
        # Within range - high score
        center_distance = distance
        max_distance = range_offset
        score = 1.0 - (center_distance / max_distance) * 0.2  # 0.8 to 1.0
        base_score = max(0.8, min(1.0, score))
    elif distance <= range_offset * 3:
        # Close proximity (within 3x range)
        distance_beyond = distance - range_offset
        max_relevant = range_offset * 2
        score = 0.79 - (distance_beyond / max_relevant) * 0.29
        base_score = max(0.5, min(0.79, score))
    else:
        # Far away - exponential decay
        distance_beyond = distance - (range_offset * 3)
        score = 0.49 * math.exp(-distance_beyond / (range_offset * 2))
        base_score = max(0.0, min(0.49, score))
    
    # Apply explicit score bonuses (not distance manipulation)
    level_type = nearest_level.get("levelType", "")
    source = nearest_level.get("source", "")
    
    is_structural = level_type in ["structural_high", "structural_low"]
    is_role_reversed = "(reversed)" in str(source)
    
    score_bonus = 0.0
    if is_structural:
        score_bonus += 0.10  # +10% for structural
    if is_role_reversed:
        score_bonus += 0.08  # +8% for role reversal
    
    final_score = min(1.0, base_score + score_bonus)
    
    return {
        'score': final_score,
        'nearest_level': {
            'price': nearest_level["price"],
            'distance': distance,
            'distance_in_atr': distance / atr_value if atr_value > 0 else 0,
            'type': nearest_level.get("levelType"),
            'is_structural': is_structural,
            'is_role_reversed': is_role_reversed
        }
    }


def calculate_dominance_no_forward_bias(
    swing: Dict,
    chart_data: Dict,
    swing_index: int,
    windows: AdaptiveWindows
) -> Dict[str, float]:
    """
    Calculate dominance using only past data (no forward bias)
    """
    highs = chart_data.get("high", [])
    lows = chart_data.get("low", [])
    
    if swing_index < 0 or swing_index >= len(highs):
        return {'score': 0.5}
    
    window = windows.get_immediate_reaction_window()
    swing_type = swing.get("type")
    swing_price = swing.get("price")
    
    # Only look at candles BEFORE and AT the swing (no forward bias)
    start_idx = max(0, swing_index - window)
    end_idx = swing_index  # Don't include candles after!
    
    total_candles = end_idx - start_idx
    if total_candles == 0:
        return {'score': 0.5}
    
    dominant_count = 0
    
    if swing_type == "high":
        # Count how many candles have lower highs
        for i in range(start_idx, end_idx):
            if i < len(highs) and highs[i] < swing_price:
                dominant_count += 1
    else:  # low
        # Count how many candles have higher lows
        for i in range(start_idx, end_idx):
            if i < len(lows) and lows[i] > swing_price:
                dominant_count += 1
    
    dominance_ratio = dominant_count / total_candles if total_candles > 0 else 0.5
    
    # Scale dominance (higher = better swing)
    score = min(1.0, dominance_ratio * 1.2)
    
    return {
        'score': score,
        'dominant_count': dominant_count,
        'total_count': total_candles,
        'ratio': dominance_ratio
    }


def calculate_momentum_reaction(
    swing_index: int,
    momentum_data: List[Dict],
    swing_type: str,
    windows: AdaptiveWindows
) -> Dict[str, float]:
    """
    Calculate momentum reaction (simplified for clarity)
    """
    if not momentum_data:
        return {'score': 0.5}
    
    window = windows.get_immediate_reaction_window()
    
    # Create index map
    mom_by_index = {m.get("index"): m for m in momentum_data if m.get("index") is not None}
    
    # Pre-swing momentum
    pre_scores = []
    for i in range(max(0, swing_index - window), swing_index):
        if i in mom_by_index:
            score = abs(mom_by_index[i].get("score", 0))
            pre_scores.append(score)
    
    # Post-swing momentum (direction-aware)
    post_scores = []
    for i in range(swing_index + 1, swing_index + 1 + window):
        if i in mom_by_index:
            mom = mom_by_index[i]
            direction = mom.get("direction", "")
            score = abs(mom.get("score", 0))
            
            # Only count aligned momentum
            if (swing_type == "low" and direction == "bullish") or \
               (swing_type == "high" and direction == "bearish"):
                post_scores.append(score)
    
    if not pre_scores or not post_scores:
        return {'score': 0.5}
    
    pre_avg = sum(pre_scores) / len(pre_scores)
    post_avg = sum(post_scores) / len(post_scores)
    
    if pre_avg == 0:
        ratio = 2.0 if post_avg > 0 else 1.0
    else:
        ratio = post_avg / pre_avg
    
    score = calculate_adaptive_sigmoid(ratio, 'moderate')
    
    return {
        'score': score,
        'pre_avg': pre_avg,
        'post_avg': post_avg,
        'ratio': ratio
    }


def calculate_swing_quality_fixed(
    swing: Dict,
    chart_data: Dict,
    all_swings: List[Dict],
    momentum_data: List[Dict],
    key_levels_data: Dict,
    atr_values: List[float],
    windows: AdaptiveWindows,
    current_swing_index: int,
    is_backtesting: bool = True
) -> Dict[str, any]:
    """
    FIXED: Complete swing quality calculation with all improvements
    
    No forward-looking bias - can be used in real-time trading
    """
    swing_index = swing.get("index")
    
    if swing_index is None or swing_index < 0:
        return {'quality': 0.5, 'breakdown': {}, 'usable_realtime': False}
    
    # Get ATR for this swing
    atr = atr_values[swing_index] if swing_index < len(atr_values) else None
    if atr is None or atr <= 0:
        atr = swing.get("price", 1000) * 0.01
    
    # Calculate all quality components (NO forward bias)
    
    # 1. Dominance (based on past candles only)
    dominance = calculate_dominance_no_forward_bias(
        swing, chart_data, swing_index, windows
    )
    
    # 2. Volume reaction (enhanced with absorption)
    volume_result = calculate_volume_reaction_enhanced(
        swing_index, chart_data, swing.get("type", ""), windows
    )
    
    # 3. Momentum reaction
    momentum_result = calculate_momentum_reaction(
        swing_index, momentum_data, swing.get("type", ""), windows
    )
    
    # 4. Key level proximity (fixed filtering)
    proximity_result = calculate_key_level_proximity_fixed(
        swing.get("price"), swing_index, key_levels_data, 
        atr, 0.25, is_backtesting
    )
    
    # 5. Clarity (weighted by size)
    clarity_result = calculate_clarity_weighted(
        swing, swing_index, chart_data, windows
    )
    
    # 6. Structure (fixed attribution)
    structure_result = calculate_structure_score_fixed(
        swing, all_swings, current_swing_index
    )
    
    # Compile breakdown
    breakdown = {
        'dominance': dominance['score'],
        'volume_reaction': volume_result['score'],
        'volume_absorption': volume_result.get('absorption_detected', False),
        'momentum_reaction': momentum_result['score'],
        'key_level_proximity': proximity_result['score'],
        'clarity': clarity_result['score'],
        'structure': structure_result['score']
    }
    
    # Calculate confluence
    high_scores = [v for v in breakdown.values() if isinstance(v, (int, float)) and v > 0.7]
    low_scores = [v for v in breakdown.values() if isinstance(v, (int, float)) and v < 0.3]
    
    confluence_bonus = 0.0
    if len(high_scores) >= 4:
        confluence_bonus = 0.15
    elif len(high_scores) >= 3:
        confluence_bonus = 0.10
    elif len(high_scores) >= 2:
        confluence_bonus = 0.05
    
    if len(low_scores) >= 2:
        confluence_bonus -= 0.10
    
    # Weighted combination
    base_quality = (
        dominance['score'] * 0.25 +
        volume_result['score'] * 0.20 +
        momentum_result['score'] * 0.15 +
        proximity_result['score'] * 0.15 +
        clarity_result['score'] * 0.10 +
        structure_result['score'] * 0.10 +
        0.05  # Reserve for future metrics
    )
    
    final_quality = max(0.0, min(1.0, base_quality + confluence_bonus))
    
    return {
        'quality': final_quality,
        'breakdown': breakdown,
        'confluence_bonus': confluence_bonus,
        'details': {
            'volume': volume_result,
            'momentum': momentum_result,
            'proximity': proximity_result,
            'clarity': clarity_result,
            'structure': structure_result,
            'dominance': dominance
        },
        'usable_realtime': True  # No forward bias!
    }


# Legacy functions for backward compatibility
def calculate_swing_structure_score(
    swing: Dict,
    all_swings: List[Dict],
    current_swing_index: int
) -> float:
    """Legacy wrapper for structure score"""
    result = calculate_structure_score_fixed(swing, all_swings, current_swing_index)
    return result['score']


def calculate_swing_clarity(
    swing: Dict,
    swing_index: int,
    chart_data: Dict,
    clarity_candles: int = 5
) -> float:
    """Legacy wrapper for clarity score"""
    # Create a simple AdaptiveWindows for backward compatibility
    windows = AdaptiveWindows('1h', 'normal')
    result = calculate_clarity_weighted(swing, swing_index, chart_data, windows)
    return result['score']


def calculate_volume_reaction_strength(
    swing_index: int,
    chart_data: Dict,
    swing_type: str,
    pre_candles: int = 4,
    post_candles: int = 4
) -> float:
    """Legacy wrapper for volume reaction"""
    windows = AdaptiveWindows('1h', 'normal')
    result = calculate_volume_reaction_enhanced(swing_index, chart_data, swing_type, windows)
    return result['score']


def calculate_momentum_reaction_strength(
    swing_index: int,
    momentum_data: List[Dict],
    swing_type: str,
    pre_candles: int = 4,
    post_candles: int = 4
) -> float:
    """Legacy wrapper for momentum reaction"""
    windows = AdaptiveWindows('1h', 'normal')
    result = calculate_momentum_reaction(swing_index, momentum_data, swing_type, windows)
    return result['score']


def calculate_key_level_proximity_score(
    swing_price: float,
    swing_index: int,
    key_levels_data: Dict,
    atr_value: float,
    range_multiplier: float = 0.25
) -> float:
    """Legacy wrapper for key level proximity"""
    result = calculate_key_level_proximity_fixed(
        swing_price, swing_index, key_levels_data, atr_value, range_multiplier, is_backtesting=True
    )
    return result['score']


def calculate_expanding_momentum_volume(
    swing_index: int,
    momentum_data: List[Dict],
    chart_data: Dict,
    swing_type: str,
    start_candle: int = 5,
    end_candle: int = 10
) -> Dict[str, float]:
    """
    Calculate expanding momentum and volume from candles 5-10 after the swing point
    (Kept for backward compatibility)
    """
    if not momentum_data or len(momentum_data) == 0:
        return {"momentum": 0.5, "volume": 0.5}
    
    volumes = chart_data.get("volume", [])
    opens = chart_data.get("open", [])
    closes = chart_data.get("close", [])
    
    if swing_index < 0:
        return {"momentum": 0.5, "volume": 0.5}
    
    momentum_by_index = {m.get("index"): m for m in momentum_data if m.get("index") is not None}
    
    expanding_momentum_scores = []
    for i in range(swing_index + start_candle, min(swing_index + end_candle + 1, len(closes) if closes else swing_index + end_candle + 1)):
        if i in momentum_by_index:
            momentum = momentum_by_index[i]
            direction = momentum.get("direction", "")
            score = abs(momentum.get("score", 0))
            
            if (swing_type == "low" and direction == "bullish") or \
               (swing_type == "high" and direction == "bearish"):
                expanding_momentum_scores.append(score)
    
    expanding_volumes = []
    for i in range(swing_index + start_candle, min(swing_index + end_candle + 1, len(volumes) if volumes else swing_index + end_candle + 1)):
        if i >= len(volumes) or volumes[i] <= 0:
            continue
        
        if i < len(opens) and i < len(closes):
            candle_open = opens[i]
            candle_close = closes[i]
            
            if candle_open is None or candle_close is None:
                continue
            
            is_bullish_candle = candle_close > candle_open
            
            if (swing_type == "low" and is_bullish_candle) or \
               (swing_type == "high" and not is_bullish_candle):
                expanding_volumes.append(volumes[i])
    
    momentum_score = 0.5
    if expanding_momentum_scores:
        avg_momentum = sum(expanding_momentum_scores) / len(expanding_momentum_scores)
        momentum_score = min(1.0, max(0.0, avg_momentum))
    
    volume_score = 0.5
    if expanding_volumes:
        pre_start = max(0, swing_index - 4)
        pre_end = swing_index
        pre_volumes = [v for v in volumes[pre_start:pre_end] if v > 0]
        
        if pre_volumes:
            pre_avg = sum(pre_volumes) / len(pre_volumes)
            expanding_avg = sum(expanding_volumes) / len(expanding_volumes)
            
            if pre_avg > 0:
                volume_ratio = expanding_avg / pre_avg
                k = 3.0
                base_ratio = volume_ratio - 1.0
                volume_score = 1.0 / (1.0 + math.exp(-k * base_ratio))
                volume_score = max(0.0, min(1.0, volume_score))
        else:
            expanding_avg = sum(expanding_volumes) / len(expanding_volumes)
            volume_score = min(1.0, expanding_avg / 10000.0) if expanding_avg > 0 else 0.5
    
    return {
        "momentum": momentum_score,
        "volume": volume_score
    }


def calculate_swing_price_range(
    swing_price: float,
    atr_value: Optional[float],
    range_multiplier: float = 0.25
) -> Dict[str, float]:
    """Calculate price range around a swing point using ATR"""
    # Guard against None atr_value
    if atr_value is None or atr_value <= 0:
        default_range = swing_price * 0.001
        return {
            "min": swing_price - default_range,
            "max": swing_price + default_range
        }
    
    range_offset = atr_value * range_multiplier
    return {
        "min": swing_price - range_offset,
        "max": swing_price + range_offset
    }


def calculate_key_level_price_range(
    key_level_price: float,
    atr_value: Optional[float],
    range_multiplier: float = 0.25
) -> Dict[str, float]:
    """Calculate price range around a key level using ATR"""
    # Guard against None atr_value
    if atr_value is None or atr_value <= 0:
        default_range = key_level_price * 0.001
        return {
            "min": key_level_price - default_range,
            "max": key_level_price + default_range
        }
    
    range_offset = atr_value * range_multiplier
    return {
        "min": key_level_price - range_offset,
        "max": key_level_price + range_offset
    }


def calculate_swing_quality(
    swing: Dict,
    candles: List[Dict],
    swing_index: int,
    lookback: int,
    dominance_ratio: float,
    chart_data: Dict,
    is_micro: bool = False
) -> float:
    """
    Legacy quality calculation (kept for backward compatibility)
    Uses simplified calculation
    """
    if swing_index < 0 or swing_index >= len(candles):
        return 0.5
    
    # Simplified quality calculation
    windows = AdaptiveWindows('1h', 'normal')
    
    dominance = calculate_dominance_no_forward_bias(swing, chart_data, swing_index, windows)
    volume_result = calculate_volume_reaction_enhanced(swing_index, chart_data, swing.get("type", ""), windows)
    
    # Weighted average
    quality = dominance['score'] * 0.6 + volume_result['score'] * 0.4
    
    if is_micro:
        quality = quality * 0.9
    
    return max(0.0, min(1.0, quality))


def evaluate_swings_with_quality(
    chart_data: Dict,
    timeframe: str,
    is_higher_tf: bool = False,
    sensitivity_factor: float = 1.0,
    detect_micro: bool = True,
    atr_window: int = 14,
    range_multiplier: float = 0.25,
    volatility_regime: str = 'normal',
    is_backtesting: bool = True
) -> List[Dict]:
    """
    Main entry point: Detect swings and add quality scores
    
    This function maintains backward compatibility while using the improved logic
    """
    # Get swings from swing_detection
    swings = detect_swing_structure(
        chart_data=chart_data,
        timeframe=timeframe,
        is_higher_tf=is_higher_tf,
        sensitivity_factor=sensitivity_factor,
        detect_micro=detect_micro
    )
    
    if not swings:
        return swings
    
    # Calculate ATR
    atr_values = average_true_range(chart_data, atr_window)
    
    # Calculate key levels
    key_levels_data = detect_key_levels(
        chart_data=chart_data,
        config=KeyLevelsConfig(
            timeframe=timeframe,
            lookback_period=50,
            min_touches=1
        )
    )
    
    # Calculate momentum (v2 API)
    momentum_result = calculate_momentum(
        data=chart_data,
        timeframe=timeframe,
        lookback=5,
        use_swings=False,
        chart_data=None,
        detect_divergences=False
    )
    # Extract momentum array from result
    momentum_data = momentum_result.get("momentum", []) if isinstance(momentum_result, dict) else []
    
    # Create AdaptiveWindows
    windows = AdaptiveWindows(timeframe, volatility_regime)
    
    # Process each swing with improved quality calculation
    swings_with_quality = []
    for swing_idx, swing in enumerate(swings):
        swing_copy = swing.copy()
        swing_index = swing.get("index")
        
        if swing_index is None or swing_index < 0:
            # Invalid index - assign defaults
            swing_copy["quality"] = 0.5
            swing_copy["volumeReaction"] = 0.5
            swing_copy["momentumReaction"] = 0.5
            swing_copy["keyLevelProximity"] = 0.0
            swing_copy["clarity"] = 0.5
            swing_copy["structure"] = 0.5
            swing_copy["expandingMomentum"] = 0.5
            swing_copy["expandingVolume"] = 0.5
            swing_price = swing.get("price")
            if swing_price is not None:
                default_range = swing_price * 0.001
                swing_copy["priceRange"] = {
                    "min": swing_price - default_range,
                    "max": swing_price + default_range
                }
            else:
                swing_copy["priceRange"] = {"min": 0.0, "max": 0.0}
            swings_with_quality.append(swing_copy)
            continue
        
        # Use improved quality calculation
        quality_result = calculate_swing_quality_fixed(
            swing=swing_copy,
            chart_data=chart_data,
            all_swings=swings,
            momentum_data=momentum_data,
            key_levels_data=key_levels_data,
            atr_values=atr_values,
            windows=windows,
            current_swing_index=swing_idx,
            is_backtesting=is_backtesting
        )
        
        # Extract scores for backward compatibility
        breakdown = quality_result.get('breakdown', {})
        swing_copy["quality"] = quality_result.get('quality', 0.5)
        swing_copy["volumeReaction"] = breakdown.get('volume_reaction', 0.5)
        swing_copy["momentumReaction"] = breakdown.get('momentum_reaction', 0.5)
        swing_copy["keyLevelProximity"] = breakdown.get('key_level_proximity', 0.0)
        swing_copy["clarity"] = breakdown.get('clarity', 0.5)
        swing_copy["structure"] = breakdown.get('structure', 0.5)
        
        # Calculate expanding momentum/volume
        expanding_scores = calculate_expanding_momentum_volume(
            swing_index,
            momentum_data,
            chart_data,
            swing.get("type", ""),
            windows.get_expanding_start(),
            windows.get_expanding_end()
        )
        swing_copy["expandingMomentum"] = expanding_scores["momentum"]
        swing_copy["expandingVolume"] = expanding_scores["volume"]
        
        # Calculate price range
        swing_price = swing.get("price")
        if swing_price is not None and swing_index < len(atr_values):
            atr_value = atr_values[swing_index]
            if atr_value is not None and atr_value > 0:
                price_range = calculate_swing_price_range(
                    swing_price,
                    atr_value,
                    range_multiplier
                )
                swing_copy["priceRange"] = price_range
            else:
                default_range = swing_price * 0.001
                swing_copy["priceRange"] = {
                    "min": swing_price - default_range,
                    "max": swing_price + default_range
                }
        else:
            swing_copy["priceRange"] = {
                "min": swing.get("price", 0.0),
                "max": swing.get("price", 0.0)
            }
        
        swings_with_quality.append(swing_copy)
    
    return swings_with_quality


# Export main function for single swing evaluation
def evaluate_swing_with_quality_fixed(
    swing: Dict,
    chart_data: Dict,
    all_swings: List[Dict],
    momentum_data: List[Dict],
    key_levels_data: Dict,
    atr_values: List[float],
    current_swing_index: int,
    timeframe: str = '1h',
    volatility_regime: str = 'normal',
    is_backtesting: bool = True
) -> Dict:
    """
    Main entry point for fixed swing evaluation (single swing)
    
    Returns:
        Dictionary with quality score, breakdown, and all details
    """
    windows = AdaptiveWindows(timeframe, volatility_regime)
    
    return calculate_swing_quality_fixed(
        swing=swing,
        chart_data=chart_data,
        all_swings=all_swings,
        momentum_data=momentum_data,
        key_levels_data=key_levels_data,
        atr_values=atr_values,
        windows=windows,
        current_swing_index=current_swing_index,
        is_backtesting=is_backtesting
    )
