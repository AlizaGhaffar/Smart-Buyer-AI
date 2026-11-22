# Spec 02: Premium Animated UI & CSV Export

> **Status:** superseded in part. Spec 03 replaces the 'verified source' badge. The dashboard now shows verification labels, evidence quotes and rules, and the CSV includes evidence and contact source URLs.

## Goal
Build a high-end Next.js dashboard with Framer Motion animations, radar loading states, score badges, verified source links, and CSV export.

## Performance & Animation Constraints
- Use lightweight Framer Motion micro-animations (fade, slide-up, scale on hover).
- Avoid heavy re-renders or complex layout animations.
- Ensure 60 FPS performance and fast initial page load (< 1.5 seconds).