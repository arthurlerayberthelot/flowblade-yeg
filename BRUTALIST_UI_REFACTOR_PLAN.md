# Brutalist UI Refactor Plan — Flowblade

## Diagnosis

Flowblade's UI is a standard GTK3 dark theme with rounded corners, gradients, transparency, decorative borders, generous padding, and blue accent colors. It looks like every other video editor trying to look "modern." The software works. The UI doesn't need to be pretty. It needs to get out of the way.

## Target Aesthetic

- **Zero border-radius.** Everything is a rectangle.
- **Zero decorative borders.** Borders only where they separate functional regions.
- **Minimal padding/margin.** Content fills space. No breathing room for aesthetics.
- **No shadows, no gradients, no transparency.** Flat. Solid. Done.
- **No hover glow, no transition animations.** State changes are instant and binary.
- **Maximum information density.** Every pixel earns its keep.
- **Modern, neat font.**

---

## Feasibility Assessment

**FEASIBLE. Medium effort. Low risk.**

### Why it's doable:

1. **Centralized theming.** One main CSS file (`gtk-flowblade-dark.css`, 3484 lines) controls ~90% of visual styling. Six small supplementary CSS files handle specific widgets. One SASS color file (`_colors.scss`) defines all color variables.

2. **Clean separation.** CSS handles appearance. Python handles structure. The `gui.py` module loads CSS via `Gtk.CssProvider` — standard GTK3 pattern. No inline styles scattered across 167 Python files (mostly).

3. **Known color system.** All colors flow from `_colors.scss` variables. Change the variables, rebuild CSS, everything updates.

4. **Python color refs are isolated.** `gui.py` lines 79-83 define `_FLOWBLADE_COLORS` and `MID_NEUTRAL_THEME_NEUTRAL`. These feed into Cairo drawing. Small surface area.

### Risks:

- **Custom Cairo-rendered widgets** (`tlinewidgets.py` 129KB, `glassbuttons.py` 30KB, `monitorwidget.py` 33KB) draw directly to canvas. These bypass CSS entirely and use hardcoded color values in Python. They need manual color extraction and replacement.
- **600+ PNG assets** in `res/css3/assets/` and `res/darktheme/`. Checkbox, radio, switch images baked as PNGs. These need replacement or override via CSS.
- **`glassbuttons.py`** — the name says it all. Glass-style rendered buttons with gradients. Needs full rewrite to flat rendering.

---

## Execution Plan

### Phase 1: Change font

### Phase 2: Kill Decoration (1 day)

**Files:** `gtk-flowblade-dark.css` (or `_common.scss`, `_drawing.scss`)

Global overrides at top of compiled CSS:

```css
* {
  border-radius: 0;
  box-shadow: none;
  text-shadow: none;
  -gtk-icon-shadow: none;
  transition: none;
}
```

Then sweep through `_common.scss` and `_drawing.scss`:
- Remove all `border-radius` declarations
- Remove all `box-shadow` / `text-shadow`
- Remove all `background-image: linear-gradient(...)` — replace with `background-color`
- Remove all `transition` properties
- Reduce all `padding` and `margin` to functional minimums (2px where needed, 0 elsewhere)

**Supplementary CSS files** — strip in parallel:
- `player-bar-id.css`: kill `border-radius: 10px`
- `notebook-side-borders-class.css`: simplify or remove decorative borders
- `empty-panel-frame-class.css`: remove colored borders

### Phase 3: Python Color Constants (0.5 day)

**Files:** `gui.py`

```python
_FLOWBLADE_COLORS = (
    (1.0, 1.0, 1.0),        # LIGHT_BG — white
    (0.04, 0.04, 0.04),     # DARK_BG — near black
    (1.0, 1.0, 1.0),        # SELECTED_BG — white
    (1.0, 1.0, 1.0),        # DARK_SELECTED_BG — white
    "Brutalist"
)
MID_NEUTRAL_THEME_NEUTRAL = (0.1, 0.1, 0.1, 1.0)
```

### Phase 4: Glass Buttons Death (1-2 days)

**File:** `widgets/glassbuttons.py` (30KB)

This module renders custom toolbar buttons with Cairo — gradients, gloss, rounded shapes. Rewrite all `draw()` methods:
- Flat black rectangle background
- White icon/text
- Active state: white background, black icon (inverted)
- No gradients, no alpha blending, no curves

### Phase 5: Timeline & Custom Widgets (2-3 days)

**Files:** `tlinewidgets.py` (129KB), `monitorwidget.py` (33KB), `positionbar.py`

These use Cairo drawing with hardcoded colors. Grep for:
- `cairo.set_source_rgb` / `set_source_rgba`
- Color tuples like `(0.x, 0.x, 0.x)`
- Any gradient patterns (`cairo.LinearGradient`, `cairo.RadialGradient`)

Replace all with B&W palette. Remove gradients. Use 1px lines for separators.

### Phase 6: Asset Replacement (1 day)

**Dirs:** `res/css3/assets/` (~300 PNGs), `res/darktheme/` (~300 PNGs)

Options (pick one):
1. **CSS override** — force GTK to use CSS-only rendering for checkboxes/radios/switches instead of PNG assets. Add `-gtk-icon-source: none;` and style with borders.
2. **Regenerate PNGs** — modify `assets.svg` to B&W, re-run `assets-render.sh`.
3. **Hybrid** — CSS override for standard widgets, keep only functional icons from darktheme.

**Recommendation:** Option 3. Override standard widgets via CSS, keep app-specific icons but desaturate them.

### Phase 7: Spacing Audit (0.5 day)

**Files:** `guiutils.py` (layout helpers), `editorwindow.py`, `panels.py`

Grep for `set_margins`, `set_border_width`, `set_spacing`, padding constants. Reduce all to functional minimums. Target: 0-2px margins, 0-4px spacing. No decorative whitespace.

---

## Scope Summary

| Phase | Files | Effort | Risk |
|-------|-------|--------|------|
| 1. Color System | 2 SCSS | Low | Low |
| 2. Kill Decoration | 1 CSS + 5 small CSS + 2 SCSS | Medium | Low |
| 3. Python Colors | 1 Python | Low | Low |
| 4. Glass Buttons | 1 Python | Medium | Medium |
| 5. Timeline/Widgets | 3-5 Python | High | Medium |
| 6. Assets | SVG + PNGs | Medium | Low |
| 7. Spacing | 3-5 Python | Low | Low |

**Total estimated effort:** 7-10 days for one developer.
**Can be done incrementally** — each phase produces a visibly improved result.
**Phases 1-3 alone** get you 70% of the way there in 2-3 days.

---

## What NOT to Touch

- MLT pipeline code
- File I/O / project serialization
- Keyboard shortcuts / keybinding system
- Rendering / encoding logic
- Plugin/filter infrastructure
- Any backend logic

This is a skin job. The skeleton stays.

---

## Dependencies

- SASS compiler (`sassc` or `dart-sass`) to rebuild CSS from SCSS
- `rsvg-convert` if regenerating PNG assets from SVG
- No new libraries needed

## Testing Strategy

- Visual inspection per phase (launch app, check each panel)
- Verify all interactive elements remain clickable/functional
- Check text readability at different monitor DPIs
- Ensure timeline tracks remain visually distinguishable in B&W (use different grays for V1-V9, A1-A4)
