"""Range - Price range and level models."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class PriceRange:
    """Price Range - Consolidation area.
    
    Defined by external high and low.
    Contains internal structure.
    
    Strength Scoring (0-1):
    - Duration (longer = more significant)
    - Boundary touches (more = stronger)
    - Active status (not broken)
    """
    id: str
    high: float
    low: float
    equilibrium: float          # Midpoint (50%)
    premium_zone: float         # Above equilibrium (75%)
    discount_zone: float        # Below equilibrium (25%)
    start_timestamp: int
    end_timestamp: Optional[int] = None
    start_index: int = 0
    end_index: Optional[int] = None
    active: bool = True         # False when broken
    compression: float = 0.0    # Volatility within range
    timeframe: str = ""
    duration_candles: int = 0   # How many candles in range
    boundary_touches: int = 0   # Times price touched high/low
    strength: float = 0.5       # 0-1 significance score
    
    @property
    def size(self) -> float:
        return self.high - self.low
    
    def is_in_premium(self, price: float) -> bool:
        """True if price is above equilibrium."""
        return price > self.equilibrium
    
    def is_in_discount(self, price: float) -> bool:
        """True if price is below equilibrium."""
        return price < self.equilibrium
    
    @property
    def is_active(self) -> bool:
        """True if range hasn't been broken."""
        return self.active


@dataclass
class ProtectedLevel:
    """Protected Level - Swing level that defines structure.
    
    A protected level remains valid ONLY until price breaks it.
    
    Protected High: Resistance until broken → becomes support
    Protected Low: Support until broken → becomes resistance
    
    Strength Scoring (0-1):
    - Source swing degree (external > internal)
    - Touch count (more tests = stronger)
    - Recency (newer = more relevant)
    """
    id: str
    price: float
    kind: str                   # "high" or "low"
    swing_id: str               # Source swing
    index: int
    timestamp: int
    timeframe: str = ""
    broken: bool = False        # True when price closes beyond
    break_timestamp: Optional[int] = None
    swing_degree: str = "internal"  # "external" or "internal"
    touch_count: int = 1        # Times price approached without break
    strength: float = 0.5       # 0-1 importance score
    
    @property
    def is_valid(self) -> bool:
        """True if level has not been broken."""
        return not self.broken
    
    @property
    def is_protected_high(self) -> bool:
        return self.kind == "high" and not self.broken
    
    @property
    def is_protected_low(self) -> bool:
        return self.kind == "low" and not self.broken
    
    @property
    def is_external(self) -> bool:
        return self.swing_degree == "external"

