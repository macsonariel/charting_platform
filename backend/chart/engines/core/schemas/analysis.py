"""Market Analysis - 8 Section Trader Q&A.

Organized into 8 clear sections answering all trader questions
about market context, structure, liquidity, and direction.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class MarketAnalysis:
    """Complete market analysis organized into 8 sections.
    
    Section 1: Market Context - "Where am I?"
    Section 2: Structure - "How is price moving?"
    Section 3: Liquidity - "Where are the incentives?"
    Section 4: Important Levels - "What matters right now?"
    Section 5: Momentum & Volatility - "How strong is the move?"
    Section 6: Probabilistic Direction - "What is price leaning toward?"
    Section 7: Invalidation Logic - "What would prove this wrong?"
    Section 8: Projection - "What information could we learn next?"
    """
    
    # =====================================================================
    # SECTION 1: MARKET CONTEXT — "Where am I?"
    # =====================================================================
    htf_direction: str = ""           # What is the higher timeframe direction?
    htf_direction_detail: str = ""
    direction_source: str = ""
    direction_source_timeframe: str = ""
    external_high: float = 0.0        # Where are the major external highs/lows?
    external_low: float = 0.0
    external_range: str = ""
    htf_leg: str = ""                 # What leg of the HTF am I inside?
    htf_leg_detail: str = ""
    
    # =====================================================================
    # SECTION 2: STRUCTURE — "How is price moving?"
    # =====================================================================
    local_structure: str = ""         # What is the current local structure?
    local_structure_detail: str = ""
    protected_levels: str = ""        # Which levels are protected?
    protected_count: int = 0
    invalidated_levels: str = ""      # Which levels are invalidated?
    invalidated_count: int = 0
    recent_event: str = ""            # What structural event happened most recently?
    recent_event_type: str = ""
    
    # =====================================================================
    # SECTION 3: LIQUIDITY — "Where are the incentives?"
    # =====================================================================
    buy_side_liquidity: str = ""      # Where is buy-side liquidity?
    sell_side_liquidity: str = ""     # Where is sell-side liquidity?
    liquidity_taken: str = ""         # What liquidity was recently taken?
    liquidity_remaining: str = ""     # What liquidity remains untouched?
    
    # =====================================================================
    # SECTION 4: IMPORTANT LEVELS — "What matters right now?"
    # =====================================================================
    valid_zones: str = ""             # What zones remain valid?
    invalid_zones: str = ""           # What zones are no longer valid?
    nearest_reaction: str = ""        # What are the nearest reaction zones?
    nearest_above: float = 0.0
    nearest_below: float = 0.0
    
    # =====================================================================
    # SECTION 5: MOMENTUM & VOLATILITY — "How strong is the move?"
    # =====================================================================
    impulse_strength: str = ""        # What is the impulse strength?
    correction_character: str = ""    # What is the correction character?
    volatility_trend: str = ""        # Is volatility increasing or decreasing?
    momentum_aligned: str = ""        # Is momentum aligned with structure?
    
    # =====================================================================
    # SECTION 6: PROBABILISTIC DIRECTION — "What is price leaning toward?"
    # =====================================================================
    directional_bias: str = ""        # Upward or downward pressure?
    bias_reasoning: str = ""          # Why this direction is more likely
    path_of_least_resistance: str = ""  # Where is the path of least resistance?
    confidence_level: str = ""        # Confidence in the bias
    
    # =====================================================================
    # SECTION 7: INVALIDATION LOGIC — "What would prove this wrong?"
    # =====================================================================
    invalidation_swing: str = ""      # What swing, if broken, invalidates context?
    invalidation_price: float = 0.0
    structural_shift_signal: str = "" # What event would signal a structural shift?
    
    # =====================================================================
    # SECTION 8: PROJECTION — "What information could we learn next?"
    # =====================================================================
    if_price_reaches: str = ""        # If price reaches X zone, what info will that provide?
    next_area_of_interest: str = ""   # What is the next major area of interest?
    next_area_price: float = 0.0
    bullish_scenario: str = ""        # What would a bullish scenario look like?
    bearish_scenario: str = ""        # What would a bearish scenario look like?
    
    # =====================================================================
    # OVERALL
    # =====================================================================
    market_state: str = ""            # TRENDING, RANGING, REVERSAL
    clarity_score: int = 0            # 0-100 readability score
    summary: str = ""                 # One-line summary
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            # Section 1: Context
            "section_1_context": {
                "htf_direction": self.htf_direction,
                "htf_direction_detail": self.htf_direction_detail,
                "direction_source": self.direction_source,
                "direction_source_timeframe": self.direction_source_timeframe,
                "external_high": self.external_high,
                "external_low": self.external_low,
                "external_range": self.external_range,
                "htf_leg": self.htf_leg,
                "htf_leg_detail": self.htf_leg_detail,
            },
            # Section 2: Structure
            "section_2_structure": {
                "local_structure": self.local_structure,
                "local_structure_detail": self.local_structure_detail,
                "protected_levels": self.protected_levels,
                "protected_count": self.protected_count,
                "invalidated_levels": self.invalidated_levels,
                "invalidated_count": self.invalidated_count,
                "recent_event": self.recent_event,
                "recent_event_type": self.recent_event_type,
            },
            # Section 3: Liquidity
            "section_3_liquidity": {
                "buy_side_liquidity": self.buy_side_liquidity,
                "sell_side_liquidity": self.sell_side_liquidity,
                "liquidity_taken": self.liquidity_taken,
                "liquidity_remaining": self.liquidity_remaining,
            },
            # Section 4: Important Levels
            "section_4_levels": {
                "valid_zones": self.valid_zones,
                "invalid_zones": self.invalid_zones,
                "nearest_reaction": self.nearest_reaction,
                "nearest_above": self.nearest_above,
                "nearest_below": self.nearest_below,
            },
            # Section 5: Momentum
            "section_5_momentum": {
                "impulse_strength": self.impulse_strength,
                "correction_character": self.correction_character,
                "volatility_trend": self.volatility_trend,
                "momentum_aligned": self.momentum_aligned,
            },
            # Section 6: Direction
            "section_6_direction": {
                "directional_bias": self.directional_bias,
                "bias_reasoning": self.bias_reasoning,
                "path_of_least_resistance": self.path_of_least_resistance,
                "confidence_level": self.confidence_level,
            },
            # Section 7: Invalidation
            "section_7_invalidation": {
                "invalidation_swing": self.invalidation_swing,
                "invalidation_price": self.invalidation_price,
                "structural_shift_signal": self.structural_shift_signal,
            },
            # Section 8: Projection
            "section_8_projection": {
                "if_price_reaches": self.if_price_reaches,
                "next_area_of_interest": self.next_area_of_interest,
                "next_area_price": self.next_area_price,
                "bullish_scenario": self.bullish_scenario,
                "bearish_scenario": self.bearish_scenario,
            },
            # Overall
            "market_state": self.market_state,
            "clarity_score": self.clarity_score,
            "summary": self.summary,
        }
