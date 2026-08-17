"""HTF Swing Classifier - Classify swings as external based on HTF alignment.

CONTRACT:
- External swings on LTF are those that match swing points on HTF
- For 4H timeframe, Daily swing points define external swings
- For 1H timeframe, 4H swing points define external swings

Logic:
- Fetch HTF swing points
- Compare each LTF swing to HTF swings
- If a LTF swing matches an HTF swing (same kind, similar price, within HTF candle period)
- Tag the LTF swing as "external"
- All other swings remain "internal"
"""
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass

from backend.chart.engines.core.schemas.swing import SwingPoint
from backend.chart.engines.core.schemas.candle import Candle

logger = logging.getLogger(__name__)


# Timeframe hierarchy - maps LTF to its corresponding HTF
HTF_MAP: Dict[str, str] = {
    "1m": "5m",
    "5m": "15m",
    "15m": "1h",
    "30m": "1h",
    "1h": "4h",
    "4h": "1d",
    "1d": "1w",
    "1w": "1M",
}

# Approximate duration in milliseconds for each timeframe
TIMEFRAME_MS: Dict[str, int] = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
    "1w": 604_800_000,
    "1M": 2_592_000_000,  # ~30 days
}


def get_htf_for_timeframe(timeframe: str) -> Optional[str]:
    """Get the higher timeframe for a given timeframe.
    
    Args:
        timeframe: Current timeframe (e.g., "4h")
        
    Returns:
        Higher timeframe (e.g., "1d") or None if no HTF defined
    """
    return HTF_MAP.get(timeframe)


def get_timeframe_duration_ms(timeframe: str) -> int:
    """Get the duration of a timeframe in milliseconds."""
    return TIMEFRAME_MS.get(timeframe, 3_600_000)  # Default 1h


@dataclass
class HTFSwingMatch:
    """Result of matching an LTF swing to an HTF swing."""
    ltf_swing_id: str
    htf_swing_id: str
    price_diff_pct: float
    time_diff_ms: int


class HTFSwingClassifier:
    """Classify LTF swings as external based on HTF alignment.
    
    A swing on the LTF is classified as "external" if it matches
    a swing on the HTF. This creates a hierarchy where structural
    swings from higher timeframes are recognized on lower timeframes.
    
    Matching Criteria:
    - Same kind (high/low)
    - Price within tolerance (default 0.5%)
    - Timestamp within HTF candle duration * factor
    
    Distance Requirement:
    - External swings must be separated by at least min_swing_distance LTF swings
    - This ensures internal structure exists between external points
    """
    
    def __init__(
        self,
        price_tolerance_pct: float = 0.005,  # 0.5% price tolerance (more lenient)
        time_tolerance_factor: float = 2.0,   # HTF candle duration * factor
        min_swing_distance: int = 4,          # Minimum LTF swings between externals
    ):
        self.price_tolerance_pct = price_tolerance_pct
        self.time_tolerance_factor = time_tolerance_factor
        self.min_swing_distance = min_swing_distance
    
    def classify(
        self,
        ltf_swings: List[SwingPoint],
        htf_swings: List[SwingPoint],
        htf_timeframe: str
    ) -> List[SwingPoint]:
        """Classify LTF swings as external based on HTF swing matches.
        
        Each HTF swing can only mark ONE LTF swing as external (the best match).
        This prevents clusters of external swings on lower timeframes.
        
        Args:
            ltf_swings: Swing points from lower timeframe (to be classified)
            htf_swings: Swing points from higher timeframe (reference)
            htf_timeframe: The HTF timeframe string (e.g., "1d")
            
        Returns:
            Updated LTF swings with degree set to "external" or "internal"
        """
        logger.debug("Classifying %d LTF swings against %d HTF swings", len(ltf_swings), len(htf_swings) if htf_swings else 0)
        
        # Default all to internal first
        for swing in ltf_swings:
            swing.degree = "internal"
        
        if not htf_swings:
            logger.debug("No HTF swings provided; LTF swings remain internal")
            return ltf_swings
        
        # Get HTF candle duration for time matching
        htf_duration_ms = get_timeframe_duration_ms(htf_timeframe)
        time_tolerance_ms = int(htf_duration_ms * self.time_tolerance_factor)
        
        logger.debug("HTF=%s time_tolerance_ms=%d price_tolerance_pct=%.3f", htf_timeframe, time_tolerance_ms, self.price_tolerance_pct * 100)
        
        # For each HTF swing, find the BEST matching LTF swing (one-to-one mapping)
        # This prevents multiple LTF swings matching the same HTF swing
        used_ltf_ids: set = set()  # Track which LTF swings are already matched
        
        for htf_swing in htf_swings:
            best_ltf: Optional[SwingPoint] = None
            best_price_diff = float('inf')
            
            for ltf_swing in ltf_swings:
                # Skip if already matched to another HTF swing
                if ltf_swing.id in used_ltf_ids:
                    continue
                
                # Must be same kind
                if ltf_swing.kind != htf_swing.kind:
                    continue
                
                # Check time proximity
                time_diff = abs(ltf_swing.timestamp - htf_swing.timestamp)
                if time_diff > time_tolerance_ms:
                    continue
                
                # Check price proximity
                price_diff_pct = abs(ltf_swing.price - htf_swing.price) / htf_swing.price
                if price_diff_pct > self.price_tolerance_pct:
                    continue
                
                # This is a valid candidate - is it the best?
                if price_diff_pct < best_price_diff:
                    best_price_diff = price_diff_pct
                    best_ltf = ltf_swing
            
            # Mark the best match as external
            if best_ltf:
                best_ltf.degree = "external"
                used_ltf_ids.add(best_ltf.id)
                logger.debug("Matched HTF %s %.2f to LTF %.2f (%.3f%%)", htf_swing.kind, htf_swing.price, best_ltf.price, best_price_diff * 100)
        
        # Post-process: Enforce minimum distance between external swings
        # External swings that are too close together defeat the purpose
        ltf_swings = self._enforce_minimum_distance(ltf_swings)
        
        # Log summary
        external_count = sum(1 for s in ltf_swings if s.degree == "external")
        logger.debug("Classified %d/%d swings as external", external_count, len(ltf_swings))
        
        return ltf_swings
    
    def _enforce_minimum_distance(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """Build a clean alternating sequence of external swings with proper spacing.
        
        Requirements:
        1. External swings must ALTERNATE (H-L-H-L pattern)
        2. External swings must be separated by minimum distance
        
        Algorithm:
        - Start with all candidate externals (matched from HTF)
        - Build new sequence by selecting best candidates that satisfy both rules
        - Demote rejected candidates to internal
        """
        if self.min_swing_distance <= 0:
            return swings
        
        # Sort all swings by index
        sorted_swings = sorted(swings, key=lambda s: s.index)
        
        # Build index mapping: swing index → position in sorted list
        index_to_pos = {s.index: i for i, s in enumerate(sorted_swings)}
        
        # Get all candidate external swings sorted by index
        candidates = [s for s in sorted_swings if s.degree == "external"]
        
        if len(candidates) < 2:
            return swings
        
        logger.debug("Building alternating external sequence from %d candidates (min distance %d)", len(candidates), self.min_swing_distance)
        
        # Build clean alternating sequence
        kept_externals: List[SwingPoint] = []
        
        for candidate in candidates:
            # Check if this candidate can be added to our sequence
            can_add, reason = self._can_add_to_sequence(
                candidate, kept_externals, index_to_pos
            )
            
            if can_add:
                kept_externals.append(candidate)
            else:
                # Demote this candidate
                candidate.degree = "internal"
                logger.debug("Demoted %s %.2f: %s", candidate.kind, candidate.price, reason)
        
        logger.debug("Kept %d external swings after filtering", len(kept_externals))
        
        return swings
    
    def _can_add_to_sequence(
        self,
        candidate: SwingPoint,
        kept: List[SwingPoint],
        index_to_pos: dict
    ) -> tuple:
        """Check if a candidate can be added to the kept externals sequence.
        
        Returns:
            (can_add: bool, reason: str) - reason is only set if can_add is False
        """
        if not kept:
            # First one - always accept
            return True, ""
        
        last_kept = kept[-1]
        
        # Rule 1: Must alternate (different kind from last kept)
        if candidate.kind == last_kept.kind:
            # Same kind - check if candidate is more extreme
            if candidate.kind == "high" and candidate.price > last_kept.price:
                # New high is higher - replace the last one
                last_kept.degree = "internal"
                kept.pop()
                logger.debug("Replaced external high %.2f with %.2f", last_kept.price, candidate.price)
                return True, ""
            elif candidate.kind == "low" and candidate.price < last_kept.price:
                # New low is lower - replace the last one
                last_kept.degree = "internal"
                kept.pop()
                logger.debug("Replaced external low %.2f with %.2f", last_kept.price, candidate.price)
                return True, ""
            else:
                # Candidate is not more extreme - skip it
                return False, f"same kind as previous ({last_kept.kind}), not more extreme"
        
        # Rule 2: Must have minimum distance from last kept
        last_pos = index_to_pos.get(last_kept.index, 0)
        candidate_pos = index_to_pos.get(candidate.index, 0)
        swings_between = candidate_pos - last_pos - 1
        
        if swings_between < self.min_swing_distance:
            return False, f"too close to previous external ({swings_between} < {self.min_swing_distance} swings)"
        
        # All checks passed
        return True, ""
    
    def _find_htf_match(
        self,
        ltf_swing: SwingPoint,
        htf_swings: List[SwingPoint],
        time_tolerance_ms: int
    ) -> Optional[HTFSwingMatch]:
        """Find a matching HTF swing for an LTF swing.
        
        Matching criteria:
        1. Same kind (high/low)
        2. Price within tolerance
        3. Timestamp within tolerance
        
        Returns the best match (closest price) or None.
        """
        best_match: Optional[HTFSwingMatch] = None
        best_price_diff = float('inf')
        
        for htf_swing in htf_swings:
            # Must be same kind
            if htf_swing.kind != ltf_swing.kind:
                continue
            
            # Check time proximity
            time_diff = abs(ltf_swing.timestamp - htf_swing.timestamp)
            if time_diff > time_tolerance_ms:
                continue
            
            # Check price proximity
            price_diff_pct = abs(ltf_swing.price - htf_swing.price) / htf_swing.price
            if price_diff_pct > self.price_tolerance_pct:
                continue
            
            # This is a valid match - check if it's the best one
            if price_diff_pct < best_price_diff:
                best_price_diff = price_diff_pct
                best_match = HTFSwingMatch(
                    ltf_swing_id=ltf_swing.id,
                    htf_swing_id=htf_swing.id,
                    price_diff_pct=price_diff_pct,
                    time_diff_ms=time_diff
                )
        
        return best_match


def classify_swings_from_htf(
    ltf_swings: List[SwingPoint],
    htf_swings: List[SwingPoint],
    htf_timeframe: str,
    ltf_timeframe: str = "",
    price_tolerance_pct: float = 0.005,
) -> List[SwingPoint]:
    """Functional API for HTF swing classification.
    
    Args:
        ltf_swings: Swing points from lower timeframe
        htf_swings: Swing points from higher timeframe
        htf_timeframe: The HTF timeframe string
        ltf_timeframe: The LTF timeframe string (used to calculate min distance)
        price_tolerance_pct: Price tolerance for matching (default 0.5%)
        
    Returns:
        Updated LTF swings with degree classification
    """
    # Calculate minimum swing distance based on timeframe ratio
    # External swings should be at least 1 HTF candle apart (in LTF terms)
    min_distance = _calculate_min_distance(ltf_timeframe, htf_timeframe)
    
    classifier = HTFSwingClassifier(
        price_tolerance_pct=price_tolerance_pct,
        min_swing_distance=min_distance
    )
    return classifier.classify(ltf_swings, htf_swings, htf_timeframe)


def _calculate_min_distance(ltf_timeframe: str, htf_timeframe: str) -> int:
    """Calculate minimum swing distance based on timeframe ratio.
    
    External swings should be separated by enough structure to be meaningful.
    We use the ratio of HTF to LTF as a guide.
    
    Examples:
    - 4H → 1D: ratio 6:1, so min 4-6 swings between externals
    - 1H → 4H: ratio 4:1, so min 3-4 swings between externals
    - 15m → 1H: ratio 4:1, so min 3-4 swings between externals
    """
    if not ltf_timeframe or not htf_timeframe:
        return 4  # Default
    
    ltf_duration = get_timeframe_duration_ms(ltf_timeframe)
    htf_duration = get_timeframe_duration_ms(htf_timeframe)
    
    if ltf_duration == 0:
        return 4
    
    # Ratio of how many LTF candles fit in one HTF candle
    ratio = htf_duration / ltf_duration
    
    # Minimum distance is roughly 2/3 of the ratio (ensures meaningful structure)
    # But at least 3 swings (H-L-H or L-H-L minimum)
    min_dist = max(3, int(ratio * 0.66))
    
    logger.debug("Minimum swing distance %d for %s -> %s (ratio %.1f)", min_dist, ltf_timeframe, htf_timeframe, ratio)
    
    return min_dist


async def fetch_htf_swings(
    symbol: str,
    ltf_timeframe: str,
    ltf_candle_count: int
) -> Optional[List[SwingPoint]]:
    """Fetch and detect swings from the higher timeframe.
    
    Args:
        symbol: Trading symbol
        ltf_timeframe: The lower timeframe (to determine HTF)
        ltf_candle_count: Number of candles on LTF (to calculate HTF lookback)
        
    Returns:
        List of HTF swing points, or None if no HTF defined
    """
    htf = get_htf_for_timeframe(ltf_timeframe)
    if not htf:
        return None
    
    # Calculate how many HTF candles we need
    # Ratio of timeframe durations
    ltf_duration = get_timeframe_duration_ms(ltf_timeframe)
    htf_duration = get_timeframe_duration_ms(htf)
    ratio = ltf_duration / htf_duration if htf_duration > 0 else 0.25
    
    # We need enough HTF candles to cover the same time period
    htf_candle_count = max(50, int(ltf_candle_count * ratio) + 10)
    
    try:
        # Lazy imports to avoid circular dependencies
        from backend.chart.data.chart_data_fetcher import async_fetch_and_convert
        from backend.chart.engines.core.detectors import detect_swings, score_swings
        from backend.chart.engines.core.detectors.swing_classifier import classify_swings
        from backend.chart.engines.core.detectors.swing_detector import SwingDetectorConfig
        
        # Fetch HTF candles
        htf_candles = await async_fetch_and_convert(symbol, htf, htf_candle_count)
        
        if not htf_candles:
            logger.warning("No HTF candles for %s %s", symbol, htf)
            return None
        
        # Detect HTF swings with appropriate lookback
        lookback_map = {
            "5m": 3, "15m": 3, "30m": 4, "1h": 4,
            "4h": 5, "1d": 5, "1w": 7, "1M": 7
        }
        lookback = lookback_map.get(htf, 5)
        config = SwingDetectorConfig(lookback=lookback)
        
        htf_swings = detect_swings(htf_candles, htf, config)
        htf_swings = score_swings(htf_candles, htf_swings)
        htf_swings = classify_swings(htf_swings)
        
        logger.debug("Fetched %d swings from %s", len(htf_swings), htf)
        return htf_swings
        
    except Exception as error:
        logger.warning("Failed to fetch HTF swings for %s %s: %s", symbol, htf, error)
        return None
