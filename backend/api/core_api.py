"""Core Analysis API Endpoint.

Provides:
- /api/core/analysis - MAIN: Full 8-section analysis with liquidity (use this)
- /api/core/analyze - DEBUG ONLY: Raw core pipeline output (for development)

Note: Analysis uses viewport_candles × 2 for lookback to ensure consistent
results based on what the user sees on their chart.

HTF External Classification:
- For 4H timeframe, Daily swing points define external swings
- External swings on LTF are those that match swing points on HTF
"""
import asyncio
import logging
import os
import time

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from types import SimpleNamespace

from backend.chart.data.chart_data_fetcher import async_fetch_and_convert as fetch_and_convert
from backend.chart.engines.core import run_pipeline
from backend.chart.engines.core.detectors.htf_swing_classifier import (
    get_htf_for_timeframe, fetch_htf_swings
)
from backend.chart.rendering import RenderOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)


CORE_VIEW_SCHEMA_VERSION = "1.0"
CORE_MTF_TIMEFRAMES = ("5m", "15m", "1h", "4h", "1d")
CORE_TIMEFRAME_ORDER = ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M")
CORE_SNAPSHOT_CACHE_TTL_SECONDS = 30

_snapshot_cache: Dict[tuple, Dict[str, Any]] = {}
_snapshot_pending: Dict[tuple, asyncio.Task] = {}


class CoreDataUnavailable(RuntimeError):
    """Raised when a market-data provider cannot supply Core input."""


def _snapshot_cache_key(symbol: str, timeframe: str, periods: int) -> tuple:
    source = os.getenv("DATA_SOURCE", "binance").lower()
    return source, symbol.upper(), timeframe, periods


async def _compute_core_snapshot(symbol: str, timeframe: str, periods: int) -> Dict[str, Any]:
    try:
        candles = await fetch_and_convert(symbol, timeframe, periods)
    except Exception as error:
        raise CoreDataUnavailable("Market data provider is unavailable") from error

    if not candles:
        raise CoreDataUnavailable(f"No candle data is available for {symbol}")

    htf_swings = await fetch_htf_swings(symbol, timeframe, periods)
    snapshot = run_pipeline(candles, symbol, timeframe, htf_swings)
    return {
        "snapshot": snapshot,
        "candles": candles,
        "htf_swings": htf_swings,
        "cached_at": time.monotonic(),
    }


async def _get_core_snapshot(symbol: str, timeframe: str, periods: int) -> Dict[str, Any]:
    """Return one cached authoritative snapshot to every API projection."""
    key = _snapshot_cache_key(symbol, timeframe, periods)
    cached = _snapshot_cache.get(key)
    if cached and time.monotonic() - cached["cached_at"] <= CORE_SNAPSHOT_CACHE_TTL_SECONDS:
        return cached

    pending = _snapshot_pending.get(key)
    if pending:
        return await pending

    task = asyncio.create_task(_compute_core_snapshot(symbol, timeframe, periods))
    _snapshot_pending[key] = task
    try:
        bundle = await task
        _snapshot_cache[key] = bundle
        return bundle
    finally:
        _snapshot_pending.pop(key, None)


def _clear_core_snapshot_cache() -> None:
    """Test and operational hook for invalidating derived snapshots."""
    _snapshot_cache.clear()


def _normalize_direction(value: Optional[str]) -> str:
    """Return the direction vocabulary used by the UI contract."""
    normalized = (value or "").strip().lower()
    if normalized in {"bullish", "up", "uptrend"}:
        return "bullish"
    if normalized in {"bearish", "down", "downtrend"}:
        return "bearish"
    return "neutral"


def _normalize_market_state(value: Optional[str]) -> str:
    """Return a stable, presentation-safe market state."""
    normalized = (value or "").strip().lower()
    aliases = {
        "trend_confirmed": "trending",
        "continuation": "trending",
        "breakout": "breakout",
        "structure_shift": "transitional",
        "reversal_setup": "reversal",
        "pullback": "pullback",
        "exhaustion": "exhaustion",
        "unknown": "neutral",
    }
    if normalized in {"trending", "ranging", "transitional", "reversal", "neutral"}:
        return normalized
    return aliases.get(normalized, "neutral")


def _snapshot_confidence(snapshot) -> Dict[str, Any]:
    """Serialize confidence owned by the canonical regime."""
    raw_score = snapshot.regime.confidence if snapshot.regime else None
    source = "core_regime"

    if raw_score is None and snapshot.actionable:
        raw_score = snapshot.actionable.confidence
        source = "actionable_context"

    if raw_score is None and snapshot.analysis:
        raw_score = snapshot.analysis.clarity_score / 100
        source = "clarity_score"

    try:
        numeric_score = float(raw_score if raw_score is not None else 0)
    except (TypeError, ValueError):
        numeric_score = 0

    if numeric_score <= 1:
        numeric_score *= 100

    return {
        "score": round(max(0, min(100, numeric_score))),
        "source": source,
    }


def _nearest_protected_levels(snapshot) -> tuple[Optional[float], Optional[float]]:
    """Return the nearest intact protected high and low around current price."""
    highs = [
        level.price for level in snapshot.protected_levels
        if not level.broken and level.kind == "high" and level.price > snapshot.current_price
    ]
    lows = [
        level.price for level in snapshot.protected_levels
        if not level.broken and level.kind == "low" and level.price < snapshot.current_price
    ]
    return (min(highs) if highs else None, max(lows) if lows else None)


def _directional_invalidation(
    snapshot,
    analysis,
    protected_high: Optional[float],
    protected_low: Optional[float],
) -> Optional[float]:
    """Choose a fallback invalidation on the side that disproves the bias."""
    if analysis and analysis.invalidation_price:
        return analysis.invalidation_price

    bias = _normalize_direction(snapshot.bias)
    if bias == "bullish":
        return protected_low
    if bias == "bearish":
        return protected_high

    candidates = [price for price in (protected_high, protected_low) if price is not None]
    return min(candidates, key=lambda price: abs(price - snapshot.current_price)) if candidates else None


def _serialize_recent_events(snapshot) -> List[Dict[str, Any]]:
    events = [event.to_dict() for event in snapshot.recent_events]
    return sorted(events, key=lambda event: event.get("timestamp") or 0, reverse=True)[:10]


def _build_core_view_model(snapshot, mtf: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the sole response contract consumed by both analysis panels."""
    analysis = snapshot.analysis
    analysis_dict = analysis.to_dict() if analysis else {}
    confidence = _snapshot_confidence(snapshot)
    protected_high, protected_low = _nearest_protected_levels(snapshot)
    invalidation_price = _directional_invalidation(
        snapshot, analysis, protected_high, protected_low
    )

    regime = snapshot.regime
    direction = _normalize_direction(regime.direction if regime else None)
    bias = _normalize_direction(regime.bias if regime else None)
    state = _normalize_market_state(regime.state if regime else None)
    phase = regime.phase if regime else "unknown"

    intact_pools = [pool for pool in snapshot.liquidity_pools if not pool.swept]
    liquidity_above = sorted(
        pool.price for pool in intact_pools
        if pool.side == "buy_side" and pool.price > snapshot.current_price
    )[:5]
    liquidity_below = sorted(
        (
            pool.price for pool in intact_pools
            if pool.side == "sell_side" and pool.price < snapshot.current_price
        ),
        reverse=True,
    )[:5]

    recent_events = _serialize_recent_events(snapshot)
    last_event = recent_events[0] if recent_events else None

    swing_structure = [
        {
            "type": "H" if swing.kind == "high" else "L",
            "price": swing.price,
            "degree": swing.degree,
        }
        for swing in sorted(snapshot.swings, key=lambda swing: swing.index)[-6:]
    ]

    sr_data = {"support": [], "resistance": [], "nearest_support": None, "nearest_resistance": None}
    if snapshot.sr_analysis:
        sr_data = {
            "support": [
                {
                    "high": zone.high,
                    "low": zone.low,
                    "midpoint": zone.midpoint,
                    "strength": zone.strength,
                    "touches": zone.touch_count,
                    "timestamp": zone.timestamp,
                    "break_count": zone.break_count,
                }
                for zone in snapshot.sr_analysis.support_zones[:5]
                if not zone.invalidated
            ],
            "resistance": [
                {
                    "high": zone.high,
                    "low": zone.low,
                    "midpoint": zone.midpoint,
                    "strength": zone.strength,
                    "touches": zone.touch_count,
                    "timestamp": zone.timestamp,
                    "break_count": zone.break_count,
                }
                for zone in snapshot.sr_analysis.resistance_zones[:5]
                if not zone.invalidated
            ],
            "nearest_support": (
                snapshot.sr_analysis.nearest_support.midpoint
                if snapshot.sr_analysis.nearest_support else None
            ),
            "nearest_resistance": (
                snapshot.sr_analysis.nearest_resistance.midpoint
                if snapshot.sr_analysis.nearest_resistance else None
            ),
        }

    range_position = None
    if snapshot.range_position:
        range_position = snapshot.range_position.to_dict()
        range_position["percentage"] = round(snapshot.range_position.position_ratio * 100, 1)

    fvgs = [
        {
            "direction": gap.direction,
            "high": gap.high,
            "low": gap.low,
            "midpoint": gap.midpoint,
            "strength": gap.strength,
            "filled": gap.filled,
        }
        for gap in snapshot.fair_value_gaps if not gap.filled
    ][:5]

    thesis = (
        snapshot.actionable.current_thesis
        if snapshot.actionable and snapshot.actionable.current_thesis
        else analysis.summary if analysis and analysis.summary
        else "No clear structural thesis is available."
    )

    model = {
        "schema_version": CORE_VIEW_SCHEMA_VERSION,
        "engine": "core",
        "source": "market_snapshot",
        "success": True,
        "status": "ready",
        "symbol": snapshot.symbol,
        "timeframe": snapshot.timeframe,
        "as_of": snapshot.timestamp,
        "generated_at": int(time.time() * 1000),
        "current_price": snapshot.current_price,
        "confidence": confidence,
        "thesis": thesis,
        "structure": {
            "direction": direction,
            "bias": bias,
            "state": state,
            "phase": phase,
            "direction_source": regime.direction_source if regime else "unavailable",
            "source_timeframe": regime.source_timeframe if regime else snapshot.timeframe,
            "swing_degree": regime.swing_degree if regime else "none",
            "fallback_used": regime.fallback_used if regime else False,
        },
        "regime": regime.to_dict() if regime else None,
        "levels": {"high": protected_high, "low": protected_low},
        "liquidity": {"above": liquidity_above, "below": liquidity_below},
        "invalidation": {
            "price": invalidation_price,
            "signal": (
                analysis.structural_shift_signal
                if analysis and analysis.structural_shift_signal
                else "No invalidation signal available"
            ),
        },
        "structure_events": {
            "bos_count": len(snapshot.structure_breaks),
            "choch_count": len(snapshot.character_changes),
            "total_swings": len(snapshot.swings),
            "moves": len(snapshot.moves),
        },
        "direction_swings": _get_authoritative_direction_swings(snapshot),
        "swing_structure": swing_structure,
        "sr_zones": sr_data,
        "range_position": range_position,
        "fvgs": fvgs,
        "recent_events": recent_events,
        "last_event": last_event,
        "analysis": analysis_dict,
        "mtf": mtf or {
            "status": "unavailable",
            "timeframes": {},
            "alignment_percentage": 0,
            "aligned_count": 0,
            "total_analyzed": 0,
        },
    }

    model["quick_overview"] = {
        "bias": bias,
        "state": state,
        "zone": range_position.get("zone") if range_position else None,
        "protected_high": protected_high,
        "protected_low": protected_low,
        "liquidity_above": liquidity_above[0] if liquidity_above else None,
        "liquidity_below": liquidity_below[0] if liquidity_below else None,
        "invalidation": invalidation_price,
        "current_price": snapshot.current_price,
        "as_of": snapshot.timestamp,
    }
    return model


def _mtf_result_from_snapshot(snapshot, timeframe: str, base_timeframe: str) -> Dict[str, Any]:
    regime = snapshot.regime
    return {
        "timeframe": timeframe,
        "direction": _normalize_direction(regime.direction if regime else None),
        "state": _normalize_market_state(regime.state if regime else None),
        "is_current": timeframe == base_timeframe,
        "bias": _normalize_direction(regime.bias if regime else None),
        "confidence": round(regime.confidence * 100) if regime else 0,
        "direction_source": regime.direction_source if regime else "unavailable",
    }


async def _analyze_mtf_timeframe(symbol: str, timeframe: str, base_timeframe: str, periods: int) -> Dict[str, Any]:
    try:
        bundle = await _get_core_snapshot(symbol, timeframe, periods)
        candles = bundle["candles"]
        if not candles or len(candles) < 10:
            return {
                "timeframe": timeframe,
                "direction": "unknown",
                "state": "insufficient_data",
                "is_current": timeframe == base_timeframe,
            }

        snapshot = bundle["snapshot"]
        return _mtf_result_from_snapshot(snapshot, timeframe, base_timeframe)
    except Exception as error:
        logger.warning("MTF analysis failed for %s: %s", timeframe, error)
        return {
            "timeframe": timeframe,
            "direction": "error",
            "state": "error",
            "is_current": timeframe == base_timeframe,
        }


async def _build_mtf_confluence(
    symbol: str,
    base_timeframe: str,
    periods: int,
    base_snapshot=None,
) -> Dict[str, Any]:
    timeframes = sorted(
        {*CORE_MTF_TIMEFRAMES, base_timeframe},
        key=lambda value: (
            CORE_TIMEFRAME_ORDER.index(value)
            if value in CORE_TIMEFRAME_ORDER
            else len(CORE_TIMEFRAME_ORDER)
        ),
    )
    timeframes_to_fetch = [
        timeframe for timeframe in timeframes
        if not (base_snapshot is not None and timeframe == base_timeframe)
    ]
    results = list(await asyncio.gather(*(
        _analyze_mtf_timeframe(symbol, timeframe, base_timeframe, periods)
        for timeframe in timeframes_to_fetch
    )))
    if base_snapshot is not None:
        results.append(_mtf_result_from_snapshot(base_snapshot, base_timeframe, base_timeframe))
    results.sort(key=lambda result: timeframes.index(result["timeframe"]))
    valid = [result for result in results if result["direction"] not in {"unknown", "error"}]
    bullish_count = sum(result["direction"] == "bullish" for result in valid)
    bearish_count = sum(result["direction"] == "bearish" for result in valid)
    neutral_count = sum(result["direction"] == "neutral" for result in valid)
    aligned_count = max(bullish_count, bearish_count, neutral_count) if valid else 0
    alignment_percentage = round(aligned_count / len(valid) * 100) if valid else 0

    if not valid:
        direction = "unknown"
        status = "unavailable"
    elif bullish_count == aligned_count and bullish_count > bearish_count:
        direction = "bullish"
        status = "ready" if len(valid) == len(results) else "partial"
    elif bearish_count == aligned_count and bearish_count > bullish_count:
        direction = "bearish"
        status = "ready" if len(valid) == len(results) else "partial"
    else:
        direction = "mixed"
        status = "ready" if len(valid) == len(results) else "partial"

    return {
        "success": bool(valid),
        "status": status,
        "symbol": symbol,
        "base_timeframe": base_timeframe,
        "timeframes": {result["timeframe"]: result for result in results},
        "direction": direction,
        "alignment_percentage": alignment_percentage,
        "aligned_count": aligned_count,
        "total_analyzed": len(valid),
        "counts": {
            "bullish": bullish_count,
            "bearish": bearish_count,
            "neutral": neutral_count,
        },
    }


def snapshot_to_dict(snapshot) -> Dict[str, Any]:
    """Convert MarketSnapshot to JSON-serializable dict."""
    result = {
        "symbol": snapshot.symbol,
        "timeframe": snapshot.timeframe,
        "timestamp": snapshot.timestamp,
        "current_price": snapshot.current_price,
        "bias": snapshot.bias,
        "regime": snapshot.regime.to_dict() if snapshot.regime else None,
        "swings": [asdict(s) for s in snapshot.swings],
        "external_high": asdict(snapshot.external_high) if snapshot.external_high else None,
        "external_low": asdict(snapshot.external_low) if snapshot.external_low else None,
        "structure_breaks": [asdict(sb) for sb in snapshot.structure_breaks],
        "character_changes": [asdict(cc) for cc in snapshot.character_changes],
        "legs": [asdict(l) for l in snapshot.legs],
        "protected_levels": [asdict(pl) for pl in snapshot.protected_levels],
        "ranges": [asdict(r) for r in snapshot.ranges],
        "liquidity_pools": [asdict(lp) for lp in snapshot.liquidity_pools],
        "recent_sweeps": [asdict(sw) for sw in snapshot.recent_sweeps],
        "fair_value_gaps": [asdict(fvg) for fvg in snapshot.fair_value_gaps],
        "drawing_zones": [z.to_dict() for z in snapshot.drawing_zones] if snapshot.drawing_zones else [],
        "moves": [asdict(m) for m in snapshot.moves] if snapshot.moves else [],
    }
    
    # Add direction analysis if available
    if snapshot.direction_analysis:
        result["direction_analysis"] = snapshot.direction_analysis.to_dict()
    
    # Add range position if available
    if snapshot.range_position:
        result["range_position"] = snapshot.range_position.to_dict()
    
    # Add S/R analysis if available
    if snapshot.sr_analysis:
        result["sr_analysis"] = {
            "support_zones": [asdict(z) for z in snapshot.sr_analysis.support_zones],
            "resistance_zones": [asdict(z) for z in snapshot.sr_analysis.resistance_zones],
            "all_zones": [asdict(z) for z in snapshot.sr_analysis.all_zones],
            "nearest_support": asdict(snapshot.sr_analysis.nearest_support) if snapshot.sr_analysis.nearest_support else None,
            "nearest_resistance": asdict(snapshot.sr_analysis.nearest_resistance) if snapshot.sr_analysis.nearest_resistance else None,
            "support_count": snapshot.sr_analysis.support_count,
            "resistance_count": snapshot.sr_analysis.resistance_count,
        }
    
    # Add recent events if available
    if snapshot.recent_events:
        result["recent_events"] = [e.to_dict() for e in snapshot.recent_events]
    
    # Add actionable context if available
    if snapshot.actionable:
        result["actionable"] = snapshot.actionable.to_dict()
    
    # Add market analysis if available
    if snapshot.analysis:
        result["analysis"] = snapshot.analysis.to_dict()
    
    # Add interpreter result if available
    if snapshot.interpretation:
        result["interpretation"] = snapshot.interpretation
    
    return result


def _get_authoritative_direction_swings(snapshot) -> dict:
    """Serialize the exact swing pattern used by the canonical regime."""
    analysis = snapshot.direction_analysis
    if not analysis:
        return {
            "swings": [],
            "direction": "neutral",
            "source": "unavailable",
            "source_timeframe": snapshot.timeframe,
            "using_external": False,
        }
    return {
        "swings": [
            {
                "index": swing.index,
                "timestamp": swing.timestamp,
                "kind": swing.kind,
                "price": swing.price,
                "degree": swing.degree,
                "label": swing.label,
            }
            for swing in analysis.pattern_swings
        ],
        "direction": analysis.direction,
        "source": analysis.source,
        "source_timeframe": analysis.source_timeframe,
        "using_external": analysis.swing_degree == "external",
        "fallback_used": analysis.fallback_used,
        "quality": analysis.quality,
        "total_swings": analysis.total_swings_analyzed,
    }

@router.get("/api/core/analyze")
async def analyze_core(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    timeframe: str = Query("1h", description="Chart timeframe"),
    periods: int = Query(300, ge=50, le=2000, description="Number of candles"),
):
    """
    [DEBUG ONLY] Raw core pipeline output.
    
    WARNING: This endpoint is for development/debugging only.
    Use /api/core/analysis for production analysis.
    
    Returns raw swings, breaks, legs, etc. in neutral terminology.
    """
    try:
        bundle = await _get_core_snapshot(symbol, timeframe, periods)
        candles = bundle["candles"]
        htf_swings = bundle["htf_swings"]
        snapshot = bundle["snapshot"]
        
        # Add HTF info to meta
        htf = get_htf_for_timeframe(timeframe)
        external_count = sum(1 for s in snapshot.swings if s.degree == "external")
        
        return {
            "success": True,
            "data": snapshot_to_dict(snapshot),
            "meta": {
                "candle_count": len(candles),
                "current_price": candles[-1].close if candles else 0,
                "htf_timeframe": htf,
                "htf_swings_count": len(htf_swings) if htf_swings else 0,
                "external_swings_count": external_count,
            }
        }
        
    except CoreDataUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Raw Core analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Core market-structure analysis failed"
        )


@router.get("/api/core/analysis")
async def core_analysis(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    timeframe: str = Query("1h", description="Chart timeframe"),
    viewport_candles: int = Query(None, ge=25, le=1000, description="Visible candles on chart (analysis uses 2x this)"),
    periods: int = Query(None, ge=50, le=2000, description="Override: exact candle count (ignores viewport_candles)"),
):
    """
    [MAIN ENDPOINT] Core 8-Section Market Analysis.
    
    Returns human-readable analysis organized into 8 sections:
    - Section 1: Market Context (external range, HTF direction)
    - Section 2: Structure (local structure, protected levels)
    - Section 3: Liquidity (buy/sell side pools)
    - etc.
    
    Periods Calculation:
    - If viewport_candles is provided: uses viewport_candles × 2
    - If periods is provided: uses exact value (for debugging)
    - If neither: defaults to 300
    
    This ensures analysis is based on what the user sees plus extra context.
    """
    try:
        # Calculate actual periods to use
        if periods is not None:
            # Explicit override - use exact value
            actual_periods = periods
        elif viewport_candles is not None:
            # Viewport-based: use 2x what user sees
            actual_periods = viewport_candles * 2
        else:
            # Default fallback
            actual_periods = 300
        
        bundle = await _get_core_snapshot(symbol, timeframe, actual_periods)
        candles = bundle["candles"]
        snapshot = bundle["snapshot"]
        analysis = snapshot.analysis

        # Compatibility projection of already-detected liquidity facts. No
        # detector or analyzer is rerun at the API boundary.
        buy_side_pools = [pool for pool in snapshot.liquidity_pools if pool.side == "buy_side"]
        sell_side_pools = [pool for pool in snapshot.liquidity_pools if pool.side == "sell_side"]
        intact_pools = [pool for pool in snapshot.liquidity_pools if not pool.swept]
        swept_pools = [pool for pool in snapshot.liquidity_pools if pool.swept]
        if snapshot.regime and snapshot.regime.bias == "bullish":
            targets = [pool for pool in intact_pools if pool.side == "buy_side" and pool.price > snapshot.current_price]
            next_target = min(targets, key=lambda pool: pool.price, default=None)
            trend_side = "buy_side"
        elif snapshot.regime and snapshot.regime.bias == "bearish":
            targets = [pool for pool in intact_pools if pool.side == "sell_side" and pool.price < snapshot.current_price]
            next_target = max(targets, key=lambda pool: pool.price, default=None)
            trend_side = "sell_side"
        else:
            next_target = min(
                intact_pools,
                key=lambda pool: abs(pool.price - snapshot.current_price),
                default=None,
            )
            trend_side = ""
        liquidity = SimpleNamespace(
            buy_side_pools=buy_side_pools,
            sell_side_pools=sell_side_pools,
            intact_pools=intact_pools,
            swept_pools=swept_pools,
            total_intact=len(intact_pools),
            total_swept=len(swept_pools),
            next_target=next_target,
            trend_liquidity_side=trend_side,
        )
        
        # Build response
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": snapshot.current_price,
            "regime": snapshot.regime.to_dict() if snapshot.regime else None,
            
            # 8-Section Analysis (using flat MarketAnalysis attributes)
            "section_1_context": {
                "htf_direction": analysis.htf_direction or "neutral",
                "htf_direction_detail": analysis.htf_direction_detail or "",
                "direction_source": analysis.direction_source or "unavailable",
                "direction_source_timeframe": analysis.direction_source_timeframe or timeframe,
                "external_range": analysis.external_range or f"{analysis.external_low:,.2f} to {analysis.external_high:,.2f}",
                "htf_leg": analysis.htf_leg or "developing",
            },
            "section_2_structure": {
                "local_structure": analysis.local_structure or "unknown",
                "protected_count": analysis.protected_count,
                "protected_levels": analysis.protected_levels or "None",
                "invalidated_count": analysis.invalidated_count,
                "recent_event": analysis.recent_event or "No recent events",
            },
            "section_3_liquidity": {
                # Filter to show pools that are actually above/below current price
                "buy_side_liquidity": f"Above: {', '.join([f'{p.price:,.2f}' for p in sorted([p for p in liquidity.buy_side_pools if p.price > snapshot.current_price and not p.swept], key=lambda x: x.price)[:3]])}",
                "sell_side_liquidity": f"Below: {', '.join([f'{p.price:,.2f}' for p in sorted([p for p in liquidity.sell_side_pools if p.price < snapshot.current_price and not p.swept], key=lambda x: -x.price)[:3]])}",
                "liquidity_remaining": f"{liquidity.total_intact} untouched pools ({len([p for p in liquidity.buy_side_pools if p.price > snapshot.current_price and not p.swept])} above, {len([p for p in liquidity.sell_side_pools if p.price < snapshot.current_price and not p.swept])} below)",
                "next_target": f"{liquidity.next_target.price:,.2f} ({liquidity.next_target.side})" if liquidity.next_target else "None",
                "trend_liquidity": liquidity.trend_liquidity_side or "No trend liquidity detected",
            },
            "section_4_levels": {
                "valid_zones": analysis.valid_zones or f"{len(snapshot.protected_levels)} protected levels, {len(snapshot.fair_value_gaps)} active FVGs",
                "invalid_zones": analysis.invalid_zones or "None",
                "nearest_reaction": analysis.nearest_reaction or "N/A",
            },
            "section_5_momentum": {
                "impulse_strength": analysis.impulse_strength or "N/A",
                "correction_character": analysis.correction_character or "N/A",
                "volatility_trend": analysis.volatility_trend or "Normal",
                "momentum_aligned": analysis.momentum_aligned or "Unknown",
            },
            "section_6_direction": {
                "bias": analysis.directional_bias or "neutral",
                "reasoning": analysis.bias_reasoning or "",
                "path": analysis.path_of_least_resistance or "",
                "confidence": analysis.confidence_level or "low",
            },
            "section_7_invalidation": {
                "swing": analysis.invalidation_swing or "N/A",
                "signal": analysis.structural_shift_signal or "",
            },
            "section_8_projection": {
                "if_reaches": analysis.if_price_reaches or "",
                "next_area": analysis.next_area_of_interest or "",
                "bullish_case": analysis.bullish_scenario or "",
                "bearish_case": analysis.bearish_scenario or "",
            },
            
            # Core Data Summary
            "core_data": {
                "swing_count": len(snapshot.swings),
                "external_swings": len([s for s in snapshot.swings if s.degree == "external"]),
                "internal_swings": len([s for s in snapshot.swings if s.degree == "internal"]),
                "structure_breaks": len(snapshot.structure_breaks),
                "character_changes": len(snapshot.character_changes),
                "legs": len(snapshot.legs),
                "protected_levels": len(snapshot.protected_levels),
                "liquidity_pools": {
                    "total": len(liquidity.buy_side_pools) + len(liquidity.sell_side_pools),
                    "buy_side": len(liquidity.buy_side_pools),
                    "sell_side": len(liquidity.sell_side_pools),
                    "intact": liquidity.total_intact,
                    "swept": liquidity.total_swept,
                },
                "fair_value_gaps": len(snapshot.fair_value_gaps),
            },
            
            # Compatibility keys all serialize the exact pattern selected by
            # the canonical direction detector; the API does not reinterpret.
            "direction_swings": _get_authoritative_direction_swings(snapshot),
            "htf_direction_swings": _get_authoritative_direction_swings(snapshot),
            "current_direction_swings": _get_authoritative_direction_swings(snapshot),
            
            # Full liquidity pools for debugging (filtered by price position)
            "liquidity_pools_detail": {
                "current_price": snapshot.current_price,
                # Buy-side: pools ABOVE current price, sorted by proximity (nearest first)
                "buy_side": [{"price": p.price, "type": p.pool_type, "strength": p.strength, "swept": p.swept} 
                            for p in sorted([p for p in liquidity.buy_side_pools if p.price > snapshot.current_price], 
                                           key=lambda x: x.price)[:5]],
                # Sell-side: pools BELOW current price, sorted by proximity (nearest first)
                "sell_side": [{"price": p.price, "type": p.pool_type, "strength": p.strength, "swept": p.swept} 
                             for p in sorted([p for p in liquidity.sell_side_pools if p.price < snapshot.current_price], 
                                            key=lambda x: -x.price)[:5]],
            },
            
            # S/R Zones (clustered swing points as zones)
            "sr_zones": {
                "support_zones": [
                    {"high": z.high, "low": z.low, "midpoint": z.midpoint, "strength": z.strength, 
                     "touches": z.touch_count, "intact": z.is_intact}
                    for z in (snapshot.sr_analysis.support_zones if snapshot.sr_analysis else [])[:5]
                ],
                "resistance_zones": [
                    {"high": z.high, "low": z.low, "midpoint": z.midpoint, "strength": z.strength,
                     "touches": z.touch_count, "intact": z.is_intact}
                    for z in (snapshot.sr_analysis.resistance_zones if snapshot.sr_analysis else [])[:5]
                ],
                "nearest_support": (snapshot.sr_analysis.nearest_support.midpoint 
                                   if snapshot.sr_analysis and snapshot.sr_analysis.nearest_support else None),
                "nearest_resistance": (snapshot.sr_analysis.nearest_resistance.midpoint 
                                      if snapshot.sr_analysis and snapshot.sr_analysis.nearest_resistance else None),
                "support_count": snapshot.sr_analysis.support_count if snapshot.sr_analysis else 0,
                "resistance_count": snapshot.sr_analysis.resistance_count if snapshot.sr_analysis else 0,
            },
            
            "meta": {
                "candle_count": len(candles),
                "source": "core_engine",
            }
        }
        
    except CoreDataUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Detailed Core analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Core analysis failed"
        )


@router.get("/api/core/summary")
async def core_summary(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    timeframe: str = Query("1h", description="Chart timeframe"),
    periods: int = Query(300, ge=50, le=2000, description="Number of candles"),
):
    """Versioned Core view model consumed by both analysis panels."""
    try:
        bundle = await _get_core_snapshot(symbol, timeframe, periods)
        snapshot = bundle["snapshot"]

        mtf = await _build_mtf_confluence(
            symbol,
            timeframe,
            min(periods, 150),
            base_snapshot=snapshot,
        )
        return _build_core_view_model(snapshot, mtf)

    except CoreDataUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Core summary failed")
        raise HTTPException(
            status_code=500,
            detail="Core summary is unavailable"
        )


@router.get("/api/core/render")
async def core_render(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    timeframe: str = Query("1h", description="Chart timeframe"),
    periods: int = Query(300, ge=50, le=2000, description="Number of candles"),
    zone_index: int = Query(0, description="Zone index to display (0 = most recent, -1 = live zone)"),
    show_all_zones: bool = Query(False, description="Show all zones instead of filtering"),
):
    """
    Zone-Filtered Rendering Data.
    
    Returns drawing data filtered to only show elements within the active zone.
    This is the primary endpoint for the chart renderer.
    
    The RenderOrchestrator filters all drawings (swings, FVGs, structure events,
    liquidity, etc.) to only show within the selected zone's boundaries.
    
    Args:
        zone_index: Which zone to show (0 = most recent, 1 = previous, etc.)
        show_all_zones: If True, show all zones without filtering
    """
    try:
        bundle = await _get_core_snapshot(symbol, timeframe, periods)
        candles = bundle["candles"]
        snapshot = bundle["snapshot"]
        
        # Create render orchestrator and set zones
        orchestrator = RenderOrchestrator()
        
        # Debug: Check drawing zones from snapshot
        # Use the zones from the snapshot
        if snapshot.drawing_zones:
            from backend.chart.rendering import DrawingZone, ZoneDirection
            zones = []
            for z in snapshot.drawing_zones:
                if hasattr(z, 'to_dict'):
                    # Already a DrawingZone object
                    zones.append(z)
                else:
                    # Convert from dict
                    zones.append(DrawingZone(
                        id=z.get('id', ''),
                        direction=ZoneDirection(z.get('direction', 'bullish')),
                        start_timestamp=z.get('start_timestamp', 0),
                        start_price=z.get('start_price', 0),
                        start_index=z.get('start_index', 0),
                        start_swing_id=z.get('start_swing_id', ''),
                        start_kind=z.get('start_kind', ''),
                        end_timestamp=z.get('end_timestamp', 0),
                        end_price=z.get('end_price', 0),
                        end_index=z.get('end_index', 0),
                        end_swing_id=z.get('end_swing_id', ''),
                        end_kind=z.get('end_kind', ''),
                        zone_high=z.get('zone_high', 0),
                        zone_low=z.get('zone_low', 0),
                        zone_high_index=z.get('zone_high_index', 0),
                        zone_low_index=z.get('zone_low_index', 0),
                        candle_count=z.get('candle_count', 0),
                        swing_count=z.get('swing_count', 0),
                    ))
            orchestrator.set_zones(zones)
        
        # Handle live zone (zone_index = -1)
        # Live zone = from end of prev_zone to current candle
        is_live_zone = zone_index == -1
        
        if is_live_zone and orchestrator.zones:
            # Create synthetic live zone from end of prev_zone to last candle
            prev_zone = orchestrator.zones[0]  # Most recent completed zone
            last_candle_index = len(candles) - 1
            last_candle = candles[-1] if candles else None
            
            # Create a synthetic DrawingZone for the live zone
            live_zone = DrawingZone(
                id="live_zone",
                direction=ZoneDirection.BULLISH if prev_zone.end_kind == "low" else ZoneDirection.BEARISH,
                start_timestamp=prev_zone.end_timestamp,
                start_price=prev_zone.end_price,
                start_index=prev_zone.end_index,
                start_swing_id=prev_zone.end_swing_id,
                start_kind=prev_zone.end_kind,
                end_timestamp=last_candle.timestamp if last_candle else 0,
                end_price=last_candle.close if last_candle else 0,
                end_index=last_candle_index,
                end_swing_id="current",
                end_kind="current",
                zone_high=max(c.high for c in candles[prev_zone.end_index:]) if prev_zone.end_index < len(candles) else 0,
                zone_low=min(c.low for c in candles[prev_zone.end_index:]) if prev_zone.end_index < len(candles) else 0,
                candle_count=last_candle_index - prev_zone.end_index + 1,
                swing_count=0,
            )
            
            # Set the live zone as active (temporarily add it)
            orchestrator.set_live_zone(live_zone)
        elif is_live_zone:
            # No completed zones, show all data
            orchestrator.show_all_zones = True
        else:
            # Set active zone and filtering mode
            orchestrator.set_active_zone(zone_index)
            orchestrator.show_all_zones = show_all_zones
        
        # Get filtered data
        filtered_data = orchestrator.filter_snapshot(snapshot)
        
        # Add S/R zones (not filtered by zone)
        if snapshot.sr_analysis:
            filtered_data["sr_zones"] = {
                "support": [
                    {"high": z.high, "low": z.low, "midpoint": z.midpoint, "strength": z.strength, "touches": z.touch_count, "timestamp": z.timestamp, "break_count": z.break_count}
                    for z in snapshot.sr_analysis.support_zones[:5] if not z.invalidated
                ],
                "resistance": [
                    {"high": z.high, "low": z.low, "midpoint": z.midpoint, "strength": z.strength, "touches": z.touch_count, "timestamp": z.timestamp, "break_count": z.break_count}
                    for z in snapshot.sr_analysis.resistance_zones[:5] if not z.invalidated
                ],
                "nearest_support": snapshot.sr_analysis.nearest_support.midpoint if snapshot.sr_analysis.nearest_support else None,
                "nearest_resistance": snapshot.sr_analysis.nearest_resistance.midpoint if snapshot.sr_analysis.nearest_resistance else None
            }
        
        # Add zone navigation info with proper naming
        zone_info = orchestrator.get_zone_info(candles)
        actual_zone_index = zone_index if not is_live_zone else -1
        filtered_data["zone_nav"] = {
            "current_index": actual_zone_index,
            "current_name": "live" if is_live_zone else orchestrator.get_zone_name(zone_index),
            "total_zones": len(orchestrator.zones),
            "has_older": True,  # Can always go to prev from live
            "has_newer": not is_live_zone and zone_index > 0,
            "is_live": is_live_zone,
        }
        filtered_data["zone_info"] = zone_info
        
        # Add zone summary for UI
        filtered_data["zone_summary"] = orchestrator.get_zone_summary()
        
        return {
            "success": True,
            "data": filtered_data,
            "meta": {
                "candle_count": len(candles),
                "zone_index": zone_index,
                "show_all_zones": show_all_zones,
            }
        }
        
    except CoreDataUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Core render projection failed")
        raise HTTPException(
            status_code=500,
            detail="Core rendering data is unavailable"
        )


@router.get("/api/core/zone-visibility")
async def get_zone_visibility(
    symbol: str = Query("BTCUSDT", description="Trading pair"),
    timeframe: str = Query("1h", description="Timeframe"),
    periods: int = Query(200, ge=50, le=2000, description="Number of candles"),
) -> Dict[str, Any]:
    """Get dynamic zone visibility based on current price position.
    
    Returns which zones should be visible and what drawing types to show:
    - Active zone: All drawings
    - Previous zone: All drawings if price within range
    - Scanned zones: Extending drawings only (FVG, protected levels, etc.)
    """
    try:
        from backend.chart.rendering import (
            calculate_visible_zones,
            get_zone_visibility_summary,
        )
        
        bundle = await _get_core_snapshot(symbol, timeframe, periods)
        candles = bundle["candles"]
        snapshot = bundle["snapshot"]
        
        # Get current price
        current_price = candles[-1].close if candles else 0
        
        # Calculate visible zones
        zones = snapshot.drawing_zones if snapshot.drawing_zones else []
        visibility_summary = get_zone_visibility_summary(zones, current_price)
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "visibility": visibility_summary,
        }
        
    except CoreDataUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Core MTF confluence failed")
        raise HTTPException(
            status_code=500,
            detail="Zone visibility is unavailable"
        )


@router.get("/api/core/mtf-confluence")
async def mtf_confluence(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    base_timeframe: str = Query("1h", description="Current chart timeframe"),
    periods: int = Query(100, ge=50, le=500, description="Number of candles per timeframe"),
):
    """Return objective multi-timeframe alignment, or 503 if none is available."""
    try:
        result = await _build_mtf_confluence(symbol, base_timeframe, periods)
        if not result["success"]:
            raise HTTPException(
                status_code=503,
                detail="Multi-timeframe analysis is currently unavailable",
            )
        return result

    except HTTPException:
        raise
    except Exception:
        logger.exception("Core zone visibility failed")
        raise HTTPException(
            status_code=500,
            detail="Multi-timeframe analysis failed"
        )
