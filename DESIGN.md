# SwiftMove – Logistics & Transportation Website Design by Sahin Mia for Pixelean on Dribbble

## Mission
Create implementation-ready, token-driven UI guidance for SwiftMove – Logistics & Transportation Website Design by Sahin Mia for Pixelean on Dribbble that is optimized for consistency, accessibility, and fast delivery across dashboard web app.

## Brand
- Product/brand: SwiftMove – Logistics & Transportation Website Design by Sahin Mia for Pixelean on Dribbble
- URL: https://dribbble.com/shots/26866271-SwiftMove-Logistics-Transportation-Website-Design
- Audience: authenticated users and operators
- Product surface: dashboard web app

## Style Foundations
- Visual style: clean, functional, implementation-oriented
- Main font style: `font.family.primary=Mona Sans`, `font.family.stack=Mona Sans, Helvetica Neue, Helvetica, Arial, sans-serif`, `font.size.base=14px`, `font.weight.base=400`, `font.lineHeight.base=28px`
- Typography scale: `font.size.xs=9px`, `font.size.sm=11px`, `font.size.md=12px`, `font.size.lg=13px`, `font.size.xl=13.33px`, `font.size.2xl=14px`, `font.size.3xl=16px`, `font.size.4xl=20px`
- Color palette: `color.text.primary=#0d0c22`, `color.text.secondary=#524b63`, `color.border.muted=#ffffff`, `color.text.inverse=#9e9ea7`, `color.surface.base=#000000`, `color.surface.muted=#ecebf0`, `color.surface.raised=#3a3546`, `color.accent=#ff7a00` (SwiftMove CTA orange), `color.accent.soft=#fff1e6`, `color.page=#f3f2f6`
- Signature patterns from the SwiftMove shot: pill navigation (white track + black active), large rounded photo hero, orange primary CTAs, floating white status chips, numbered service rows, photo feature cards
- Spacing scale: `space.1=4px`, `space.2=5px`, `space.3=8px`, `space.4=10px`, `space.5=12px`, `space.6=15px`, `space.7=16px`, `space.8=18px`
- Radius/shadow/motion tokens: `radius.xs=4px`, `radius.sm=6px`, `radius.md=8px`, `radius.lg=16px`, `radius.xl=50px`, `radius.2xl=10000000px` | `shadow.1=rgba(0, 0, 0, 0.01) 0px 2px 2px 0px` | `motion.duration.instant=50ms`, `motion.duration.fast=100ms`, `motion.duration.normal=200ms`

## Accessibility
- Target: WCAG 2.2 AA
- Keyboard-first interactions required.
- Focus-visible rules required.
- Contrast constraints required.

## Writing Tone
Concise, confident, implementation-focused.

## Rules: Do
- Use semantic tokens, not raw hex values, in component guidance.
- Every component must define states for default, hover, focus-visible, active, disabled, loading, and error.
- Component behavior should specify responsive and edge-case handling.
- Interactive components must document keyboard, pointer, and touch behavior.
- Accessibility acceptance criteria must be testable in implementation.

## Rules: Don't
- Do not allow low-contrast text or hidden focus indicators.
- Do not introduce one-off spacing or typography exceptions.
- Do not use ambiguous labels or non-descriptive actions.
- Do not ship component guidance without explicit state rules.

## Guideline Authoring Workflow
1. Restate design intent in one sentence.
2. Define foundations and semantic tokens.
3. Define component anatomy, variants, interactions, and state behavior.
4. Add accessibility acceptance criteria with pass/fail checks.
5. Add anti-patterns, migration notes, and edge-case handling.
6. End with a QA checklist.

## Required Output Structure
- Context and goals.
- Design tokens and foundations.
- Component-level rules (anatomy, variants, states, responsive behavior).
- Accessibility requirements and testable acceptance criteria.
- Content and tone standards with examples.
- Anti-patterns and prohibited implementations.
- QA checklist.

## Component Rule Expectations
- Include keyboard, pointer, and touch behavior.
- Include spacing and typography token requirements.
- Include long-content, overflow, and empty-state handling.
- Include known page component density: links (412), buttons (213), lists (61), cards (53), inputs (4), navigation (2).


## Quality Gates
- Every non-negotiable rule must use "must".
- Every recommendation should use "should".
- Every accessibility rule must be testable in implementation.
- Teams should prefer system consistency over local visual exceptions.
