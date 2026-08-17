"""Leg Analyzer - Detect and classify price legs.

Identifies legs between swing points and classifies them by type:
- Impulse: Strong directional move
- Corrective: Counter-trend pullback
- Consolidation: Sideways movement
- Compression: Tightening range
- Post-sweep: Reaction after liquidity sweep
"""
from typing import List, Optional, TYPE_CHECKING
from dataclasses import dataclass
import uuid

from backend.chart.engines.core.schemas.leg import Leg, LegType

if TYPE_CHECKING:
    from backend.chart.engines.core.schemas import SwingPoint, StructureBreak


class LegAnalyzer:
    """Analyzes and classifies price legs."""
    
    def __init__(self, timeframe: str = ""):
        self.timeframe = timeframe
        self._legs: List[Leg] = []
    
    def analyze(
        self,
        swings: List['SwingPoint'],
        breaks: List['StructureBreak'],
        sweeps: Optional[List] = None,
        candles: Optional[List] = None
    ) -> List[Leg]:
        """Analyze swings and create classified legs.
        
        Args:
            swings: Detected swing points
            breaks: Structure breaks for internal analysis
            sweeps: Liquidity sweeps for post-sweep detection
            candles: Raw candle data for aggression calculation
        
        Returns:
            List of classified Leg objects
        """
        if len(swings) < 2:
            return []
        
        self._legs = []
        sorted_swings = sorted(swings, key=lambda s: s.index)
        
        # Filter for EXTERNAL swings only - these define structural legs
        # Internal swings form inside the structure and don't create structural legs
        external_swings = [s for s in sorted_swings if getattr(s, 'degree', 'internal') == 'external']
        
        # If no external swings (or only one), fall back to all swings for minimal analysis
        if len(external_swings) < 2:
            external_swings = sorted_swings
        
        for i in range(len(external_swings) - 1):
            start = external_swings[i]
            end = external_swings[i + 1]
            
            leg = self._create_leg(start, end, candles)
            
            # Classify leg type
            if i > 0:
                prev_leg = self._legs[-1] if self._legs else None
                leg.leg_type = self._classify_leg(leg, prev_leg, sweeps)
                leg.retracement_depth = self._calc_retracement(leg, prev_leg)
            
            # Count internal structure
            leg.internal_swings = self._count_internal_swings(swings, start.index, end.index)
            leg.internal_breaks = self._count_internal_breaks(breaks, start.index, end.index)
            
            # Calculate aggression
            if candles:
                leg.candle_aggression = self._calc_aggression(candles, start.index, end.index)
            
            self._legs.append(leg)
        
        # Calculate impulse/correction ratios
        self._calc_impulse_ratios()
        
        return self._legs
    
    def _create_leg(
        self, 
        start: 'SwingPoint', 
        end: 'SwingPoint',
        candles: Optional[List] = None
    ) -> Leg:
        """Create a basic leg from two swing points."""
        direction = "bullish" if end.price > start.price else "bearish"
        
        # Get timestamps
        start_ts = getattr(start, 'timestamp', 0)
        end_ts = getattr(end, 'timestamp', 0)
        
        return Leg(
            id=f"leg_{uuid.uuid4().hex[:8]}",
            start_swing_id=start.id,
            end_swing_id=end.id,
            start_price=start.price,
            end_price=end.price,
            start_index=start.index,
            end_index=end.index,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            direction=direction,
            timeframe=self.timeframe
        )
    
    def _classify_leg(
        self, 
        leg: Leg, 
        prev_leg: Optional[Leg],
        sweeps: Optional[List] = None
    ) -> str:
        """Classify the leg type based on characteristics."""
        
        # Check for post-sweep reaction
        if sweeps:
            for sweep in sweeps:
                sweep_idx = getattr(sweep, 'index', 0)
                if leg.start_index - 3 <= sweep_idx <= leg.start_index:
                    return LegType.POST_SWEEP.value
        
        if not prev_leg:
            return LegType.IMPULSE.value
        
        # Compare to previous leg
        size_ratio = leg.size / prev_leg.size if prev_leg.size > 0 else 1.0
        
        # Consolidation: Very small movement
        if size_ratio < 0.3:
            return "consolidation"
        
        # Compression: Range tightening
        if prev_leg.candle_count > 0 and leg.candle_count > prev_leg.candle_count * 1.5:
            if size_ratio < 0.5:
                return "compression"
        
        # Corrective: Counter-direction or weak same-direction
        if leg.direction != prev_leg.direction:
            return LegType.CORRECTIVE.value
        
        # Impulse: Strong continuation
        if size_ratio >= 0.8 and leg.momentum >= prev_leg.momentum * 0.7:
            return LegType.IMPULSE.value
        
        # Default to corrective for weaker continuation
        return LegType.CORRECTIVE.value
    
    def _calc_retracement(self, leg: Leg, prev_leg: Optional[Leg]) -> float:
        """Calculate retracement depth relative to previous leg."""
        if not prev_leg or prev_leg.size == 0:
            return 0.0
        
        # Retracement only makes sense for opposing directions
        if leg.direction == prev_leg.direction:
            return 0.0
        
        retracement = leg.size / prev_leg.size
        return min(1.0, retracement)  # Cap at 100%
    
    def _count_internal_swings(
        self, 
        swings: List['SwingPoint'], 
        start_idx: int, 
        end_idx: int
    ) -> int:
        """Count swing points within the leg."""
        count = 0
        for swing in swings:
            if start_idx < swing.index < end_idx:
                count += 1
        return count
    
    def _count_internal_breaks(
        self, 
        breaks: List['StructureBreak'], 
        start_idx: int, 
        end_idx: int
    ) -> int:
        """Count structure breaks within the leg."""
        count = 0
        for brk in breaks:
            break_idx = getattr(brk, 'break_index', 0)
            if start_idx < break_idx < end_idx:
                count += 1
        return count
    
    def _calc_aggression(
        self, 
        candles: List, 
        start_idx: int, 
        end_idx: int
    ) -> float:
        """Calculate average candle aggression (body/range ratio)."""
        total = 0.0
        count = 0
        
        for i in range(start_idx, min(end_idx + 1, len(candles))):
            candle = candles[i]
            high = getattr(candle, 'high', 0)
            low = getattr(candle, 'low', 0)
            open_p = getattr(candle, 'open', 0)
            close = getattr(candle, 'close', 0)
            
            total_range = high - low
            if total_range > 0:
                body = abs(close - open_p)
                total += body / total_range
                count += 1
        
        return total / count if count > 0 else 0.0
    
    def _calc_impulse_ratios(self):
        """Calculate impulse/correction ratio for each leg."""
        if len(self._legs) < 3:
            return
        
        for i in range(1, len(self._legs) - 1):
            leg = self._legs[i]
            prev = self._legs[i - 1]
            next_leg = self._legs[i + 1]
            
            # Count impulse moves around this leg
            impulse_count = sum(1 for l in [prev, next_leg] if l.is_impulse)
            total = 2
            
            leg.impulse_correction_ratio = impulse_count / total
    
    # =========================================================================
    # STRUCTURE STATE TRACKING (for filtering system)
    # =========================================================================
    
    def get_structure_state(
        self,
        current_price: float,
        current_index: int,
        current_timestamp: int = 0,
        candles: Optional[List] = None
    ) -> dict:
        """Get active and previous leg for filtering.
        
        Returns:
            dict with:
            - active_leg: Current developing leg (last swing → current price)
            - previous_leg: Last completed leg
            - all_legs: List of all complete legs
        """
        complete_legs = [l for l in self._legs if l.is_complete]
        
        # Create or retrieve developing leg
        active_leg = self._create_developing_leg(
            current_price, current_index, current_timestamp, candles
        )
        
        previous_leg = complete_legs[-1] if complete_legs else None
        
        return {
            "active_leg": active_leg,
            "previous_leg": previous_leg,
            "all_legs": complete_legs
        }
    
    def _create_developing_leg(
        self, 
        current_price: float, 
        current_index: int,
        current_timestamp: int = 0,
        candles: Optional[List] = None
    ) -> Optional[Leg]:
        """Create a developing leg from last confirmed swing to current price.
        
        The developing leg has:
        - start_swing_id: Last confirmed swing
        - end_swing_id: None (not yet confirmed)
        - end_price: Current price
        - status: "developing"
        - high_price/low_price: Actual high/low of candles within leg
        """
        complete_legs = [l for l in self._legs if l.is_complete]
        
        if not complete_legs:
            return None
        
        last_leg = complete_legs[-1]
        
        # The developing leg starts from the end of the last complete leg
        direction = "bullish" if current_price > last_leg.end_price else "bearish"
        
        # Calculate high/low from candles within the leg range
        start_idx = last_leg.end_index
        high_price = max(last_leg.end_price, current_price)
        low_price = min(last_leg.end_price, current_price)
        
        if candles and start_idx < len(candles):
            for i in range(start_idx, len(candles)):
                candle = candles[i]
                high_price = max(high_price, candle.high)
                low_price = min(low_price, candle.low)
        
        return Leg(
            id=f"leg_dev_{uuid.uuid4().hex[:8]}",
            start_swing_id=last_leg.end_swing_id,
            end_swing_id=None,  # Not confirmed yet
            start_price=last_leg.end_price,
            end_price=current_price,
            start_index=last_leg.end_index,
            end_index=current_index,
            start_timestamp=last_leg.end_timestamp,
            end_timestamp=current_timestamp,
            high_price=high_price,
            low_price=low_price,
            direction=direction,
            leg_type="impulse",  # Default, will be classified when complete
            scope="swing",
            status="developing",
            timeframe=self.timeframe
        )
    
    def on_swing_confirmed(
        self,
        new_swing: 'SwingPoint',
        candles: Optional[List] = None
    ) -> Leg:
        """Handle when a new swing is confirmed.
        
        This is the state transition:
        1. The developing leg becomes complete
        2. A new developing leg starts from this swing
        
        Args:
            new_swing: The newly confirmed swing point
            candles: Candle data for aggression calculation
            
        Returns:
            The newly completed leg
        """
        # Get the last complete leg to find start point
        complete_legs = [l for l in self._legs if l.is_complete]
        
        if not complete_legs:
            # This is the first swing confirmation, can't create a leg yet
            return None
        
        last_leg = complete_legs[-1]
        
        # Create the new complete leg (was developing, now confirmed)
        new_complete_leg = Leg(
            id=f"leg_{uuid.uuid4().hex[:8]}",
            start_swing_id=last_leg.end_swing_id,
            end_swing_id=new_swing.id,
            start_price=last_leg.end_price,
            end_price=new_swing.price,
            start_index=last_leg.end_index,
            end_index=new_swing.index,
            start_timestamp=last_leg.end_timestamp,
            end_timestamp=getattr(new_swing, 'timestamp', 0),
            direction="bullish" if new_swing.price > last_leg.end_price else "bearish",
            leg_type="impulse",  # Will be classified
            scope="swing",
            status="complete",
            timeframe=self.timeframe
        )
        
        # Classify the new leg
        prev_leg = self._legs[-1] if self._legs else None
        new_complete_leg.leg_type = self._classify_leg(new_complete_leg, prev_leg)
        new_complete_leg.retracement_depth = self._calc_retracement(new_complete_leg, prev_leg)
        
        # Calculate aggression if candles provided
        if candles:
            new_complete_leg.candle_aggression = self._calc_aggression(
                candles, new_complete_leg.start_index, new_complete_leg.end_index
            )
        
        # Add to legs list
        self._legs.append(new_complete_leg)
        
        return new_complete_leg


def analyze_legs(
    swings: List['SwingPoint'],
    breaks: List['StructureBreak'],
    sweeps: Optional[List] = None,
    candles: Optional[List] = None,
    timeframe: str = "",
    current_price: float = 0.0
) -> List[Leg]:
    """Functional API for leg analysis.
    
    Args:
        swings: All swing points
        breaks: Structure breaks
        sweeps: Liquidity sweeps
        candles: Candle data for aggression
        timeframe: Timeframe string
        current_price: Current market price (for developing leg)
        
    Returns:
        List of legs including both complete and developing legs.
        The developing (active) leg has status="developing".
    """
    analyzer = LegAnalyzer(timeframe=timeframe)
    complete_legs = analyzer.analyze(swings, breaks, sweeps, candles)
    
    # Add developing leg if we have complete legs and current price
    if complete_legs and current_price > 0 and candles:
        current_index = len(candles) - 1
        current_timestamp = candles[-1].timestamp if candles else 0
        
        state = analyzer.get_structure_state(current_price, current_index, current_timestamp, candles)
        if state.get("active_leg"):
            complete_legs.append(state["active_leg"])
    
    return complete_legs
