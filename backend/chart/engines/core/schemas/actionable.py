"""Actionable Context - What matters now.

This module provides the ActionableLevel and ActionableContext schemas
for answering "What actually matters now?" - filtering to the 1-3 most
relevant levels based on proximity, confluence, and bias alignment.
"""
from dataclasses import dataclass, field
from typing import List, Optional


# Base significance scores for level types
LEVEL_SIGNIFICANCE = {
    "choch": 1.0,       # Highest - reversal zone
    "bos": 0.8,         # High - continuation S/R
    "protected": 0.7,   # Key structural level
    "fvg": 0.6,         # Imbalance zone
    "liquidity": 0.5,   # Stop cluster
}

# Action hints for each level type
LEVEL_ACTIONS = {
    "choch": "Reversal zone - watch for confirmation",
    "bos": "Continuation S/R - watch for reaction",
    "protected": "Key structural level - potential entry",
    "fvg": "Imbalance zone - watch for fill/reaction",
    "liquidity": "Stop cluster - potential sweep target",
}


@dataclass
class ActionableLevel:
    """A single actionable price level.
    
    Represents a level that matters right now - close to price,
    high significance, and/or strong confluence.
    
    Attributes:
        level_type: Type of level ("choch", "bos", "protected", "fvg", "liquidity")
        price: Price level
        distance_percent: Distance from current price as percentage
        direction: "above" or "below" current price
        action: Suggested action/what to watch for
        significance: Base significance score (0-1)
        confluence_score: Bonus for overlapping levels (0-1)
        total_score: Combined score for ranking
        source_id: ID of source object
        bias_aligned: Whether level aligns with current market bias
    """
    level_type: str
    price: float
    distance_percent: float
    direction: str
    action: str
    significance: float
    confluence_score: float
    total_score: float
    source_id: str
    bias_aligned: bool = True
    
    @classmethod
    def from_structure_break(cls, sb, current_price: float, bias: str) -> 'ActionableLevel':
        """Create from a structure break (BOS/CHoCH)."""
        is_choch = getattr(sb, 'type', 'BOS') == 'CHoCH'
        level_type = "choch" if is_choch else "bos"
        price = sb.level  # The broken level becomes S/R
        
        distance = abs(price - current_price) / current_price * 100
        direction = "above" if price > current_price else "below"
        significance = LEVEL_SIGNIFICANCE[level_type]
        
        # Bias alignment: bullish bias wants longs from below, bearish from above
        bias_aligned = (
            (bias == "bullish" and direction == "below") or
            (bias == "bearish" and direction == "above") or
            bias == "neutral"
        )
        
        return cls(
            level_type=level_type,
            price=price,
            distance_percent=distance,
            direction=direction,
            action=LEVEL_ACTIONS[level_type],
            significance=significance,
            confluence_score=0.0,
            total_score=significance,
            source_id=sb.id,
            bias_aligned=bias_aligned
        )
    
    @classmethod
    def from_protected_level(cls, pl, current_price: float, bias: str) -> 'ActionableLevel':
        """Create from a protected level."""
        price = pl.price
        distance = abs(price - current_price) / current_price * 100
        direction = "above" if price > current_price else "below"
        significance = LEVEL_SIGNIFICANCE["protected"]
        
        bias_aligned = (
            (bias == "bullish" and direction == "below") or
            (bias == "bearish" and direction == "above") or
            bias == "neutral"
        )
        
        return cls(
            level_type="protected",
            price=price,
            distance_percent=distance,
            direction=direction,
            action=LEVEL_ACTIONS["protected"],
            significance=significance,
            confluence_score=0.0,
            total_score=significance,
            source_id=pl.id,
            bias_aligned=bias_aligned
        )
    
    @classmethod
    def from_fvg(cls, fvg, current_price: float, bias: str) -> 'ActionableLevel':
        """Create from a fair value gap."""
        price = (fvg.high + fvg.low) / 2  # Use midpoint
        distance = abs(price - current_price) / current_price * 100
        direction = "above" if price > current_price else "below"
        significance = LEVEL_SIGNIFICANCE["fvg"]
        
        # FVG alignment: bullish FVG below for long, bearish FVG above for short
        fvg_dir = getattr(fvg, 'direction', 'neutral')
        bias_aligned = (
            (bias == "bullish" and fvg_dir == "bullish" and direction == "below") or
            (bias == "bearish" and fvg_dir == "bearish" and direction == "above") or
            bias == "neutral"
        )
        
        return cls(
            level_type="fvg",
            price=price,
            distance_percent=distance,
            direction=direction,
            action=LEVEL_ACTIONS["fvg"],
            significance=significance,
            confluence_score=0.0,
            total_score=significance,
            source_id=fvg.id,
            bias_aligned=bias_aligned
        )
    
    @classmethod
    def from_liquidity_pool(cls, lp, current_price: float, bias: str) -> 'ActionableLevel':
        """Create from a liquidity pool."""
        price = lp.price
        distance = abs(price - current_price) / current_price * 100
        direction = "above" if price > current_price else "below"
        significance = LEVEL_SIGNIFICANCE["liquidity"]
        
        # Liquidity above for shorts (sweep), below for longs
        bias_aligned = (
            (bias == "bullish" and direction == "below") or
            (bias == "bearish" and direction == "above") or
            bias == "neutral"
        )
        
        return cls(
            level_type="liquidity",
            price=price,
            distance_percent=distance,
            direction=direction,
            action=LEVEL_ACTIONS["liquidity"],
            significance=significance,
            confluence_score=0.0,
            total_score=significance,
            source_id=lp.id,
            bias_aligned=bias_aligned
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "level_type": self.level_type,
            "price": self.price,
            "distance_percent": round(self.distance_percent, 2),
            "direction": self.direction,
            "action": self.action,
            "significance": self.significance,
            "confluence_score": self.confluence_score,
            "total_score": round(self.total_score, 2),
            "source_id": self.source_id,
            "bias_aligned": self.bias_aligned
        }


@dataclass
class ActionableContext:
    """What matters now - filtered actionable context.
    
    Contains the 1-3 most relevant levels and a thesis statement.
    
    Attributes:
        primary_level: The single most important level right now
        secondary_levels: Next 2-3 important levels
        current_thesis: Human-readable thesis statement
        bias: Current market bias
        confidence: Overall confidence (0-1)
    """
    primary_level: Optional[ActionableLevel]
    secondary_levels: List[ActionableLevel] = field(default_factory=list)
    current_thesis: str = ""
    bias: str = "neutral"
    confidence: float = 0.0
    
    @property
    def all_levels(self) -> List[ActionableLevel]:
        """Get all levels (primary + secondary)."""
        if self.primary_level:
            return [self.primary_level] + self.secondary_levels
        return self.secondary_levels
    
    @property
    def level_count(self) -> int:
        """Count of actionable levels."""
        return len(self.all_levels)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "primary_level": self.primary_level.to_dict() if self.primary_level else None,
            "secondary_levels": [l.to_dict() for l in self.secondary_levels],
            "current_thesis": self.current_thesis,
            "bias": self.bias,
            "confidence": round(self.confidence, 2),
            "level_count": self.level_count
        }
