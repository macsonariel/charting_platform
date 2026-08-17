"""Narrative Templates - Text templates for different market scenarios.

Contains template strings and formatters for each scenario type.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class NarrativeTemplate:
    """A narrative template with placeholders."""
    scenario: str
    summary_template: str
    detail_template: str
    action_template: str
    risk_template: str


# ============================================================================
# BULLISH TEMPLATES
# ============================================================================

BULLISH_TRENDING = NarrativeTemplate(
    scenario="trending_up",
    
    summary_template="""
{symbol} is in a **bullish uptrend** on the {timeframe} timeframe. 
Price is currently at {current_price:,.2f}, trading above key structure levels.
""".strip(),
    
    detail_template="""
**Trend Evidence:**
- {bullish_bos} bullish structure break(s) confirm upward momentum
- External high at {external_high:,.2f} defines the structural ceiling
- External low at {external_low:,.2f} is the key support to hold

**Key Observations:**
- {swing_pattern}
- {fvg_status}
- {level_status}
""".strip(),
    
    action_template="""
**Potential Opportunities:**
- Look for pullbacks to unfilled FVGs around {fvg_entry:,.2f}
- Protected low at {protected_low:,.2f} is the invalidation point
- Target extension toward {target:,.2f} if momentum continues
""".strip(),
    
    risk_template="""
**Risk Factors:**
- A close below {protected_low:,.2f} would break bullish structure
- {bearish_bos} bearish BOS present - watch for trend weakness
- Monitor for CHoCH (character change) near highs
""".strip(),
)


BULLISH_REVERSAL = NarrativeTemplate(
    scenario="reversal_up",
    
    summary_template="""
{symbol} is showing signs of a **bullish reversal** on the {timeframe} timeframe.
A character change (CHoCH) has occurred, suggesting the downtrend may be ending.
Current price: {current_price:,.2f}
""".strip(),
    
    detail_template="""
**Reversal Evidence:**
- CHoCH detected - previous lower high broken to upside
- {bullish_bos} bullish BOS following the reversal signal
- Shift from bearish to bullish structure in progress

**Key Levels:**
- Reversal pivot around {pivot_level:,.2f}
- New protected low at {protected_low:,.2f}
""".strip(),
    
    action_template="""
**Potential Opportunities:**
- Entry on pullback to the CHoCH zone or nearest FVG
- Conservative target: retest of previous structure high
- Aggressive target: new higher high formation
""".strip(),
    
    risk_template="""
**Risk Factors:**
- Reversals can fail - wait for confirmation BOS
- Previous trend may resume if CHoCH level is reclaimed
- Lower timeframe must align for higher probability
""".strip(),
)


# ============================================================================
# BEARISH TEMPLATES
# ============================================================================

BEARISH_TRENDING = NarrativeTemplate(
    scenario="trending_down",
    
    summary_template="""
{symbol} is in a **bearish downtrend** on the {timeframe} timeframe.
Price is currently at {current_price:,.2f}, trading below key structure levels.
""".strip(),
    
    detail_template="""
**Trend Evidence:**
- {bearish_bos} bearish structure break(s) confirm downward momentum
- External low at {external_low:,.2f} defines the structural floor
- External high at {external_high:,.2f} is the key resistance to break

**Key Observations:**
- {swing_pattern}
- {fvg_status}
- {level_status}
""".strip(),
    
    action_template="""
**Potential Opportunities:**
- Look for rallies into unfilled FVGs around {fvg_entry:,.2f}
- Protected high at {protected_high:,.2f} is the invalidation point
- Target extension toward {target:,.2f} if momentum continues
""".strip(),
    
    risk_template="""
**Risk Factors:**
- A close above {protected_high:,.2f} would break bearish structure
- {bullish_bos} bullish BOS present - watch for trend weakness
- Monitor for CHoCH (character change) near lows
""".strip(),
)


BEARISH_REVERSAL = NarrativeTemplate(
    scenario="reversal_down",
    
    summary_template="""
{symbol} is showing signs of a **bearish reversal** on the {timeframe} timeframe.
A character change (CHoCH) has occurred, suggesting the uptrend may be ending.
Current price: {current_price:,.2f}
""".strip(),
    
    detail_template="""
**Reversal Evidence:**
- CHoCH detected - previous higher low broken to downside
- {bearish_bos} bearish BOS following the reversal signal
- Shift from bullish to bearish structure in progress

**Key Levels:**
- Reversal pivot around {pivot_level:,.2f}
- New protected high at {protected_high:,.2f}
""".strip(),
    
    action_template="""
**Potential Opportunities:**
- Entry on rally to the CHoCH zone or nearest FVG
- Conservative target: retest of previous structure low
- Aggressive target: new lower low formation
""".strip(),
    
    risk_template="""
**Risk Factors:**
- Reversals can fail - wait for confirmation BOS
- Previous trend may resume if CHoCH level is reclaimed
- Lower timeframe must align for higher probability
""".strip(),
)


# ============================================================================
# NEUTRAL TEMPLATES
# ============================================================================

RANGING = NarrativeTemplate(
    scenario="ranging",
    
    summary_template="""
{symbol} is in a **ranging/consolidation** phase on the {timeframe} timeframe.
Price is currently at {current_price:,.2f}, oscillating between defined boundaries.
""".strip(),
    
    detail_template="""
**Range Evidence:**
- No clear directional bias - mixed structure breaks
- Price contained between {range_high:,.2f} and {range_low:,.2f}
- Internal swings dominating, no external expansion

**Key Observations:**
- Range equilibrium around {equilibrium:,.2f}
- Both bulls and bears failing to take control
""".strip(),
    
    action_template="""
**Potential Opportunities:**
- Range traders: buy at {range_low:,.2f}, sell at {range_high:,.2f}
- Breakout traders: wait for close outside range
- Watch for accumulation (bullish) or distribution (bearish) patterns
""".strip(),
    
    risk_template="""
**Risk Factors:**
- Ranges can persist longer than expected
- False breakouts common - wait for confirmation
- Volatility often follows extended consolidation
""".strip(),
)


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

TEMPLATES: Dict[str, NarrativeTemplate] = {
    "trending_up": BULLISH_TRENDING,
    "trending_down": BEARISH_TRENDING,
    "reversal_up": BULLISH_REVERSAL,
    "reversal_down": BEARISH_REVERSAL,
    "ranging": RANGING,
    "unknown": RANGING,  # Fallback
    "accumulation": RANGING,
    "distribution": RANGING,
    "breakout_up": BULLISH_TRENDING,
    "breakout_down": BEARISH_TRENDING,
}


def get_template(scenario: str) -> NarrativeTemplate:
    """Get template for a scenario."""
    return TEMPLATES.get(scenario, RANGING)
