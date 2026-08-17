"""Market Analyzer - 8 Section Trader Q&A.

Analyzes MarketSnapshot and produces answers organized into 8 sections.
"""
from typing import TYPE_CHECKING

from backend.chart.engines.core.schemas.analysis import MarketAnalysis

if TYPE_CHECKING:
    from backend.chart.engines.core.schemas import MarketSnapshot


class MarketAnalyzer:
    """Produces 8-section market analysis.
    
    NOTE: This analyzer READS from schemas populated by detectors.
    It does NOT compute direction or range position - those are
    now handled by direction_detector and range_detector.
    """
    
    def analyze(self, snapshot: 'MarketSnapshot') -> MarketAnalysis:
        """Analyze snapshot and produce complete 8-section analysis."""
        
        # Section 1: Market Context
        s1 = self._analyze_context(snapshot)
        
        # Section 2: Structure
        s2 = self._analyze_structure(snapshot)
        
        # Section 3: Liquidity
        s3 = self._analyze_liquidity(snapshot)
        
        # Section 4: Important Levels
        s4 = self._analyze_levels(snapshot)
        
        # Section 5: Momentum & Volatility
        s5 = self._analyze_momentum(snapshot, s2)
        
        # Section 6: Probabilistic Direction
        s6 = self._analyze_direction(snapshot)
        
        # Section 7: Invalidation Logic
        s7 = self._analyze_invalidation(snapshot, s6)
        
        # Section 8: Projection
        s8 = self._analyze_projection(snapshot, s4, s6)
        
        # Overall
        state, clarity = self._analyze_overall(snapshot)
        summary = self._build_summary(s1, s6, state)
        
        return MarketAnalysis(
            # Section 1
            htf_direction=s1["direction"],
            htf_direction_detail=s1["direction_detail"],
            direction_source=s1["direction_source"],
            direction_source_timeframe=s1["source_timeframe"],
            external_high=s1["ext_high"],
            external_low=s1["ext_low"],
            external_range=s1["ext_range"],
            htf_leg=s1["leg"],
            htf_leg_detail=s1["leg_detail"],
            # Section 2
            local_structure=s2["local"],
            local_structure_detail=s2["local_detail"],
            protected_levels=s2["protected"],
            protected_count=s2["protected_count"],
            invalidated_levels=s2["invalidated"],
            invalidated_count=s2["invalidated_count"],
            recent_event=s2["recent"],
            recent_event_type=s2["recent_type"],
            # Section 3
            buy_side_liquidity=s3["buy_side"],
            sell_side_liquidity=s3["sell_side"],
            liquidity_taken=s3["taken"],
            liquidity_remaining=s3["remaining"],
            # Section 4
            valid_zones=s4["valid"],
            invalid_zones=s4["invalid"],
            nearest_reaction=s4["nearest"],
            nearest_above=s4["above"],
            nearest_below=s4["below"],
            # Section 5
            impulse_strength=s5["impulse"],
            correction_character=s5["correction"],
            volatility_trend=s5["volatility"],
            momentum_aligned=s5["aligned"],
            # Section 6
            directional_bias=s6["bias"],
            bias_reasoning=s6["reasoning"],
            path_of_least_resistance=s6["path"],
            confidence_level=s6["confidence"],
            # Section 7
            invalidation_swing=s7["swing"],
            invalidation_price=s7["price"],
            structural_shift_signal=s7["shift_signal"],
            # Section 8
            if_price_reaches=s8["if_reaches"],
            next_area_of_interest=s8["next_area"],
            next_area_price=s8["next_price"],
            bullish_scenario=s8["bullish"],
            bearish_scenario=s8["bearish"],
            # Overall
            market_state=state,
            clarity_score=clarity,
            summary=summary
        )
    
    # =========================================================================
    # SECTION 1: MARKET CONTEXT — "Where am I?"
    # =========================================================================
    def _analyze_context(self, snapshot) -> dict:
        """Where am I in the selected structural timeframe?
        
        READS FROM SCHEMAS (no computation):
        - snapshot.direction_analysis: direction and provenance from alternating swings
        - snapshot.range_position: Premium/discount/equilibrium zone
        """
        regime = snapshot.regime

        # Direction is owned by the canonical regime. DirectionAnalysis remains
        # the supporting swing evidence and provenance.
        dir_analysis = getattr(snapshot, 'direction_analysis', None)
        if regime and dir_analysis:
            direction = regime.direction
            direction_detail = dir_analysis.direction_detail
            direction_source = regime.direction_source
            source_timeframe = regime.source_timeframe
        else:
            direction = "neutral"
            direction_detail = "Direction unavailable"
            direction_source = "unavailable"
            source_timeframe = snapshot.timeframe
        
        # Get range from schema (computed by range_detector)
        range_pos = getattr(snapshot, 'range_position', None)
        if range_pos:
            high_price = range_pos.external_high
            low_price = range_pos.external_low
            leg = range_pos.zone
            leg_detail = range_pos.zone_detail
        else:
            # Fallback to external swings in snapshot
            ext_high = getattr(snapshot, 'external_high', None)
            ext_low = getattr(snapshot, 'external_low', None)
            high_price = ext_high.price if ext_high else 0.0
            low_price = ext_low.price if ext_low else 0.0
            leg = "developing"
            leg_detail = "Range forming"
        
        # Format range string
        if high_price and low_price:
            ext_range = f"{low_price:,.2f} to {high_price:,.2f}"
        else:
            ext_range = "Range developing"
        
        return {
            "direction": direction, "direction_detail": direction_detail,
            "direction_source": direction_source,
            "source_timeframe": source_timeframe,
            "ext_high": high_price, "ext_low": low_price, "ext_range": ext_range,
            "leg": leg, "leg_detail": leg_detail
        }
    
    # =========================================================================
    # SECTION 2: STRUCTURE — "How is price moving?"
    # =========================================================================
    def _analyze_structure(self, snapshot) -> dict:
        """Current local structure and events."""
        breaks = snapshot.structure_breaks
        levels = getattr(snapshot, 'protected_levels', [])
        
        # Local structure is a presentation of the canonical short-term bias.
        if snapshot.regime and snapshot.regime.bias in {"bullish", "bearish"}:
            local = snapshot.regime.bias
            if len(breaks) >= 3:
                recent = breaks[-3:]
                aligned = sum(
                    1 for event in recent
                    if ("bullish" if event.direction == "up" else "bearish") == local
                )
                local_detail = f"Canonical {local} bias; {aligned}/3 recent BOS aligned"
            else:
                local_detail = f"Canonical {local} bias from available structure"
        elif len(breaks) >= 3:
            recent = breaks[-3:]
            bullish = sum(1 for b in recent if b.direction == "up")
            bearish = sum(1 for b in recent if b.direction == "down")
            if bullish > bearish:
                local = "bullish"
                local_detail = f"{bullish}/3 recent breaks bullish"
            elif bearish > bullish:
                local = "bearish"
                local_detail = f"{bearish}/3 recent breaks bearish"
            else:
                local = "mixed"
                local_detail = "Equal bullish/bearish breaks"
        else:
            local = "developing"
            local_detail = "Insufficient structure data"
        
        # Protected levels
        protected = [l for l in levels if not getattr(l, 'broken', False)]
        protected_str = "; ".join([f"{l.kind.title()} at {l.price:,.2f}" for l in protected[:4]])
        
        # Invalidated levels
        invalid = [l for l in levels if getattr(l, 'broken', False)]
        invalid_str = "; ".join([f"{l.kind.title()} at {l.price:,.2f}" for l in invalid[:4]])
        
        # Most recent event across both continuation and reversal structure.
        structural_events = sorted(
            [*breaks, *getattr(snapshot, 'character_changes', [])],
            key=lambda event: event.break_timestamp,
        )
        if structural_events:
            last = structural_events[-1]
            recent_type = last.type if hasattr(last, 'type') else "Structure"
            recent = f"{last.direction.title()} {recent_type} at {last.break_price:,.2f}"
        else:
            recent = "No recent structural events"
            recent_type = ""
        
        return {
            "local": local, "local_detail": local_detail,
            "protected": protected_str or "None", "protected_count": len(protected),
            "invalidated": invalid_str or "None", "invalidated_count": len(invalid),
            "recent": recent, "recent_type": recent_type
        }
    
    # =========================================================================
    # SECTION 3: LIQUIDITY — "Where are the incentives?"
    # =========================================================================
    def _analyze_liquidity(self, snapshot) -> dict:
        """Where is liquidity?"""
        pools = getattr(snapshot, 'liquidity_pools', [])
        sweeps = getattr(snapshot, 'recent_sweeps', [])
        current = snapshot.current_price
        
        # Buy-side liquidity (above price - stop losses from shorts)
        buy_side = [p for p in pools if p.price > current and not getattr(p, 'swept', False)]
        buy_str = ", ".join([f"{p.price:,.2f}" for p in buy_side[:3]]) if buy_side else "None identified"
        
        # Sell-side liquidity (below price - stop losses from longs)
        sell_side = [p for p in pools if p.price < current and not getattr(p, 'swept', False)]
        sell_str = ", ".join([f"{p.price:,.2f}" for p in sell_side[:3]]) if sell_side else "None identified"
        
        # Recently taken
        if sweeps:
            last_sweep = sweeps[-1]
            sweep_signal = "Bullish" if last_sweep.is_bullish_sweep else "Bearish"
            swept_side = "sell-side" if last_sweep.is_bullish_sweep else "buy-side"
            taken = f"{sweep_signal} {swept_side} sweep at {last_sweep.sweep_price:,.2f}"
        else:
            taken = "No recent sweeps"
        
        # Remaining
        total_remaining = len(buy_side) + len(sell_side)
        remaining = f"{total_remaining} untouched pools ({len(buy_side)} above, {len(sell_side)} below)"
        
        return {
            "buy_side": f"Above: {buy_str}",
            "sell_side": f"Below: {sell_str}",
            "taken": taken,
            "remaining": remaining
        }
    
    # =========================================================================
    # SECTION 4: IMPORTANT LEVELS — "What matters right now?"
    # =========================================================================
    def _analyze_levels(self, snapshot) -> dict:
        """What zones are valid and nearest?"""
        levels = getattr(snapshot, 'protected_levels', [])
        fvgs = getattr(snapshot, 'fair_value_gaps', [])
        current = snapshot.current_price
        
        # Valid zones
        valid = [l for l in levels if not getattr(l, 'broken', False)]
        valid_fvgs = [f for f in fvgs if not getattr(f, 'filled', False)]
        valid_str = f"{len(valid)} protected levels, {len(valid_fvgs)} active FVGs"
        
        # Invalid zones
        invalid = [l for l in levels if getattr(l, 'broken', False)]
        invalid_str = f"{len(invalid)} broken levels"
        
        # Nearest reaction zones
        above = [l for l in valid if l.price > current]
        below = [l for l in valid if l.price < current]
        
        nearest_above = min(above, key=lambda l: l.price).price if above else 0.0
        nearest_below = max(below, key=lambda l: l.price).price if below else 0.0
        
        if nearest_above and nearest_below:
            nearest = f"Above: {nearest_above:,.2f} | Below: {nearest_below:,.2f}"
        elif nearest_above:
            nearest = f"Above: {nearest_above:,.2f}"
        elif nearest_below:
            nearest = f"Below: {nearest_below:,.2f}"
        else:
            nearest = "No nearby reaction zones"
        
        return {
            "valid": valid_str, "invalid": invalid_str,
            "nearest": nearest, "above": nearest_above, "below": nearest_below
        }
    
    # =========================================================================
    # SECTION 5: MOMENTUM & VOLATILITY — "How strong is the move?"
    # =========================================================================
    def _analyze_momentum(self, snapshot, structure: dict = None) -> dict:
        """Momentum and volatility assessment."""
        legs = getattr(snapshot, 'legs', [])
        volatility = getattr(snapshot, 'volatility_state', None)
        
        # Impulse strength from leg analysis
        if legs:
            last = legs[-1]
            # Use candle_count and price range as proxy for momentum
            candles = getattr(last, 'candle_count', 0)
            price_move = abs(last.end_price - last.start_price)
            avg_per_candle = price_move / candles if candles > 0 else 0
            
            # Classify based on leg type and aggression
            leg_type = getattr(last, 'leg_type', 'corrective')
            aggression = getattr(last, 'candle_aggression', 0.5)
            
            if leg_type == 'impulse' or aggression > 0.7:
                impulse = "Strong"
            elif leg_type == 'compression' or aggression < 0.3:
                impulse = "Weak"
            else:
                impulse = "Moderate"
            
            # Correction character
            if leg_type == "impulse":
                correction = "In impulse move"
            elif leg_type == "corrective":
                retracement = getattr(last, 'retracement_depth', 0.5)
                if retracement > 0.6:
                    correction = "Deep pullback"
                elif retracement > 0.3:
                    correction = "Normal retracement"
                else:
                    correction = "Shallow pullback"
            else:
                correction = f"{leg_type.title()} pattern"
        else:
            # Fallback to structure breaks if no legs
            breaks = snapshot.structure_breaks
            if breaks:
                recent = breaks[-3:] if len(breaks) >= 3 else breaks
                bullish = sum(1 for b in recent if b.direction == 'up')
                bearish = sum(1 for b in recent if b.direction == 'down')
                if bullish > bearish:
                    impulse = "Bullish momentum"
                elif bearish > bullish:
                    impulse = "Bearish momentum"
                else:
                    impulse = "Mixed momentum"
                correction = "Multiple structure breaks"
            else:
                impulse = "Developing"
                correction = "Awaiting structure"
        
        # Volatility trend
        if volatility == "expanding":
            vol = "Increasing - expansion phase"
        elif volatility == "contracting":
            vol = "Decreasing - compression phase"
        elif volatility == "normal":
            vol = "Normal volatility"
        else:
            vol = "Not measured"
        
        # Momentum alignment with structure
        s2 = structure or self._analyze_structure(snapshot)
        if s2["local"] in ["bullish", "bearish"]:
            if legs:
                last_dir = legs[-1].direction
                # Normalize direction comparison
                struct = s2["local"]
                leg_dir = 'bullish' if last_dir in ['up', 'bullish'] else 'bearish'
                if leg_dir == struct:
                    aligned = f"Yes - {struct} alignment"
                else:
                    aligned = "No - diverging"
            else:
                aligned = "Awaiting leg data"
        else:
            aligned = "Structure developing"
        
        return {
            "impulse": impulse, "correction": correction,
            "volatility": vol, "aligned": aligned
        }
    
    # =========================================================================
    # SECTION 6: PROBABILISTIC DIRECTION — "What is price leaning toward?"
    # =========================================================================
    def _analyze_direction(self, snapshot) -> dict:
        """Probabilistic directional bias (NOT trade entries)."""
        regime = snapshot.regime
        if not regime:
            return {
                "bias": "Neutral - no canonical regime",
                "reasoning": "Canonical Core regime is unavailable",
                "path": "Awaiting structural evidence",
                "confidence": "Low",
            }

        if regime.bias == "bullish":
            bias = "Upward pressure"
            reasoning = "; ".join(regime.reasons)
            path = "Higher prices - following structure"
        elif regime.bias == "bearish":
            bias = "Downward pressure"
            reasoning = "; ".join(regime.reasons)
            path = "Lower prices - following structure"
        else:
            bias = "Neutral - no clear pressure"
            reasoning = "; ".join(regime.reasons) or "Mixed or insufficient evidence"
            path = "Consolidation likely"

        confidence = (
            "High" if regime.confidence >= 0.7
            else "Moderate" if regime.confidence >= 0.4
            else "Low"
        )
        
        return {
            "bias": bias, "reasoning": reasoning,
            "path": path, "confidence": confidence
        }
    
    # =========================================================================
    # SECTION 7: INVALIDATION LOGIC — "What would prove this wrong?"
    # =========================================================================
    def _analyze_invalidation(self, snapshot, direction: dict = None) -> dict:
        """What would invalidate the current context?"""
        s6 = direction or self._analyze_direction(snapshot)
        levels = getattr(snapshot, 'protected_levels', [])
        active = [l for l in levels if not getattr(l, 'broken', False)]
        current = snapshot.current_price
        
        if "Upward" in s6["bias"]:
            # Bullish invalidated by breaking low
            lows = [l for l in active if l.kind == 'low']
            if lows:
                inv = max(lows, key=lambda l: l.price)
                swing = f"Low at {inv.price:,.2f}"
                price = inv.price
                shift = f"Break below {inv.price:,.2f} shifts structure bearish"
            else:
                swing = "Nearest swing low"
                price = 0.0
                shift = "Break of any major low would signal shift"
        elif "Downward" in s6["bias"]:
            # Bearish invalidated by breaking high
            highs = [l for l in active if l.kind == 'high']
            if highs:
                inv = min(highs, key=lambda l: l.price)
                swing = f"High at {inv.price:,.2f}"
                price = inv.price
                shift = f"Break above {inv.price:,.2f} shifts structure bullish"
            else:
                swing = "Nearest swing high"
                price = 0.0
                shift = "Break of any major high would signal shift"
        else:
            swing = "Break of either extreme"
            price = 0.0
            shift = "Break of range bounds would resolve direction"
        
        return {"swing": swing, "price": price, "shift_signal": shift}
    
    # =========================================================================
    # SECTION 8: PROJECTION — "What information could we learn next?"
    # =========================================================================
    def _analyze_projection(self, snapshot, levels: dict = None, direction: dict = None) -> dict:
        """What information could price movement provide?"""
        s4 = levels or self._analyze_levels(snapshot)
        s6 = direction or self._analyze_direction(snapshot)
        current = snapshot.current_price
        
        # If price reaches zone
        if s4["above"]:
            if_reaches = f"Reaching {s4['above']:,.2f}: Tests protected high - rejection = bearish, break = bullish continuation"
        elif s4["below"]:
            if_reaches = f"Reaching {s4['below']:,.2f}: Tests protected low - reaction = bullish, break = bearish continuation"
        else:
            if_reaches = "No clear test zone ahead"
        
        # Next area of interest
        if "Upward" in s6["bias"]:
            next_area = f"Protected high at {s4['above']:,.2f}" if s4["above"] else "Next swing high"
            next_price = s4["above"]
        elif "Downward" in s6["bias"]:
            next_area = f"Protected low at {s4['below']:,.2f}" if s4["below"] else "Next swing low"
            next_price = s4["below"]
        else:
            next_area = "Range boundary"
            next_price = s4["above"] if s4["above"] else s4["below"]
        
        # Scenarios
        bullish = f"Break above {s4['above']:,.2f}, target next liquidity pool" if s4["above"] else "Break structure high, continuation"
        bearish = f"Break below {s4['below']:,.2f}, target next liquidity pool" if s4["below"] else "Break structure low, continuation"
        
        return {
            "if_reaches": if_reaches,
            "next_area": next_area, "next_price": next_price,
            "bullish": bullish, "bearish": bearish
        }
    
    # =========================================================================
    # OVERALL
    # =========================================================================
    def _analyze_overall(self, snapshot) -> tuple:
        """Expose canonical state and measure fact completeness."""
        breaks = snapshot.structure_breaks
        state = snapshot.regime.state.upper() if snapshot.regime else "UNKNOWN"
        
        # Clarity
        score = 100
        if len(snapshot.swings) < 4:
            score -= 20
        if len(breaks) < 2:
            score -= 20
        fvgs = getattr(snapshot, 'fair_value_gaps', [])
        if len([f for f in fvgs if not getattr(f, 'filled', False)]) > 5:
            score -= 15
        
        return state, max(0, min(100, score))
    
    def _build_summary(self, s1: dict, s6: dict, state: str) -> str:
        """Build one-line summary."""
        source = s1["source_timeframe"] or "current timeframe"
        return f"{s6['bias']}. Direction ({source}): {s1['direction']}. State: {state}. {s6['path']}."


def analyze_market(snapshot: 'MarketSnapshot') -> MarketAnalysis:
    """Functional API for market analysis."""
    return MarketAnalyzer().analyze(snapshot)
