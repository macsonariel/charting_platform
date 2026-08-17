"""Narrative Package - Human-friendly market analysis generation.

This package transforms raw market data (MarketSnapshot) into
human-readable narratives, insights, and trading recommendations.

Components:
- ScenarioAnalyzer: Classifies market state (trending, ranging, reversal)
- NarrativeBuilder: Generates text narratives from scenarios
- InsightGenerator: Produces specific actionable insights

Usage:
    from backend.chart.engines.core.narrative import build_narrative, generate_insights
    
    snapshot = run_pipeline(candles, symbol, timeframe)
    narrative = build_narrative(snapshot)
    insights = generate_insights(snapshot)
    
    print(narrative.to_text())
    for insight in insights:
        print(f"{insight.priority.value}: {insight.message}")
"""

from backend.chart.engines.core.narrative.scenario_analyzer import (
    ScenarioAnalyzer,
    ScenarioResult,
    ScenarioFactor,
    MarketScenario,
)
from backend.chart.engines.core.narrative.narrative_builder import (
    NarrativeBuilder,
    Narrative,
    build_narrative,
)
from backend.chart.engines.core.narrative.insight_generator import (
    InsightGenerator,
    Insight,
    InsightType,
    InsightPriority,
    generate_insights,
)
from backend.chart.engines.core.narrative.templates import (
    NarrativeTemplate,
    get_template,
    TEMPLATES,
)

__all__ = [
    # Scenario Analysis
    "ScenarioAnalyzer",
    "ScenarioResult",
    "ScenarioFactor",
    "MarketScenario",
    
    # Narrative Building
    "NarrativeBuilder",
    "Narrative",
    "build_narrative",
    
    # Insight Generation
    "InsightGenerator",
    "Insight",
    "InsightType",
    "InsightPriority",
    "generate_insights",
    
    # Templates
    "NarrativeTemplate",
    "get_template",
    "TEMPLATES",
]
