"""Canonical interpretation of swing-derived Core facts."""
from typing import TYPE_CHECKING, Iterable

from backend.chart.engines.core.schemas.regime import MarketRegime

if TYPE_CHECKING:
    from backend.chart.engines.core.schemas.snapshot import MarketSnapshot


def _event_direction(event) -> str:
    return "bullish" if event.direction == "up" else "bearish"


def _latest(items: Iterable):
    values = list(items)
    return max(values, key=lambda item: item.break_timestamp) if values else None


def _bos_streak(snapshot: "MarketSnapshot") -> int:
    breaks = sorted(snapshot.structure_breaks, key=lambda event: event.break_timestamp)
    if not breaks:
        return 0
    direction = breaks[-1].direction
    streak = 0
    for event in reversed(breaks):
        if event.direction != direction:
            break
        streak += 1
    return streak


def analyze_regime(snapshot: "MarketSnapshot") -> MarketRegime:
    """Produce the sole direction/bias/state/phase/confidence interpretation.

    The input is a completed fact snapshot. No candle-pattern detection occurs
    here; every structural decision is based on the swing-derived facts already
    present on the snapshot.
    """
    direction_analysis = snapshot.direction_analysis
    direction = direction_analysis.direction if direction_analysis else "neutral"
    direction_source = direction_analysis.source if direction_analysis else "unavailable"
    source_timeframe = direction_analysis.source_timeframe if direction_analysis else snapshot.timeframe
    swing_degree = direction_analysis.swing_degree if direction_analysis else "none"
    fallback_used = direction_analysis.fallback_used if direction_analysis else False

    breaks = sorted(snapshot.structure_breaks, key=lambda event: event.break_timestamp)
    changes = sorted(
        (
            event for event in snapshot.character_changes
            if not getattr(event, "invalidated", False)
        ),
        key=lambda event: event.break_timestamp,
    )
    latest_break = _latest(breaks)
    latest_change = _latest(changes)
    latest_structural_event = _latest([*breaks, *changes])

    recent_events = sorted(
        [*breaks, *changes],
        key=lambda event: event.break_timestamp,
    )[-5:]
    if recent_events:
        bullish = sum(event.direction == "up" for event in recent_events)
        bearish = sum(event.direction == "down" for event in recent_events)
        if bullish > bearish:
            bias = "bullish"
        elif bearish > bullish:
            bias = "bearish"
        else:
            bias = _event_direction(recent_events[-1])
    else:
        bias = direction if direction in {"bullish", "bearish"} else "neutral"

    active_ranges = [price_range for price_range in snapshot.ranges if price_range.active]
    active_range = max(active_ranges, key=lambda item: item.start_index) if active_ranges else None
    unsuperseded_change = bool(
        latest_change
        and (not latest_break or latest_change.break_timestamp > latest_break.break_timestamp)
    )
    range_is_current = bool(
        active_range
        and (
            not latest_structural_event
            or latest_structural_event.break_timestamp < active_range.start_timestamp
        )
    )

    aligned_breaks = [
        event for event in breaks[-3:]
        if _event_direction(event) == direction
    ]
    if unsuperseded_change:
        state = "reversal"
    elif range_is_current:
        state = "ranging"
    elif direction in {"bullish", "bearish"} and len(aligned_breaks) >= 2:
        state = "trending"
    elif latest_structural_event:
        state = "transitional"
    elif active_range:
        state = "ranging"
    else:
        state = "unknown"

    if state == "trending":
        phase = "markup" if bias == "bullish" else "markdown"
    elif state == "reversal":
        phase = "accumulation" if bias == "bullish" else "distribution"
    elif state == "ranging":
        phase = "accumulation" if bias == "bullish" else "distribution" if bias == "bearish" else "consolidation"
    elif state == "transitional":
        phase = "transition"
    else:
        phase = "neutral"

    pattern_count = len(direction_analysis.pattern_swings) if direction_analysis else 0
    if pattern_count >= 4:
        direction_factor = 0.88 if swing_degree == "external" else 0.74
        if direction == "neutral":
            direction_factor = 0.5
    else:
        direction_factor = 0.2

    if recent_events:
        majority = max(
            sum(event.direction == "up" for event in recent_events),
            sum(event.direction == "down" for event in recent_events),
        ) / len(recent_events)
        structure_factor = 0.35 + (majority * 0.55)
    else:
        structure_factor = 0.2
    if unsuperseded_change:
        structure_factor = 0.85 if getattr(latest_change, "confirmed", False) else 0.65

    if state == "trending":
        state_factor = 0.85
    elif state == "reversal":
        state_factor = 0.8 if getattr(latest_change, "confirmed", False) else 0.62
    elif state == "ranging":
        state_factor = active_range.strength if active_range else 0.55
    elif state == "transitional":
        state_factor = 0.45
    else:
        state_factor = 0.2

    evidence_factor = min(
        1.0,
        min(len(snapshot.swings) / 8, 1.0) * 0.5
        + min(len(recent_events) / 4, 1.0) * 0.3
        + min(len(snapshot.active_protected_levels) / 2, 1.0) * 0.2,
    )
    confidence = (
        direction_factor * 0.35
        + structure_factor * 0.35
        + state_factor * 0.2
        + evidence_factor * 0.1
    )

    reasons = []
    if direction_analysis:
        reasons.append(
            f"{direction_analysis.direction_detail} from "
            f"{direction_analysis.source.replace('_', ' ')}"
        )
    if unsuperseded_change:
        reasons.append(
            f"Latest valid CHoCH is {_event_direction(latest_change)} and not superseded by BOS"
        )
    elif breaks:
        reasons.append(f"{len(aligned_breaks)}/3 recent BOS align with {direction} direction")
    if range_is_current:
        reasons.append("Current price remains inside a swing-confirmed structural range")
    if direction in {"bullish", "bearish"} and bias not in {direction, "neutral"}:
        confidence -= 0.12
        reasons.append(f"Short-term {bias} bias disagrees with {direction} structural direction")
    if fallback_used:
        reasons.append("Direction fell back because external swings were insufficient")

    return MarketRegime(
        direction=direction,
        bias=bias,
        state=state,
        phase=phase,
        confidence=max(0.0, min(1.0, confidence)),
        direction_source=direction_source,
        source_timeframe=source_timeframe,
        swing_degree=swing_degree,
        fallback_used=fallback_used,
        reasons=reasons,
        confidence_factors={
            "direction": direction_factor,
            "structure": structure_factor,
            "state": state_factor,
            "evidence": evidence_factor,
        },
    )


def regime_interpretation(snapshot: "MarketSnapshot", regime: MarketRegime) -> dict:
    """Return the former interpreter contract as a view of ``regime``."""
    rating = "high" if regime.confidence >= 0.7 else "medium" if regime.confidence >= 0.4 else "low"
    narrative = ". ".join(regime.reasons)
    context = {
        "timestamp": snapshot.timestamp,
        "timeframe": snapshot.timeframe,
        "current_price": snapshot.current_price,
        "htf_bias": regime.direction,
        "ltf_bias": regime.bias,
        "aligned": regime.direction == regime.bias and regime.direction != "neutral",
        "direction_source": regime.direction_source,
        "source_timeframe": regime.source_timeframe,
    }
    return {
        "state": regime.state.upper(),
        "bias": regime.bias.upper(),
        "phase": regime.phase.upper(),
        "confidence": regime.confidence,
        "bos_streak": _bos_streak(snapshot),
        "choch_count": len(snapshot.character_changes),
        "event_count": (
            len(snapshot.structure_breaks)
            + len(snapshot.character_changes)
            + len(snapshot.recent_sweeps)
        ),
        "narrative": narrative,
        "full_state": {
            "name": "core_regime",
            "state": regime.state.upper(),
            "bias": regime.bias.upper(),
            "phase": regime.phase.upper(),
            "confidence": {
                "score": round(regime.confidence, 3),
                "rating": rating,
                "factors": dict(regime.confidence_factors),
            },
            "context": context,
            "narrative": {"current_thesis": narrative},
            "event_count": (
                len(snapshot.structure_breaks)
                + len(snapshot.character_changes)
                + len(snapshot.recent_sweeps)
            ),
        },
    }
