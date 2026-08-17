"""Narrative API - Endpoints for human-friendly market analysis."""
from fastapi import APIRouter, Query, HTTPException

from backend.api.core_api import CoreDataUnavailable, _get_core_snapshot
from backend.chart.engines.core.narrative import build_narrative, generate_insights


router = APIRouter(tags=["Narrative Analysis"])


@router.get("/api/narrative")
async def get_narrative(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    timeframe: str = Query("1h", description="Chart timeframe"),
    periods: int = Query(200, description="Number of candles to analyze"),
):
    """Get human-friendly narrative analysis.
    
    Returns:
    - Scenario classification (trending, ranging, reversal)
    - Summary text
    - Detailed analysis
    - Action recommendations
    - Risk assessment
    - Key levels
    """
    try:
        snapshot = (await _get_core_snapshot(symbol, timeframe, periods))["snapshot"]
        
        # Build narrative
        narrative = build_narrative(snapshot)
        
        # Generate insights
        insights = generate_insights(snapshot)
        
        return {
            "success": True,
            "data": {
                "symbol": narrative.symbol,
                "timeframe": narrative.timeframe,
                "scenario": narrative.scenario,
                "confidence": round(narrative.confidence, 1),
                "bias": narrative.bias,
                "summary": narrative.summary,
                "details": narrative.details,
                "action": narrative.action,
                "risk": narrative.risk,
                "key_levels": narrative.key_levels,
                "factors": narrative.factors,
                "insights": [i.to_dict() for i in insights],
            },
            "meta": {
                "symbol": symbol,
                "timeframe": timeframe,
                "periods": periods,
                "current_price": snapshot.current_price,
            }
        }
        
    except CoreDataUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/api/narrative/text")
async def get_narrative_text(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    timeframe: str = Query("1h", description="Chart timeframe"),
    periods: int = Query(200, description="Number of candles to analyze"),
):
    """Get narrative as plain text for display/printing."""
    try:
        snapshot = (await _get_core_snapshot(symbol, timeframe, periods))["snapshot"]
        
        # Build narrative
        narrative = build_narrative(snapshot)
        
        return {
            "success": True,
            "text": narrative.to_text(),
            "meta": {
                "symbol": symbol,
                "timeframe": timeframe,
            }
        }
        
    except CoreDataUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/api/insights")
async def get_insights(
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    timeframe: str = Query("1h", description="Chart timeframe"),
    periods: int = Query(200, description="Number of candles to analyze"),
):
    """Get actionable trading insights.
    
    Returns prioritized list of insights like:
    - Entry zones
    - Exit targets
    - Stop levels
    - Structure signals
    """
    try:
        snapshot = (await _get_core_snapshot(symbol, timeframe, periods))["snapshot"]
        
        # Generate insights
        insights = generate_insights(snapshot)
        
        # Group by priority
        high = [i.to_dict() for i in insights if i.priority.value == "high"]
        medium = [i.to_dict() for i in insights if i.priority.value == "medium"]
        low = [i.to_dict() for i in insights if i.priority.value == "low"]
        
        return {
            "success": True,
            "data": {
                "total": len(insights),
                "high_priority": high,
                "medium_priority": medium,
                "low_priority": low,
                "all": [i.to_dict() for i in insights],
            },
            "meta": {
                "symbol": symbol,
                "timeframe": timeframe,
                "current_price": snapshot.current_price,
            }
        }
        
    except CoreDataUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
