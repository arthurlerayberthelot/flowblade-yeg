# Brutalist UI Refactor Plan — Flowblade

## Target Aesthetic

1. The Geometry (Forms)

    The Rectangle is King: Almost every UI element is a rectangle with minimal corner rounding. This maximizes screen real estate and reinforces a "modular" feel.

    Flatness: There are no drop shadows, gradients, or 3D skeuomorphism. It’s a 2D environment designed to reduce cognitive load—a knob looks like a circle, not a physical piece of plastic.

    Vector Precision: Every line is thin and high-contrast. The UI is built on vectors, meaning shapes remain razor-sharp regardless of your zoom level or monitor resolution.

2. The Palette (Colours)

    Neutrality: The default mid-light theme uses a neutral base to ensure that the user-assigned colors for clips and tracks pop. The UI itself stays out of the way.

    Functional Highlighting: Bright "Blue" (or high-contrast yellow/orange) is reserved strictly for active states—on/off buttons, selected parameters, or automation breakpoints.

    The "Glow" Logic: When a clip is playing, it doesn't just change color; it pulses. Visual movement is used sparingly but effectively to indicate activity without needing text.

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
