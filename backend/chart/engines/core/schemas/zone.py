"""Zone - Supply/Demand Zones.

Supply and demand zones are areas of price where institutional
order flow residue remains from previous activity.
"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ZoneType(str, Enum):
    """Type of zone."""
    SUPPLY = "supply"   # Selling interest (resistance)
    DEMAND = "demand"   # Buying interest (support)


class ZoneStatus(str, Enum):
    """Current status of zone."""
    VALID = "valid"         # Untested, active
    TESTED = "tested"       # Touched but not broken
    MITIGATED = "mitigated" # Partially filled
    BROKEN = "broken"       # Price passed through


@dataclass
class SupplyDemandZone:
    """A supply or demand zone.
    
    Attributes:
        id: Unique identifier
        zone_type: "supply" or "demand"
        high: Upper bound of zone
        low: Lower bound of zone
        origin_index: Candle index where zone formed
        origin_timestamp: Timestamp of formation
        status: Current validity status
        strength: 0.0-1.0 strength score
    """
    id: str
    zone_type: str          # "supply" or "demand"
    high: float
    low: float
    origin_index: int
    origin_timestamp: int
    status: str = "valid"   # "valid", "tested", "mitigated", "broken"
    strength: float = 0.5
    timeframe: str = ""
    
    @property
    def mid(self) -> float:
        """Midpoint of zone."""
        return (self.high + self.low) / 2
    
    @property
    def size(self) -> float:
        """Size of zone."""
        return self.high - self.low
    
    @property
    def is_supply(self) -> bool:
        return self.zone_type == "supply"
    
    @property
    def is_demand(self) -> bool:
        return self.zone_type == "demand"
    
    @property
    def is_valid(self) -> bool:
        return self.status == "valid"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "zone_type": self.zone_type,
            "high": self.high,
            "low": self.low,
            "mid": self.mid,
            "size": self.size,
            "origin_index": self.origin_index,
            "origin_timestamp": self.origin_timestamp,
            "status": self.status,
            "strength": self.strength,
            "timeframe": self.timeframe,
        }
