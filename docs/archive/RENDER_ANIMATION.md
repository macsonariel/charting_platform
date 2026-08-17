# Render Animation System

## Overview

The render animation system allows you to toggle between two rendering modes for chart drawings:

1. **Animated Mode**: Elements appear progressively with stagger effects and section-by-section animation
2. **Instant Mode**: All elements appear immediately (default)

## Usage

### Toggle Animation On/Off

```javascript
// Toggle animation (switches between on/off)
toggleRenderAnimation();

// Enable animation
toggleRenderAnimation(true);

// Disable animation
toggleRenderAnimation(false);
```

### Configure Animation Settings

```javascript
// Set custom animation parameters
setRenderAnimationSettings({
    duration: 1000,        // Animation duration in ms (default: 800)
    staggerDelay: 75,      // Delay between elements in ms (default: 50)
    sectionDelay: 300      // Delay between sections in ms (default: 200)
});
```

### Check Current Settings

```javascript
// Access current animation settings
console.log(window.renderAnimationSettings);
// {
//     enabled: false,
//     duration: 800,
//     staggerDelay: 50,
//     sectionDelay: 200
// }
```

## How It Works

### Animated Mode

When animation is enabled, elements are rendered in sections with progressive effects:

1. **Break Lines** (BOS/CHOCH): Lines draw from start to end point
2. **Connecting Lines**: Swing connecting lines draw progressively
3. **Labels & Markers**: Fade in with stagger effect

Each section waits for the previous section to complete before starting.

### Instant Mode

When animation is disabled (default), all elements appear immediately at their final positions and opacity.

## Implementation Details

### Render Functions

Render functions now accept an `animated` option:

```javascript
await renderMacroSwingsD3(swings, overlay, xScale, yScale, {
    showLabels: true,
    showBOS: true,
    showCHOCH: true,
    showLines: true,
    chartData: chartData,
    animated: renderAnimationSettings.enabled,  // Use global setting
    animationDuration: renderAnimationSettings.duration,
    animationStaggerDelay: renderAnimationSettings.staggerDelay,
    animationSectionDelay: renderAnimationSettings.sectionDelay
});
```

### Animation Utilities

The system uses animation utilities from `backend/chart/renders/render-animation-utils.js`:

- `animateLinesDrawing()`: Draws lines from start to end
- `animateFadeIn()`: Fades elements in with stagger
- `animateElementsProgressive()`: Generic progressive animation
- `animateSectionsProgressive()`: Animates multiple sections sequentially

## Example: Adding Animation to a Custom Render Function

```javascript
async function renderMyCustomD3(data, chartData, overlay, xScale, yScale, options = {}) {
    const {
        animated = false,
        animationDuration = 800,
        animationStaggerDelay = 50
    } = options;

    // Create elements with initial state (hidden if animated)
    const elements = data.map((item, i) => {
        const element = overlay.append('circle')
            .attr('cx', xScale(item.x))
            .attr('cy', yScale(item.y))
            .attr('r', 0)  // Start at 0 if animated
            .attr('opacity', animated ? 0 : 1);  // Hidden if animated
        
        return element;
    });

    // Animate if enabled
    if (animated && typeof animateFadeIn !== 'undefined') {
        const selection = d3.selectAll(elements.map(el => el.node()));
        
        // Animate radius
        selection
            .transition()
            .duration(animationDuration)
            .delay((d, i) => i * animationStaggerDelay)
            .attr('r', 5)
            .attr('opacity', 1);
    }

    return { count: elements.length };
}
```

## Browser Console Examples

```javascript
// Enable animation and re-render
toggleRenderAnimation(true);

// Disable animation
toggleRenderAnimation(false);

// Set faster animation
setRenderAnimationSettings({
    duration: 500,
    staggerDelay: 30,
    sectionDelay: 150
});

// Check if animation is enabled
console.log(renderAnimationSettings.enabled);
```

## Files Modified

1. **`script/fragments/market-chart.js`**:
   - Added `renderAnimationSettings` global configuration
   - Added `toggleRenderAnimation()` function
   - Added `setRenderAnimationSettings()` function
   - Updated render calls to pass animation options

2. **`backend/chart/renders/macro-swing-render.js`**:
   - Added animation support with section-by-section rendering
   - Elements start hidden/at start position when animated
   - Progressive animation for lines and fade-in for labels

3. **`backend/chart/renders/render-animation-utils.js`** (new):
   - Animation utility functions for progressive rendering
   - Line drawing animations
   - Fade-in animations
   - Section-based progressive animations

4. **`html/fragments/market-chart.html`**:
   - Added script tag to load animation utilities

## Notes

- Animation is **disabled by default** for performance
- Animation only affects new renders (toggle a render off/on to see animation)
- Animation utilities must be loaded before render functions use them
- The system gracefully falls back to simple fade-in if animation utilities aren't available

