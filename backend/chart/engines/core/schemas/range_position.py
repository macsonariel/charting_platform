"""Range Position Schema - Price position within external range.

Contains premium/discount/equilibrium classification.
"""
from dataclasses import dataclass


@dataclass
class RangePosition:
    """Price position within the external high/low range.
    
    Classifies current price as premium, discount, or equilibrium.
    """
    
    # Range boundaries
    external_high: float = 0.0
    external_low: float = 0.0
    range_size: float = 0.0
    
    # Current position
    current_price: float = 0.0
    position_ratio: float = 0.5  # 0.0 = at low, 1.0 = at high
    
    # Zone classification
    zone: str = "equilibrium"  # premium / discount / equilibrium
    zone_detail: str = "Mid-range"
    
    # Premium/discount thresholds (default: 0.25 and 0.75)
    premium_threshold: float = 0.75
    discount_threshold: float = 0.25
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "external_high": self.external_high,
            "external_low": self.external_low,
            "range_size": self.range_size,
            "current_price": self.current_price,
            "position_ratio": self.position_ratio,
            "zone": self.zone,
            "zone_detail": self.zone_detail
        }
    
    @classmethod
    def from_prices(cls, current: float, high: float, low: float) -> 'RangePosition':
        """Create RangePosition from current price and range boundaries."""
        if high == low or high == 0 or low == 0:
            return cls(
                current_price=current,
                external_high=high,
                external_low=low,
                zone="developing",
                zone_detail="Range forming"
            )
        
        range_size = high - low
        position = (current - low) / range_size if range_size > 0 else 0.5
        
        # Clamp position to 0-1 range
        position = max(0.0, min(1.0, position))
        
        # Classify zone
        if position > 0.75:
            zone = "premium"
            zone_detail = f"Upper zone ({position:.0%} of range)"
        elif position < 0.25:
            zone = "discount"
            zone_detail = f"Lower zone ({position:.0%} of range)"
        else:
            zone = "equilibrium"
            zone_detail = f"Mid-range ({position:.0%} of range)"
        
        return cls(
            external_high=high,
            external_low=low,
            range_size=range_size,
            current_price=current,
            position_ratio=position,
            zone=zone,
            zone_detail=zone_detail
        )
