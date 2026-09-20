---
name: recall-design
character: >
  A forensic instrument, not a page about one. Recall's whole claim is that agent
  memory should be inspectable, so the interface has to be the inspection surface:
  every number on screen is read from a real trace, every colour encodes either
  where a memory came from or how a task ended, and nothing is drawn that a reader
  cannot act on. The page reads like an audit report that happens to be running.
---

# Recall design

## Principle

**The page is the instrument.** The Raycast system works because its marketing chrome
is its product chrome at a larger size. Recall's equivalent: the page renders the same
JSON trace the CLI prints, through the same vocabulary. There is no mockup anywhere, and
no number that was typed by hand.

Three consequences, which settle most arguments:

1. If a value is on screen, it came from a trace. No invented metrics, no deltas without
   a named comparison period.
2. If something is coloured, the colour is data. Provenance (where a memory came from) or
   state (how a task ended). Nothing is coloured to look designed.
3. If something moves, it is explaining a change of state. No loops, no ambient motion.

## Why dark

Not a default. Two reasons, both real: the demo runs at 20:00 in a dim room, and the
product's own output is a terminal, so a light page would be a costume over dark content.
Deep navy rather than black, because the semantic colours vibrate against pure black.

## Colour

Colour is an encoding, never decoration. Two independent scales, deliberately distinct so
they cannot be confused for each other.

```
ground        #0a1424   deep navy canvas
ground-2      #0d1a2d   raised surface
sunken        #06101c   machine output (terminal, console)
line          #1c2b3f   hairline
line-strong   #2d4060   control borders
ink           #eef2f7   primary text
ink-2         #c3ccd9   body text
ink-3         #93a3b8   supporting text
```

**Provenance** answers "where did this memory come from", which is the thing the system
reasons about:

```
prov-user     #4ade80   the user said it            trust 1.0
prov-tool     #5aa9ff   a tool returned it          trust 0.6
prov-web      #ff6b6b   read from fetched content   trust 0.2
prov-derived  #b98cff   the agent wrote it          inherits min parent trust
```

**State** answers "how did this task end":

```
sem-safe      #4ade80   CORRECT
sem-harm      #ff6b6b   UNSAFE_ACTION
sem-degraded  #ffb340   UNNECESSARY_ESCALATION
sem-info      #5aa9ff   informational
```

The accent is `sem-safe`, spent at one moment only: the repair landing. Everywhere else
green means a specific measured thing, so it cannot also be the brand colour doing brand
work. Every foreground/background pair clears WCAG AA; measured lowest is 6.65:1.

## Typography

**Switzer** (Fontshare) for everything a person wrote. Chosen for one reason: this page is
mostly dense comparative tables and the figures in them must line up, so it needs real
tabular numerals and a low-contrast grotesk that holds at 13px. Not chosen because it is
the current default.

**Monospace only for machine output.** Memory ids, outcome constants, trace lines, token
counts. Mono is a signal that a value came from the system rather than from an author. It
is not available as an aesthetic: no monospace headings, no wide-tracked uppercase labels
standing in for typographic hierarchy.

Scale is a 1.25 minor third from 16px. Weights: 300 for display, 400 body, 500 emphasis.

## Rhythm

Sections vary by the work they do. An argument section is a narrow measure of prose. An
evidence section is full width and dense. The instrument runs edge to edge. A single
padding value applied to every section is the tell that no one decided anything, so the
rhythm is declared per section type, not globally.

## Motion

Dial: **2 of 5.** State changes and one explanatory sequence. Nothing ambient.

The one animated element is the provenance graph, because the mechanism is a change of
state over a graph and a static picture cannot show taint propagating and then being cut.
The stage bar fills as the audit reaches each phase, which is progress, not decoration.
The terminal cursor marks a real state (output still arriving) and is removed when the
replay completes.

`prefers-reduced-motion` resolves every sequence immediately to its final readable state.

## Do

- Read every figure from a trace, and say which model produced it
- Reserve mono for machine output
- Let the evidence be dense; a judge is reading for the number
- Vary section composition by purpose
- State limitations in the same voice as results

## Don't

- Eyebrow labels that repeat the headline underneath
- Wide-tracked uppercase as a substitute for hierarchy
- Coloured left stripes, decorative dots, badges, pills
- Cards, drop shadows, glass, glow, bento grids
- Gradients, unless the gradient encodes a scale
- Any animation that loops without a user action

## Known gaps

- Consolidation is scripted in `scenario.py` rather than produced by the agent
- Real-model runs are not reproducible; figures are quoted over repeated runs
