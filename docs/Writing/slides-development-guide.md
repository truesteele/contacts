# Slide Development Guide

A guide for creating presentation slides using reveal.js, developed through the Kindora slide deck process.

**Last updated:** February 2026

---

## Table of Contents

1. [Development Workflow](#development-workflow)
2. [Tech Stack](#tech-stack)
3. [File Structure](#file-structure)
4. [Quick Start](#quick-start)
5. [Brand Colors](#brand-colors)
6. [Typography](#typography)
7. [Slide Types](#slide-types)
8. [Speaker Notes](#speaker-notes)
9. [Images](#images)
10. [PDF Export](#pdf-export)
11. [Configuration Options](#configuration-options)
12. [Content Principles](#content-principles)
13. [Troubleshooting](#troubleshooting)
14. [Resources](#resources)

---

## Development Workflow

This is the process we developed building Kindora's slide decks (platform overview, conference talks). It uses Claude Code to go from idea to polished, presentation-ready deck with speaker notes.

### Overview: The 5-Phase Process

```
Phase 1: Content Strategy     (you + Claude — define narrative)
Phase 2: Content Draft         (Claude — generate slide content + speaker notes)
Phase 3: Build                 (Claude — produce presentation.html)
Phase 4: Image Production      (you — generate/capture images)
Phase 5: Polish & Export       (you + Claude — iterate in browser, export PDF)
```

### Phase 1: Content Strategy

Start with a single prompt that gives Claude the full context. Don't ask it to "make slides" — ask it to **think about the narrative first**.

Include in your prompt:
- **Audience** — who is this for? (investors, customers, conference attendees)
- **Goal** — what should the audience do after? (sign up, invest, remember one thing)
- **Time constraint** — how long is the talk? (5 min, 10 min, 20 min)
- **Key stats/proof points** — specific numbers you want to hit
- **Tone** — inspirational, technical, conversational, urgent
- **Comparable decks** — links to decks you admire or want to emulate
- **Source material** — product docs, customer testimonials, company overview

Example prompt structure:
```
I need a [TIME] presentation for [AUDIENCE] about [TOPIC].

Goal: [WHAT SHOULD THEY DO AFTER]
Tone: [DESCRIPTION]

Here's our key material:
- [paste or attach source docs, stats, customer quotes]
- [link to competitor/comparable decks]

Think about the narrative arc first. What story structure
would be most compelling for this audience? Don't write
slides yet — outline the narrative flow.
```

Claude will propose a narrative arc (e.g., Problem -> Pain -> Solution -> Proof -> Ask). Iterate on the structure before moving to content.

### Phase 2: Content Draft

Once the narrative is agreed, ask Claude to produce:

1. **Slide-by-slide content** — headline, body text, stats, and visual direction for each slide
2. **Speaker notes** — talking points, timing, transitions, and objection handling
3. **Image prompts** — AI image generation prompts for any needed photos/illustrations

This creates three deliverables that we store as separate files:
- The presentation itself (`presentation.html`)
- Speaker notes for team review (`speaker-notes.md`)
- Image generation prompts (`image-prompts.md`)

**Key insight from our process:** Write the speaker notes *alongside* the slides, not after. The notes inform what goes on the slide (minimal text) vs. what's said verbally (the real content).

### Phase 3: Build

Claude generates a single self-contained HTML file using reveal.js (CDN-hosted, no build step). The file includes:
- All slide content as `<section>` elements
- Custom CSS with brand colors as CSS variables
- Speaker notes as `<aside class="notes">` blocks
- reveal.js initialization config
- Print-specific CSS for PDF export

**What works well:**
- Give Claude the full slide content + speaker notes in one go
- Ask it to produce the complete HTML file, not slide-by-slide
- Include all CSS in `<style>` — no external files needed (except fonts/images)
- Use CSS custom properties for brand colors so the entire palette is changeable in one place

**Per-deck customization:** Each deck gets its own color palette and typography. The Kindora overview deck uses teal (#0B7B7A) with DM Serif Display + DM Sans. The Claude Code talk uses a deep tech palette (#2B2D42) with JetBrains Mono for code. Define these as CSS variables at the top.

### Phase 4: Image Production

Three categories of images, handled differently:

| Type | Source | Notes |
|------|--------|-------|
| **Product screenshots** | Capture from the live app | Most authentic — use real UI |
| **AI-generated photos** | Midjourney, DALL-E, etc. | Use the `image-prompts.md` file; aim for documentary style, not stock photos |
| **Icons** | AI-generated SVG or icon libraries | Simple line style, 2-color max |

For AI-generated photos, the `image-prompts.md` file should include:
- Detailed scene description
- Mood/lighting direction (documentary, warm, natural light)
- Subject description with diversity notes
- Alternative prompts if the first doesn't work
- Brand color references for consistency

**Photography guidelines:**
- Documentary/authentic style — real moments, not posed
- Subject as hero — protagonists, not victims
- Warm lighting — natural light, golden hour
- Nonprofit casual attire — not suits, not hoodies
- Background context matters — community center aesthetic

### Phase 5: Polish & Export

1. **Open in browser** — just double-click the HTML file
2. **Iterate visually** — identify overflow, spacing, color issues
3. **Test presenter view** — press `S` to check speaker notes
4. **PDF export** — use `?print-pdf` query parameter + browser print
5. **Fix print issues** — add `html.print-pdf` CSS overrides for any overflow

This phase often involves several back-and-forth rounds with Claude: "the stats on slide 4 overlap the image" -> Claude adjusts CSS -> reload and check.

### Workflow Summary: What We Learned

| Lesson | Detail |
|--------|--------|
| **Narrative first, slides second** | Get the story arc right before writing any content |
| **Speaker notes are primary** | The slides are visual aids; the notes are the real presentation |
| **Single-file architecture** | One HTML file with everything inline = zero dependency headaches |
| **Image prompts as a deliverable** | Treat image generation as a separate, documented step |
| **Print CSS is non-trivial** | Always test PDF export early; content overflow causes blank pages |
| **Brand colors as CSS variables** | Change the entire deck's palette by editing 5 lines |
| **One idea per slide** | If you're cramming, split or cut |

### Example Decks Built With This Process

| Deck | Purpose | Slides | Location |
|------|---------|--------|----------|
| Kindora Platform Overview | Customer/investor overview | 16 slides, ~12 min | `slides/kindora-overview/` |
| Building with Claude Code | Conference talk on AI-assisted development | 11 slides, ~10 min | `slides/claude-code-talk/` |

---

## Tech Stack

- **[reveal.js](https://revealjs.com/)** - HTML presentation framework
- **CDN-hosted** - No build step required, just open HTML in browser
- **Custom CSS** - Define your own brand colors and typography

---

## File Structure

```
slides/
├── {deck-name}/
│   ├── presentation.html        # Main presentation file (HTML + CSS + JS)
│   ├── speaker-notes.md         # Extracted talking points for team sharing
│   ├── image-prompts.md         # AI image generation prompts (optional)
│   └── images/                  # Presentation images
│       ├── logo.png
│       ├── photo1.png
│       └── ...
│
├── {another-deck}/
│   ├── presentation.html
│   ├── speaker-notes.md
│   └── images/
│       └── ...
│
photos/                          # Shared photo assets (reference with ../photos/)
├── person1.png
├── event-photo.png
└── ...
```

Each deck is a self-contained directory. Shared assets (like team photos) live in `photos/` and are referenced with relative paths.

---

## Quick Start

### 1. Create a new presentation

Create a new directory under `slides/` and copy the template structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Presentation Title</title>

  <!-- Reveal.js CSS -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/white.css">

  <!-- Google Fonts (optional) -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

  <style>
    /* Your custom CSS here - see Brand Colors section */
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">

      <section>
        <!-- Slide 1 content -->
      </section>

      <section>
        <!-- Slide 2 content -->
      </section>

    </div>
  </div>

  <!-- Reveal.js -->
  <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/notes/notes.js"></script>
  <script>
    Reveal.initialize({
      hash: true,
      slideNumber: 'c/t',
      showSlideNumber: 'speaker',
      progress: true,
      history: true,
      center: true,
      transition: 'fade',
      width: 1280,
      height: 720,
      margin: 0,
      plugins: [ RevealNotes ]
    });
  </script>
</body>
</html>
```

### 2. View your presentation

Simply open the HTML file in a browser. No server required for basic viewing.

For live reload during development:
```bash
cd slides && npx serve .
```

---

## Brand Colors

Define your brand colors as CSS variables for consistency:

```css
:root {
  /* Primary brand colors - customize for each client */
  --brand-primary: #0B7B7A;
  --brand-primary-light: #1A9B99;
  --brand-primary-dark: #065656;

  /* Section/Chapter accent colors */
  --accent-1: #F26A3D;      /* Orange */
  --accent-2: #1E9B7B;      /* Green */
  --accent-3: #6B4FCF;      /* Purple */
  --accent-4: #E5B732;      /* Gold */

  /* Neutrals */
  --gray-900: #1a1a1a;
  --gray-800: #2d2d2d;
  --gray-700: #404040;
  --gray-600: #525252;
  --gray-500: #6b6b6b;
  --gray-400: #8c8c8c;
  --gray-200: #d9d9d9;
  --gray-100: #f0f0f0;
  --gray-50: #fafafa;
  --white: #ffffff;
}
```

---

## Typography

```css
/* Base styles */
.reveal {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 32px;
  color: var(--gray-900);
}

/* Headings - use a serif for contrast */
.reveal h1, .reveal h2, .reveal h3 {
  font-family: Georgia, 'Times New Roman', serif;
  font-weight: 700;
  text-transform: none;
  letter-spacing: -0.02em;
}

.reveal h1 { font-size: 2.4em; line-height: 1.1; }
.reveal h2 { font-size: 1.8em; line-height: 1.2; }
.reveal h3 { font-size: 1.2em; color: var(--brand-primary); }

.reveal p {
  line-height: 1.5;
  color: var(--gray-700);
}
```

---

## Slide Types

### Title Slide (Gradient background)

```html
<section class="slide-title">
  <img src="images/logo.png" alt="Organization Name" class="title-logo">
  <h1>Presentation Title</h1>
  <p class="title-tagline">Subtitle or tagline goes here</p>
</section>
```

```css
.slide-title {
  background: linear-gradient(180deg, var(--brand-primary) 0%, var(--brand-primary-dark) 100%);
  color: var(--white);
  text-align: center;
}

.title-logo {
  width: 160px;
  filter: brightness(0) invert(1);  /* Makes logo white */
  opacity: 0.95;
  margin-bottom: 0.8em;
}

.slide-title h1 {
  color: var(--white);
  font-size: 2.8em;
  text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.slide-title .title-tagline {
  font-size: 1.1em;
  color: #ffffff !important;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0,0,0,0.3);
}
```

### Hero Story Slide (50/50 Image-Dominant Layout)

**Best for:** Beneficiary stories, testimonials, customer stories, emotional hooks

This layout follows social impact and pitch deck best practices: the image dominates, the subject is the hero, and the photo is documentary/authentic in style.

```html
<section class="slide-story-hero">
  <div class="story-hero-layout">
    <div class="story-hero-text">
      <h1>Compelling headline here.</h1>
      <p class="story-hero-quote">Opening context about the person or situation.</p>
      <p class="story-hero-quote">The key moment with <em>emphasis on what matters</em>.</p>
      <p class="story-hero-outcome"><strong>The result.</strong><br>What happened next.</p>
      <div class="story-hero-footer">
        <img src="images/partner-logo.png" alt="Partner" class="story-hero-logo">
        <span class="story-hero-caption">Name and image changed to protect privacy</span>
      </div>
    </div>
    <div class="story-hero-image">
      <img src="../photos/main-photo.png" alt="Scene description">
      <img src="../photos/portrait.png" alt="Person name" class="story-hero-portrait">
    </div>
  </div>
</section>
```

```css
.slide-story-hero {
  background: var(--gray-50);
  padding: 0 !important;
}

.story-hero-layout {
  display: flex;
  height: 100%;
  width: 100%;
}

.story-hero-text {
  flex: 0 0 50%;
  padding: 50px 50px 40px 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: left;
}

.story-hero-text h1 {
  font-size: 2.2em;
  line-height: 1.15;
  margin-bottom: 0.5em;
}

.story-hero-quote {
  font-size: 0.72em;
  line-height: 1.5;
  color: var(--gray-700);
  margin: 0 0 0.5em 0;
}

.story-hero-quote em {
  color: var(--brand-primary);
  font-style: normal;
  font-weight: 600;
}

.story-hero-outcome {
  font-size: 0.72em;
  line-height: 1.5;
  color: var(--gray-800);
  margin-top: 0.6em;
}

.story-hero-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: auto;
  padding-top: 1em;
}

.story-hero-logo {
  width: 80px;
  height: auto;
  opacity: 0.7;
}

.story-hero-caption {
  font-size: 0.4em;
  color: var(--gray-400);
  font-style: italic;
}

/* Full-height image on right */
.story-hero-image {
  flex: 0 0 50%;
  position: relative;
  overflow: hidden;
}

.story-hero-image > img:first-child {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Portrait overlay */
.story-hero-portrait {
  position: absolute;
  bottom: 40px;
  left: 30px;
  width: 140px;
  height: 140px;
  object-fit: cover;
  border-radius: 50%;
  border: 5px solid white;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}
```

### Problem/Crisis Slide (Stats + Image)

```html
<section class="slide-problem">
  <div class="problem-layout">
    <div class="problem-content">
      <h1>The Problem in Plain Terms</h1>

      <div class="stats-row-vertical">
        <div class="stat-item-horizontal">
          <div class="stat-value">10M</div>
          <div class="stat-label">people affected annually</div>
        </div>
        <div class="stat-item-horizontal">
          <div class="stat-value alert">60%</div>
          <div class="stat-label">don't get the help they need</div>
        </div>
      </div>

      <h3>The answer isn't fixing what's broken.<br>It's building something new.</h3>
    </div>

    <div class="problem-image">
      <img src="images/problem-visual.png" alt="Visual representation">
      <p class="image-caption">Caption explaining the visual</p>
    </div>
  </div>
</section>
```

```css
.slide-problem {
  background: var(--white);
}

.problem-layout {
  display: flex;
  align-items: center;
  gap: 60px;
  text-align: left;
  height: 100%;
}

.problem-content {
  flex: 1;
}

.problem-image {
  flex: 0 0 420px;
  text-align: center;
}

.problem-image img {
  width: 420px;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.15);
}

.image-caption {
  font-size: 0.55em;
  color: var(--gray-500);
  font-style: italic;
  margin-top: 0.6em;
}

.stats-row-vertical {
  display: flex;
  flex-direction: column;
  gap: 0.5em;
  margin: 0.6em 0;
}

.stat-item-horizontal {
  display: flex;
  align-items: baseline;
  gap: 0.5em;
}

.stat-value {
  font-family: Georgia, serif;
  font-size: 2.8em;
  font-weight: 700;
  line-height: 1;
  color: var(--brand-primary);
}

.stat-value.alert {
  color: var(--accent-1);
}

.stat-label {
  font-size: 0.6em;
  color: var(--gray-600);
}
```

### Feature/Initiative Slide (Colored Accent Background)

Use different accent colors for each major section or initiative.

```html
<section class="slide-feature slide-feature-1">
  <p class="feature-eyebrow">Initiative 1 · $15M</p>
  <h1>Feature or Initiative Name</h1>

  <div class="feature-layout">
    <div class="feature-content">
      <p class="feature-description">
        Brief description of what this initiative does and why it matters.
      </p>

      <ul class="feature-actions">
        <li>Key action or deliverable with <strong>specific metric</strong></li>
        <li>Another action with <strong>measurable outcome</strong></li>
      </ul>

      <div class="evidence-box">
        <span class="evidence-stat">95%</span>
        <span class="evidence-label">success rate<br>Source and timeframe</span>
      </div>
    </div>

    <div class="feature-image">
      <img src="images/feature-photo.png" alt="Feature in action">
    </div>
  </div>
</section>
```

```css
/* Base feature slide styles */
.slide-feature {
  text-align: left;
}

.feature-eyebrow {
  font-size: 0.5em;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 600;
  margin-bottom: 0.3em;
}

.feature-layout {
  display: flex;
  align-items: flex-start;
  gap: 50px;
  margin-top: 0.5em;
}

.feature-content {
  flex: 1;
}

.feature-image {
  flex: 0 0 280px;
}

.feature-image img {
  width: 280px;
  height: 280px;
  object-fit: cover;
  border-radius: 12px;
  box-shadow: 0 15px 40px rgba(0,0,0,0.12);
}

.feature-description {
  font-size: 0.7em;
  line-height: 1.5;
  margin-bottom: 0.6em;
}

.feature-actions {
  font-size: 0.6em;
  margin: 0.5em 0;
}

.evidence-box {
  display: inline-flex;
  align-items: baseline;
  gap: 0.5em;
  padding: 0.5em 0.8em;
  border-radius: 8px;
  margin-top: 0.3em;
}

.evidence-stat {
  font-family: Georgia, serif;
  font-size: 1.8em;
  font-weight: 700;
}

.evidence-label {
  font-size: 0.55em;
  color: var(--gray-600);
}

/* Color variant 1 (orange) */
.slide-feature-1 {
  background: linear-gradient(135deg, #FEF3EF 0%, #FDE8E0 100%);
}
.slide-feature-1 .feature-eyebrow,
.slide-feature-1 h1 { color: var(--accent-1); }
.slide-feature-1 .evidence-box { background: rgba(242, 106, 61, 0.12); }
.slide-feature-1 .evidence-stat { color: var(--accent-1); }

/* Color variant 2 (green) */
.slide-feature-2 {
  background: linear-gradient(135deg, #EDF7F5 0%, #E0F2EE 100%);
}
.slide-feature-2 .feature-eyebrow,
.slide-feature-2 h1 { color: var(--accent-2); }
.slide-feature-2 .evidence-box { background: rgba(30, 155, 123, 0.12); }
.slide-feature-2 .evidence-stat { color: var(--accent-2); }

/* Color variant 3 (purple) */
.slide-feature-3 {
  background: linear-gradient(135deg, #F3F0FA 0%, #EBE5F7 100%);
}
.slide-feature-3 .feature-eyebrow,
.slide-feature-3 h1 { color: var(--accent-3); }
.slide-feature-3 .evidence-box { background: rgba(107, 79, 207, 0.12); }
.slide-feature-3 .evidence-stat { color: var(--accent-3); }
```

### Proof/Evidence Slide

```html
<section class="slide-proof">
  <h1>What We've Already Proven</h1>

  <div class="proof-stats">
    <div class="proof-item">
      <div class="proof-value color-1">95%</div>
      <div class="proof-label">primary metric</div>
      <div class="proof-source">Source, timeframe</div>
    </div>
    <div class="proof-item">
      <div class="proof-value color-2">6.5x</div>
      <div class="proof-label">improvement metric</div>
      <div class="proof-source">Comparison baseline</div>
    </div>
    <div class="proof-item">
      <div class="proof-value color-3">90%</div>
      <div class="proof-label">outcome metric</div>
      <div class="proof-source">Source with context</div>
    </div>
  </div>

  <h3>These aren't projections—this is proven</h3>

  <ul class="proof-bullets">
    <li><strong>Partner A</strong> achieved specific measurable result</li>
    <li><strong>Partner B</strong> validated our approach with investment/endorsement</li>
  </ul>
</section>
```

```css
.slide-proof {
  background: var(--white);
}

.proof-stats {
  display: flex;
  justify-content: space-around;
  margin: 0.6em 0;
}

.proof-item {
  text-align: center;
  flex: 1;
}

.proof-value {
  font-family: Georgia, serif;
  font-size: 2.8em;
  font-weight: 700;
  line-height: 1;
}

.proof-value.color-1 { color: var(--accent-1); }
.proof-value.color-2 { color: var(--accent-2); }
.proof-value.color-3 { color: var(--accent-3); }

.proof-label {
  font-size: 0.5em;
  color: var(--gray-600);
  margin-top: 0.3em;
}

.proof-source {
  font-size: 0.7em;
  color: var(--gray-400);
  font-style: italic;
}

.proof-bullets {
  text-align: left;
  font-size: 0.6em;
  max-width: 850px;
  margin: 0.5em auto 0;
  columns: 2;
  column-gap: 40px;
}
```

### CTA/Ask Slide (Grid Layout)

```html
<section class="slide-cta">
  <img src="images/logo.png" alt="Organization" class="cta-logo">

  <h1>$50 Million Over Five Years</h1>

  <h3 style="color: rgba(255,255,255,0.9); margin-bottom: 0.3em;">Where Every Dollar Goes:</h3>

  <div class="cta-grid">
    <div class="cta-item">
      <h3>Initiative One</h3>
      <p>$15M to achieve specific outcome reaching X people</p>
    </div>
    <div class="cta-item">
      <h3>Initiative Two</h3>
      <p>$10M to deploy solution in X markets</p>
    </div>
    <div class="cta-item">
      <h3>Initiative Three</h3>
      <p>$15M to scale impact to X organizations</p>
    </div>
  </div>

  <p class="cta-footer">Proving the model locally. Scaling nationally.</p>
  <p class="cta-footer">contact@organization.org · organization.org</p>
</section>
```

```css
.slide-cta {
  background: linear-gradient(180deg, var(--brand-primary) 0%, var(--brand-primary-dark) 100%);
  color: var(--white);
}

.slide-cta h1, .slide-cta h2 {
  color: var(--white);
  margin-top: 0.1em;
}

.cta-logo {
  width: 120px;
  filter: brightness(0) invert(1);
  opacity: 0.9;
  margin-bottom: 0.3em;
}

.cta-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 25px;
  font-size: 0.55em;
  text-align: left;
  margin: 0.6em 0;
}

.cta-item {
  background: rgba(255,255,255,0.15);
  border-radius: 10px;
  padding: 1em;
}

/* IMPORTANT: Use !important to override reveal.js defaults on colored backgrounds */
.cta-item h3 {
  color: #ffffff !important;
  font-size: 1em;
  margin: 0 0 0.4em 0;
}

.cta-item p {
  color: #ffffff !important;
  margin: 0;
  font-size: 0.95em;
  line-height: 1.4;
}

.cta-footer {
  font-size: 0.5em;
  color: #ffffff !important;
  margin-top: 0.8em;
}
```

---

## Speaker Notes

Add notes that appear in presenter view:

```html
<section>
  <h1>Slide Title</h1>
  <p>Visible content</p>

  <aside class="notes">
    <p><strong>TIMING: 30 seconds</strong></p>
    <p>Main talking point here.</p>
    <p>Secondary point.</p>
    <p><em>[TRANSITION: Move to next topic...]</em></p>
  </aside>
</section>
```

**Access presenter view:** Press `S` while viewing the presentation.

### Speaker Notes Best Practices

- **Include timing** - e.g., "TIMING: 30 seconds"
- **Write talking points, not scripts** - Bullet points, not paragraphs
- **Mark transitions** - Use italics: *[TRANSITION: But for most people...]*
- **Extract to shareable doc** - Create a `speaker-notes.md` file for team review

---

## Images

### Adding Images

1. **Slide-specific images:** Place in `slides/images/`
2. **Shared photos:** Place in `photos/` and reference with `../photos/`

### Common Image Styles

```css
/* Circular portrait */
.circular-image {
  width: 300px;
  height: 300px;
  object-fit: cover;
  border-radius: 50%;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}

/* Portrait overlay on hero images */
.portrait-overlay {
  position: absolute;
  bottom: 40px;
  left: 30px;
  width: 140px;
  height: 140px;
  object-fit: cover;
  border-radius: 50%;
  border: 5px solid white;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

/* Rectangular with rounded corners */
.rounded-image {
  width: 280px;
  height: auto;
  border-radius: 12px;
  box-shadow: 0 15px 40px rgba(0,0,0,0.12);
}

/* White logo on dark backgrounds */
.logo-white {
  filter: brightness(0) invert(1);
}
```

### Photography Guidelines for Impact

- **Documentary/authentic style** - Real moments, not posed stock photos
- **Subject as hero** - The person featured should be the protagonist, not a victim
- **Emotional connection** - Images should evoke empathy and inspire action
- **Privacy considerations** - Include caption noting name/image changes when needed

---

## PDF Export

### Method 1: Browser Print (Recommended)

1. Open presentation with `?print-pdf` query parameter:
   ```
   file:///path/to/slides/presentation.html?print-pdf
   ```

2. Press `Cmd+P` (Mac) or `Ctrl+P` (Windows)

3. Configure print settings:
   - Destination: "Save as PDF"
   - Margins: "None" or "Minimum"
   - Enable: "Background graphics" (important!)

4. Save

### Method 2: Decktape (Higher quality)

```bash
npx decktape reveal presentation.html output.pdf
```

### Print-Specific CSS (Critical!)

Content overflow can cause blank pages in PDF export. Use aggressive print CSS:

```css
@media print {
  .reveal .slides section {
    padding: 40px 60px !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
    page-break-inside: avoid !important;
    break-inside: avoid !important;
  }
}

html.print-pdf .reveal .slides section {
  padding: 40px 60px !important;
  box-sizing: border-box !important;
  overflow: hidden !important;
}

/* Example: Story slide print fixes */
html.print-pdf .slide-story-hero {
  padding: 0 !important;
  overflow: hidden !important;
}

html.print-pdf .story-hero-layout {
  height: 100% !important;
  max-height: 720px !important;
}

html.print-pdf .story-hero-text {
  padding: 25px 25px 20px 35px !important;
  overflow: hidden !important;
}

html.print-pdf .story-hero-text h1 {
  font-size: 1.6em !important;
  margin-bottom: 0.3em !important;
}

html.print-pdf .story-hero-quote {
  font-size: 0.58em !important;
  margin-bottom: 0.3em !important;
}

html.print-pdf .story-hero-portrait {
  width: 100px !important;
  height: 100px !important;
  bottom: 20px !important;
  left: 15px !important;
}
```

**Key principle:** If content bleeds to an extra page, reduce font sizes, padding, and margins in `html.print-pdf` rules until it fits.

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `→` / `Space` | Next slide |
| `←` | Previous slide |
| `S` | Speaker notes (presenter view) |
| `O` | Overview mode |
| `F` | Fullscreen |
| `Esc` | Exit fullscreen/overview |
| `B` | Black screen (pause) |

---

## Configuration Options

Common reveal.js configuration options:

```javascript
Reveal.initialize({
  // Display controls
  controls: true,
  progress: true,
  slideNumber: 'c/t',        // current/total
  showSlideNumber: 'speaker', // only in speaker view

  // Navigation
  hash: true,                 // Enable URL hashes per slide
  history: true,              // Push slides to browser history
  keyboard: true,

  // Appearance
  center: true,               // Vertically center content
  transition: 'fade',         // none/fade/slide/convex/concave/zoom
  transitionSpeed: 'default', // default/fast/slow
  backgroundTransition: 'fade',

  // Sizing
  width: 1280,
  height: 720,
  margin: 0,                  // 0 for edge-to-edge, 0.04-0.1 for padding
  minScale: 0.2,
  maxScale: 2.0,

  // Plugins
  plugins: [ RevealNotes ]
});
```

---

## Content Principles

### Every Slide Must Earn Its Place

Before adding a slide, ask:
- Does this advance the narrative?
- Is this information essential, or can it be a verbal talking point?
- Does it duplicate information from another slide?

**If a slide feels weak, cut it.** Verbal talking points during transitions are often more effective than mediocre slides.

### Pitch Deck Best Practices

1. **Lead with story** - Open with a specific person or situation, not statistics
2. **Images dominate** - Photos should take 50% or more of story slides
3. **Subject is the hero** - They're not a victim; they're the protagonist
4. **Stats support, don't lead** - Use numbers to reinforce emotional points
5. **Show proof** - Include evidence boxes with specific data and sources
6. **Clear ask** - End with exactly what you're asking for and where it goes

### Design Guidelines

- **One idea per slide** - Don't overcrowd
- **Large stats** - Use big numbers that read from the back of a room
- **Minimal text** - Bullet points, not paragraphs
- **Consistent spacing** - Use CSS classes, not inline styles
- **High contrast** - Ensure text is readable on all backgrounds
- **Test at scale** - View slides on a projector or large screen

---

## Troubleshooting

### Images not showing
- Check file path is correct and case-sensitive
- For shared photos, use `../photos/filename.png`
- Ensure image is in the correct directory

### PDF has blank pages
- Content is overflowing - add `overflow: hidden` to sections
- Scale down large elements in print-specific CSS
- Add `max-height: 720px !important` to containers
- Reduce font sizes and padding in `html.print-pdf` rules

### Text not visible on colored backgrounds
- Use `!important` on color rules: `color: #ffffff !important;`
- Check that `.reveal p` or `.reveal h3` isn't overriding your custom colors
- reveal.js defaults often need explicit overrides

### Fonts not loading
- Ensure internet connection (fonts are loaded from Google Fonts CDN)
- For offline use, download and host fonts locally

### Colors look wrong in PDF
- Enable "Background graphics" in print settings
- Some gradients may render differently - test and adjust

---

## Resources

- [reveal.js Documentation](https://revealjs.com/)
- [reveal.js GitHub](https://github.com/hakimel/reveal.js)
- [Decktape (PDF export)](https://github.com/astefanutti/decktape)
- [Google Fonts](https://fonts.google.com/)

---

## Appendix: Kindora Deck Reference

### Kindora Platform Overview (`slides/kindora-overview/`)

**Audience:** Potential customers, partners, investors
**Duration:** ~12 minutes (16 slides)
**Narrative arc:** Pain -> Barrier -> Solution -> Features -> Proof -> Team -> Pricing -> CTA
**Color palette:** Kindora teal (#0B7B7A), coral for problem stats (#E5736A), feature accent colors
**Typography:** DM Serif Display (headlines) + DM Sans (body)
**Images:** Mix of AI-generated documentary photos + product screenshots
**Key stats:** 60x faster, 88% cheaper, 175K+ foundations, 5.7M grants

Files:
- `presentation.html` — full deck
- `speaker-notes.md` — talking points, timing, objection handling, key stats table
- `image-prompts.md` — AI generation prompts for all photos and icons

### Claude Code Talk (`slides/claude-code-talk/`)

**Audience:** Developers at a conference/meetup
**Duration:** ~10 minutes (11 slides)
**Narrative arc:** Result -> Old Way -> Method -> Two Prompts -> Autonomous Build -> Debug -> Lessons -> Workflow
**Color palette:** Deep tech palette (#2B2D42), coral (#E76F51), teal (#2A9D8F)
**Typography:** DM Serif Display (headlines) + DM Sans (body) + JetBrains Mono (code blocks)
**Images:** Product screenshots + code block visuals built into the slides
**Key stats:** 7,136 lines, 20 files, 2 prompts, 12 autonomous iterations, 62 minutes

Files:
- `presentation.html` — full deck
- `speaker-notes.md` — talking points with timing

---

*Last updated: February 2026*
