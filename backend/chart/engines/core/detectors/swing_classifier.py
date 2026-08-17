"""Swing Classifier - Classify swings as HH/HL/LH/LL.

CONTRACT:
- FACT DETECTION ONLY
- NO interpretation
- NO phase decisions

Label Classification: Classifies swings based on price relationships.
"""
from typing import List, Optional

from backend.chart.engines.core.schemas.swing import SwingPoint


class SwingClassifier:
    """Classify swings based on price relationships.
    
    Labels:
    - HH = Higher High (swing high above previous swing high)
    - HL = Higher Low (swing low above previous swing low)
    - LH = Lower High (swing high below previous swing high)
    - LL = Lower Low (swing low below previous swing low)
    """
    
    def classify(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """Classify swings with HH/HL/LH/LL labels."""
        if len(swings) < 2:
            return swings
        
        sorted_swings = sorted(swings, key=lambda s: s.index)
        
        # Ensure alternation
        alternating = self._enforce_alternation(sorted_swings)
        
        # Classify labels
        classified = self._classify_labels(alternating)
        
        return classified
    
    def _enforce_alternation(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """Ensure swings alternate between high and low."""
        alternating: List[SwingPoint] = []
        last_kind: Optional[str] = None
        
        for swing in swings:
            if swing.kind != last_kind:
                alternating.append(swing)
                last_kind = swing.kind
            else:
                # Same kind as last - keep the more extreme
                if swing.kind == "high" and swing.price > alternating[-1].price:
                    alternating[-1] = swing
                elif swing.kind == "low" and swing.price < alternating[-1].price:
                    alternating[-1] = swing
        
        return alternating
    
    def _classify_labels(self, swings: List[SwingPoint]) -> List[SwingPoint]:
        """Classify swings as HH/HL/LH/LL based on price relationships."""
        last_high: Optional[SwingPoint] = None
        last_low: Optional[SwingPoint] = None
        labeled: List[SwingPoint] = []
        
        for swing in swings:
            label = None
            
            if swing.kind == "high":
                if last_high is not None:
                    label = "HH" if swing.price > last_high.price else "LH"
                last_high = swing
            elif swing.kind == "low":
                if last_low is not None:
                    label = "HL" if swing.price > last_low.price else "LL"
                last_low = swing
            
            # Create new swing with label (keep all other fields as-is)
            labeled.append(SwingPoint(
                id=swing.id,
                index=swing.index,
                timestamp=swing.timestamp,
                price=swing.price,
                kind=swing.kind,
                label=label,
                degree=swing.degree,  # Preserve original degree
                was_demoted=swing.was_demoted,
                strength=swing.strength,
                valid=swing.valid,
                timeframe=swing.timeframe
            ))
        
        return labeled


def classify_swings(swings: List[SwingPoint]) -> List[SwingPoint]:
    """Functional API for swing classification (HH/HL/LH/LL labels only)."""
    classifier = SwingClassifier()
    return classifier.classify(swings)
