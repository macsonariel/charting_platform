"""Actionable Analyzer - Filter to what matters now.

This module provides the ActionableAnalyzer that processes all detected
levels and returns the 1-3 most actionable based on:
- Proximity to current price
- Significance (CHoCH > BOS > Protected > FVG > Liquidity)
- Confluence (multiple levels at same price)
- Bias alignment
"""
from typing import List, Optional
from dataclasses import dataclass

from backend.chart.engines.core.schemas.actionable import (
    ActionableLevel, ActionableContext, LEVEL_SIGNIFICANCE
)


@dataclass
class ActionableAnalyzerConfig:
    """Configuration for actionable analysis."""
    max_distance_percent: float = 3.0   # Only consider levels within 3%
    max_levels: int = 3                 # Return at most 3 levels
    confluence_threshold: float = 0.5   # % distance to count as confluence
    bias_alignment_bonus: float = 0.2   # Bonus for aligned levels
    proximity_weight: float = 0.3       # Weight for proximity in scoring


class ActionableAnalyzer:
    """Analyzes levels to find what matters now.
    
    Takes all detected levels (BOS, CHoCH, protected, FVG, liquidity)
    and filters to the most actionable based on scoring.
    """
    
    def __init__(self, config: Optional[ActionableAnalyzerConfig] = None):
        self.config = config or ActionableAnalyzerConfig()
    
    def analyze(
        self,
        current_price: float,
        bias: str,
        structure_breaks: List = None,
        character_changes: List = None,
        protected_levels: List = None,
        fair_value_gaps: List = None,
        liquidity_pools: List = None
    ) -> ActionableContext:
        """Analyze all levels and return actionable context.
        
        Args:
            current_price: Current market price
            bias: Market bias ("bullish", "bearish", "neutral")
            structure_breaks: List of StructureBreak objects
            character_changes: List of CharacterChange objects
            protected_levels: List of ProtectedLevel objects
            fair_value_gaps: List of FairValueGap objects
            liquidity_pools: List of LiquidityPool objects
            
        Returns:
            ActionableContext with top 1-3 levels and thesis
        """
        levels: List[ActionableLevel] = []
        
        # Collect from structure breaks (BOS)
        if structure_breaks:
            for sb in structure_breaks:
                # Only consider BOS (CHoCH handled separately)
                if getattr(sb, 'type', 'BOS') == 'BOS':
                    level = ActionableLevel.from_structure_break(sb, current_price, bias)
                    levels.append(level)
        
        # Collect from character changes (CHoCH)
        if character_changes:
            for cc in character_changes:
                # Create a mock object with same interface
                level = ActionableLevel(
                    level_type="choch",
                    price=cc.level,
                    distance_percent=abs(cc.level - current_price) / current_price * 100,
                    direction="above" if cc.level > current_price else "below",
                    action="Reversal zone - watch for confirmation",
                    significance=LEVEL_SIGNIFICANCE["choch"],
                    confluence_score=0.0,
                    total_score=LEVEL_SIGNIFICANCE["choch"],
                    source_id=cc.id,
                    bias_aligned=(
                        (bias == "bullish" and cc.direction == "up") or
                        (bias == "bearish" and cc.direction == "down") or
                        bias == "neutral"
                    )
                )
                levels.append(level)
        
        # Collect from protected levels (only active ones)
        if protected_levels:
            for pl in protected_levels:
                if not getattr(pl, 'broken', False):
                    level = ActionableLevel.from_protected_level(pl, current_price, bias)
                    levels.append(level)
        
        # Collect from FVGs (only unfilled)
        if fair_value_gaps:
            for fvg in fair_value_gaps:
                if not getattr(fvg, 'filled', False):
                    level = ActionableLevel.from_fvg(fvg, current_price, bias)
                    levels.append(level)
        
        # Collect from liquidity pools
        if liquidity_pools:
            for lp in liquidity_pools:
                if not getattr(lp, 'swept', False):
                    level = ActionableLevel.from_liquidity_pool(lp, current_price, bias)
                    levels.append(level)
        
        # Filter by proximity
        levels = [l for l in levels if l.distance_percent <= self.config.max_distance_percent]
        
        if not levels:
            return ActionableContext(
                primary_level=None,
                secondary_levels=[],
                current_thesis=self._generate_thesis(None, [], bias),
                bias=bias,
                confidence=0.0
            )
        
        # Calculate confluence scores
        levels = self._calculate_confluence(levels)
        
        # Calculate total scores
        levels = self._calculate_total_scores(levels)
        
        # Sort by total score (descending)
        levels.sort(key=lambda l: l.total_score, reverse=True)
        
        # Take top N
        top_levels = levels[:self.config.max_levels]
        
        # Split into primary and secondary
        primary = top_levels[0] if top_levels else None
        secondary = top_levels[1:] if len(top_levels) > 1 else []
        
        # Calculate confidence
        confidence = self._calculate_confidence(primary, secondary, bias)
        
        # Generate thesis
        thesis = self._generate_thesis(primary, secondary, bias)
        
        return ActionableContext(
            primary_level=primary,
            secondary_levels=secondary,
            current_thesis=thesis,
            bias=bias,
            confidence=confidence
        )
    
    def _calculate_confluence(self, levels: List[ActionableLevel]) -> List[ActionableLevel]:
        """Calculate confluence scores for overlapping levels."""
        for i, level in enumerate(levels):
            confluence = 0.0
            for j, other in enumerate(levels):
                if i == j:
                    continue
                # Check if levels are close (within threshold %)
                price_diff = abs(level.price - other.price) / level.price * 100
                if price_diff <= self.config.confluence_threshold:
                    # Add bonus based on other level's significance
                    confluence += other.significance * 0.3
            level.confluence_score = min(1.0, confluence)
        return levels
    
    def _calculate_total_scores(self, levels: List[ActionableLevel]) -> List[ActionableLevel]:
        """Calculate total score for each level."""
        for level in levels:
            # Base score from significance
            score = level.significance
            
            # Confluence bonus
            score += level.confluence_score * 0.3
            
            # Proximity bonus (closer = better)
            proximity_bonus = (1 - level.distance_percent / self.config.max_distance_percent) * self.config.proximity_weight
            score += proximity_bonus
            
            # Bias alignment bonus
            if level.bias_aligned:
                score += self.config.bias_alignment_bonus
            
            level.total_score = min(2.0, score)  # Cap at 2.0
        
        return levels
    
    def _calculate_confidence(
        self,
        primary: Optional[ActionableLevel],
        secondary: List[ActionableLevel],
        bias: str
    ) -> float:
        """Calculate overall confidence score."""
        if not primary:
            return 0.0
        
        confidence = 0.5  # Base
        
        # Primary level score contribution
        confidence += primary.total_score * 0.2
        
        # Confluence contribution
        if secondary:
            avg_confluence = sum(l.confluence_score for l in secondary) / len(secondary)
            confidence += avg_confluence * 0.1
        
        # Bias alignment contribution
        all_levels = [primary] + secondary
        aligned_count = sum(1 for l in all_levels if l.bias_aligned)
        confidence += (aligned_count / len(all_levels)) * 0.2
        
        return min(1.0, confidence)
    
    def _generate_thesis(
        self,
        primary: Optional[ActionableLevel],
        secondary: List[ActionableLevel],
        bias: str
    ) -> str:
        """Generate human-readable thesis statement."""
        if not primary:
            return "No actionable levels nearby. Wait for price to approach key levels."
        
        bias_text = {
            "bullish": "Bullish bias",
            "bearish": "Bearish bias",
            "neutral": "Neutral bias"
        }.get(bias, "Neutral bias")
        
        direction_text = "above" if primary.direction == "above" else "below"
        action_verb = {
            "bullish": "long entry" if primary.direction == "below" else "resistance test",
            "bearish": "short entry" if primary.direction == "above" else "support test",
            "neutral": "reaction"
        }.get(bias, "reaction")
        
        thesis = f"{bias_text}. "
        thesis += f"Key {primary.level_type.upper()} at {primary.price:,.2f} ({direction_text}, {primary.distance_percent:.1f}% away). "
        thesis += f"Watch for {action_verb}."
        
        if secondary:
            thesis += f" {len(secondary)} secondary level{'s' if len(secondary) > 1 else ''} nearby."
        
        return thesis


def analyze_actionable(
    current_price: float,
    bias: str,
    structure_breaks: List = None,
    character_changes: List = None,
    protected_levels: List = None,
    fair_value_gaps: List = None,
    liquidity_pools: List = None,
    config: Optional[ActionableAnalyzerConfig] = None
) -> ActionableContext:
    """Functional API for actionable analysis."""
    analyzer = ActionableAnalyzer(config)
    return analyzer.analyze(
        current_price=current_price,
        bias=bias,
        structure_breaks=structure_breaks,
        character_changes=character_changes,
        protected_levels=protected_levels,
        fair_value_gaps=fair_value_gaps,
        liquidity_pools=liquidity_pools
    )
