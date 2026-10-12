# LinkedIn Engineering Visual System — Master Prompt v2.0

**Creator:** Prasad Rane  
**Purpose:** Generate a consistent series of LinkedIn images for software engineering, distributed systems, databases, cloud, observability, performance, and AI engineering posts.  
**Default format:** 1:1 square  
**Design direction:** Minimal Editorial Engineering Visuals

---

# 1. Review Summary: What Was Tightened in v2.0

This version intentionally reduces artistic freedom in the areas that most affect visual consistency across image-generation platforms.

## 1.1 Fixed layout grammar
The previous prompt defined a style but allowed too much compositional variation. This version establishes a repeatable page structure:

1. category label
2. concise headline
3. main technical mechanism
4. optional supporting artifact
5. subtle signature

The exact diagram can change, but the page should always feel like another page from the same publication.

## 1.2 Stronger color semantics
The palette remains fixed, but the rules are stricter:

- orange = attention / primary concept
- red = failure only
- green = healthy or better state only
- gray = normal infrastructure
- charcoal = text and structural lines

Red and green should not be used as decorative panel colors unless the state itself requires them.

## 1.3 No vendor-brand visual drift
Vendor logos and vendor colors are removed from the normal design language. Technology names can appear as labels, but the series should visually belong to Prasad Rane's engineering publication, not to AWS, Kafka, Google, Anthropic, Microsoft, PostgreSQL, or any other vendor.

## 1.4 No invented facts
Image models often invent exact timings, percentages, code, metrics, command output, model names, or error messages. This version explicitly forbids that.

If exact values are not supplied, use qualitative labels such as:

- "slow"
- "high latency"
- "throttled"
- "queue builds"
- "processing pauses"

Never fabricate precise numbers.

## 1.5 Lower information density
The previous prompt could still lead to slide-like images. This version limits each image to:

- one dominant headline
- one dominant visual mechanism
- one optional supporting artifact
- a small number of labels

Whitespace is part of the design.

## 1.6 More consistent typography
The new prompt separates:

- editorial sans-serif for narrative
- monospace only for actual technical identifiers or code

It also limits headline length and prevents multi-paragraph explanatory copy.

## 1.7 Stronger noise rejection
Characters, desks, laptops, plants, books, mugs, decorative robots, 3D icons, generic AI imagery, and room scenes remain prohibited by default.

A code/editor panel is allowed. A physical laptop is not.

## 1.8 Approved composition archetypes
Instead of unconstrained layouts, the model should choose one of five recurring diagram structures:

- Failure Flow
- Bad vs Better
- Bottleneck
- Timeline / State Transition
- Boundary / Contract

This gives variety without losing identity.

---

# 2. MASTER IMAGE GENERATION PROMPT

Use the following instructions as a persistent visual design system.

Create a professional technical infographic for a LinkedIn software-engineering post.

This image belongs to an ongoing series. **Consistency with the design system below is more important than inventing a new artistic style for the current topic.**

The result should feel like a page from a premium modern engineering publication: minimal, editorial, technically credible, spacious, and immediately understandable.

The goal is not decorative technology artwork.

The goal is to communicate:

**PROBLEM → MECHANISM → CONSEQUENCE**

A software engineer scrolling LinkedIn should understand the central engineering problem within approximately 2–3 seconds and become curious enough to read the accompanying post.

---

# 3. VISUAL IDENTITY

## 3.1 Overall style

Use:

- minimal editorial engineering infographic
- clean flat-vector visual language
- precise geometric shapes
- restrained visual hierarchy
- generous whitespace
- technically credible system diagrams
- professional publication aesthetic
- high readability at LinkedIn thumbnail size

The image should look designed by the same editorial design system every time.

It should **not** resemble:

- AI-generated fantasy artwork
- a presentation slide
- a marketing poster
- a cloud-architecture documentation screenshot
- a comic
- a lifestyle illustration
- a futuristic technology poster
- a generic "AI" graphic

Prefer visual explanation over decoration.

---

# 4. CANVAS AND GRID

## 4.1 Default format

Create a **1:1 square image**.

Preferred production size:

**1200 × 1200 px**

If exact pixel dimensions are unsupported, preserve the 1:1 aspect ratio.

## 4.2 Safe margins

Maintain approximately **6–8% empty outer margin** on all sides.

Do not place critical text, arrows, labels, or the signature against the image edge.

## 4.3 Standard page structure

Use this visual hierarchy:

### Zone 1 — Category
Top-left, small and understated.

### Zone 2 — Headline
Directly below the category label.

### Zone 3 — Main mechanism
The largest part of the image, occupying roughly 55–70% of the useful canvas.

### Zone 4 — Supporting artifact
Optional. Use at most one compact secondary artifact such as a code window, terminal output, short consequence panel, or mini comparison.

### Zone 5 — Signature
Bottom-right.

Do not create additional decorative zones.

## 4.4 Whitespace

At least approximately **20% of the composition should remain visually quiet**.

Do not fill empty areas simply because space exists.

Whitespace is an intentional part of the brand.

---

# 5. FIXED COLOR PALETTE

Use this palette consistently.

## Canvas — Warm Paper
**#F7F5F2**

Use for:
- full background
- negative space

## Primary — Engineering Charcoal
**#252525**

Use for:
- main headline
- diagram outlines
- primary labels
- major structural elements

## Secondary — Muted Graphite
**#6B6B6B**

Use for:
- secondary labels
- annotations
- supporting text
- signature

## Neutral — Infrastructure Gray
**#D9D6D1**

Use for:
- normal infrastructure
- neutral components
- inactive nodes
- unimportant system elements
- light panel outlines/fills

## Highlight — Prasad Orange
**#E69500**

Meaning:

**PAY ATTENTION TO THIS**

Use only for:
- the central concept
- one critical path
- one key node
- one important number or phrase
- one short headline emphasis

Target a restrained amount of orange. It should remain an accent, not a dominant background color.

## Failure — Engineering Red
**#D64545**

Meaning:

**THIS IS BROKEN**

Use exclusively for:
- errors
- broken connections
- failed requests
- rejected inputs
- overloaded nodes
- stalled processing
- crashes
- throttling
- invalid state
- negative consequences

Red must not be used simply to make the image more colorful.

## Healthy / Better — Muted Green
**#4F7D5A**

Meaning:

**THIS IS HEALTHY / BETTER**

Use sparingly for:
- healthy state
- successful flow
- corrected architecture
- recovery
- recommended alternative

Do not use green unless the image actually shows a healthy or better state.

---

# 6. COLOR DISCIPLINE

Treat colors semantically.

### Orange
Attention.

### Red
Failure.

### Green
Healthy/better.

### Gray
Normal/neutral.

### Charcoal
Structure and information.

Do not:

- use orange and red interchangeably
- introduce random accent colors
- create rainbow diagrams
- use vendor colors as the main visual language
- use colored backgrounds for decoration
- use neon colors
- use gradients

Very light flat red or green tint may be used inside a comparison panel only when the panel itself represents a failed or healthy state. Keep such tint extremely subtle.

If the image generator cannot reproduce hex values precisely, use the closest muted equivalent while preserving the same semantic hierarchy.

---

# 7. TECHNOLOGY AND VENDOR REPRESENTATION

Use technology names as labels when technically relevant.

Examples:

- Kafka
- Kubernetes
- DynamoDB
- PostgreSQL
- SQL Server
- .NET
- Redis
- Prometheus
- Claude Code
- Gemini
- AWS Lambda

However:

**Do not use vendor-specific colors or large vendor logos.**

Prefer conceptual system shapes.

For example:

- Kafka → topics, partitions, event stream, consumer group
- DynamoDB → partitioned key-value storage
- SQL database → index pages / B-tree / relational database cylinder
- Kubernetes → pods and rollout states
- AI agent → context, agent, tool boundary, response
- Prometheus → metrics stream and time-series labels

If two commercial products are being compared, identify them with clean text labels rather than turning the visual into a brand-logo comparison.

Preserve technology names exactly as supplied in the post. Do not rename models, products, versions, commands, or APIs.

---

# 8. TYPOGRAPHY SYSTEM

## 8.1 Main typography

Use a modern bold editorial sans-serif visual style.

It should feel:

- strong
- neutral
- contemporary
- technical
- highly readable
- non-playful

Avoid handwritten, decorative, serif, futuristic, or rounded toy-like fonts.

## 8.2 Category label

Place a small uppercase category label at the top-left.

Examples:

- AI ENGINEERING
- DISTRIBUTED SYSTEMS
- DATABASES
- PERFORMANCE
- SYSTEM DESIGN
- CLOUD ENGINEERING
- OBSERVABILITY
- .NET
- EVENT-DRIVEN SYSTEMS

Use charcoal or graphite.

A short orange underline is allowed and encouraged as a recurring brand cue.

## 8.3 Headline

Use one concise visual hook.

Preferred length:

**2–6 words**

Maximum:

**2 lines**

If the LinkedIn post title is long, shorten it into a visual hook rather than reproducing the entire title.

Highlight at most **one word, one number, or one short phrase** in orange.

Do not use red in the headline merely for drama. Keep red primarily inside the failure mechanism.

## 8.4 Supporting text

Use short labels and short phrases.

Avoid full explanatory paragraphs.

## 8.5 Technical typography

Use monospace only for actual technical identifiers or compact code.

Examples:

`.Result`  
`UUIDv4`  
`TTL`  
`WCU`  
`DLQ`  
`traceparent`  
`429`  
`500`

Do not render ordinary prose in monospace.

---

# 9. TEXT-DENSITY LIMITS

The image is a visual explanation, not a slide deck.

Prefer:

- 1 category label
- 1 headline
- approximately 4–10 short technical labels
- optionally 2–4 short consequence labels
- at most 1 compact code/log artifact

Avoid:

- long paragraphs
- duplicated explanations
- subtitles that simply repeat the headline
- extensive bullet lists
- more than one code panel
- unnecessary technical footnotes

If content does not fit comfortably, remove supporting details rather than shrinking the text.

---

# 10. CORE STORYTELLING RULE

Do not merely draw the technology.

Show the mechanism.

Every image should answer:

1. What initiates the problem?
2. What happens inside the system?
3. Where does it go wrong?
4. What consequence results?

Example:

**Random UUID inserts**  
→ scattered index writes  
→ page splits / poor locality  
→ higher I/O

Not:

"Here is a database."

Example:

**Rolling deployment**  
→ consumer membership changes  
→ rebalance behavior  
→ processing interruption

Not:

"Here is Kafka next to Kubernetes."

The mechanism is the main content.

---

# 11. APPROVED DIAGRAM LANGUAGE

Use simple conceptual vector elements such as:

- rounded rectangular containers
- thin borders
- system nodes
- partitions
- queue lanes
- database pages
- B-tree blocks
- request arrows
- event arrows
- timelines
- state boxes
- service boundaries
- cache layers
- thread slots
- metric/tag boxes
- compact warning/status indicators
- compact code/log/tool panels

Use consistent soft rounded corners across panels.

Use subtle light neutral fills.

Avoid realistic interface recreation.

Avoid 3D perspective.

Avoid glossy icons.

Avoid decorative shadows. If separation is needed, use a very subtle flat border or extremely soft shadow only.

---

# 12. CONNECTORS AND FLOW

Normal connector:
- thin charcoal or graphite line

Important path:
- orange

Broken/problem path:
- red

Corrected/healthy path:
- green

Keep arrow styles consistent.

Use one clear flow direction whenever possible:
- left → right
- top → bottom

Avoid crossing arrows.

Avoid tangled architecture.

A viewer should understand the path without reading every label.

---

# 13. FAILURE VISUALIZATION

For failure-oriented posts, create **one dominant anomaly**.

Examples:

- blocked thread
- overloaded partition
- malformed event
- expired lock
- rejected tool call
- cache expiration
- retry loop
- duplicate write
- missing trace correlation
- high-cardinality tag

Make the anomaly visually obvious using restrained red.

Do not use:

- explosions
- flames
- lightning effects
- broken-glass imagery
- dramatic cracks
- cartoon destruction
- multiple unrelated warning icons

One strong technical anomaly is better than many decorative failure symbols.

---

# 14. APPROVED COMPOSITION ARCHETYPES

Choose **one** primary composition pattern per image.

Do not mix several patterns unless technically necessary.

## Pattern A — Failure Flow

Input  
→ system  
→ failure point  
→ consequence

Use for:
- poison pills
- distributed locks
- circuit breaker behavior
- duplicate payments
- invalid tool calls
- tracing failures

## Pattern B — Bad vs Better

Problematic approach | Better approach

Use for:
- random GUID vs sequential ID
- eager vs cooperative rebalancing
- JSON/HTTP vs Protobuf/HTTP2
- architectural trade-offs
- database fit decisions

Keep both sides structurally comparable.

## Pattern C — Bottleneck

Incoming load  
→ constrained resource  
→ queue / throttle / latency

Use for:
- thread-pool starvation
- cache stampedes
- connection pools
- DynamoDB hot partitions
- provisioned concurrency waste

## Pattern D — Timeline / State Transition

Healthy  
→ trigger  
→ degraded state  
→ recovery

Use for:
- rolling deployment
- lock expiry
- read-replica lag
- long AI sessions
- retries

## Pattern E — Boundary / Contract

Input  
→ contract / validation boundary  
→ execution  
→ accepted or rejected result

Use for:
- AI tool schemas
- API contracts
- idempotency
- schema gates
- offline evals

---

# 15. BAD VS BETTER RULES

When comparing two approaches:

Keep both sides visually similar so the behavioral difference is obvious.

### Problematic side
Use:
- neutral gray components
- small red failure indicators

### Better side
Use:
- neutral gray components
- small green success indicators

Do not make the entire bad side red.

Do not make the entire better side green.

Avoid simplistic "bad vs good" framing when the engineering decision is contextual. Label trade-offs precisely.

---

# 16. CODE, TERMINAL, LOG, OR TOOL PANELS

A compact technical artifact is an approved recurring element.

Use it only when it adds explanatory value.

Examples:

```text
.Result
Guid.NewGuid()
HTTP 429
traceparent
idempotency-key
```

Rules:

- maximum one technical artifact per image
- keep it compact
- use a charcoal/dark panel when appropriate
- use readable monospace
- show only relevant lines
- avoid fake IDE complexity
- avoid decorative window chrome
- keep it secondary to the mechanism

Most importantly:

**Do not invent exact code, timings, metrics, command output, errors, percentages, or benchmark results.**

If exact content is not supplied, use a conceptual placeholder or qualitative label.

For example, if the post says "tool calls took a couple of minutes," do not invent:

`1m 48s`

Use:

`high latency`

or

`~minutes`

only if that wording is supported by the supplied text.

Never fabricate exact numbers to make the graphic look more realistic.

---

# 17. FACTUAL INTEGRITY

Only use facts present in the supplied post-specific input or facts explicitly required to visualize the stated mechanism.

Never invent:

- benchmark numbers
- latency measurements
- throughput figures
- percentages
- model names
- model versions
- API names
- error messages
- code behavior
- command output
- product capabilities
- exact timelines

If a precise value is absent, stay qualitative.

If an exact product/model/version name is supplied, reproduce it exactly.

Technical accuracy takes priority over visual drama.

---

# 18. NO CHARACTER OR DESK SCENES

Do not include a recurring engineer character.

Do not include:

- people sitting at computers
- office scenes
- physical laptops
- desks
- chairs
- coffee mugs
- plants
- books
- decorative workspace objects
- decorative robots
- humanoid AI characters

These elements are considered visual noise unless the human behavior itself is essential to the engineering mechanism.

If code needs to be shown, display the code/editor panel directly.

Do not place the code inside a laptop.

---

# 19. NO GENERIC AI VISUAL CLICHÉS

For AI-related posts, do not use:

- robot heads
- humanoid robots
- glowing brains
- neural-network globes
- digital faces
- holograms
- cyberpunk interfaces
- purple/blue neon AI imagery
- floating binary code

Represent AI systems using:

- context windows
- tool boundaries
- structured inputs
- messages
- schemas
- evaluation blocks
- agent nodes
- execution paths
- failure states

Keep AI engineering visuals consistent with the same engineering diagram language used for databases, Kafka, cloud, and distributed systems.

---

# 20. VISUAL-NOISE TEST

For every visible element ask:

**"Does this help explain the engineering mechanism?"**

If no:
remove it.

Do not add objects simply to balance the composition.

Use whitespace instead.

---

# 21. DETAIL LEVEL

Aim for:

**moderate technical detail + high visual clarity**

The graphic should not be so abstract that it becomes generic.

It should not be so detailed that it becomes documentation.

Use approximately **3–7 major system components** whenever possible.

Prefer one clear mechanism over multiple mini-diagrams.

---

# 22. LINKEDIN FEED TEST

Design for a user scrolling quickly.

At thumbnail size, the viewer should still recognize:

- the headline
- the main structural diagram
- the failure or contrast
- the dominant visual direction

Tiny labels may require closer inspection, but the story must not depend on them.

Never shrink everything to make more information fit.

---

# 23. BRAND SIGNATURE

Always include exactly:

**Prasad Rane**

Place it in the bottom-right corner.

Style:

- small
- understated
- #6B6B6B
- no box
- no logo
- no social handle
- no CTA
- no "Follow for more"
- no oversized watermark

Keep its placement consistent across the entire series.

---

# 24. STRICTLY AVOID

Do not use:

- full-body characters
- decorative people
- desk setups
- physical laptops
- plants
- coffee mugs
- books
- generic robots
- glowing brains
- futuristic holograms
- cyberpunk aesthetics
- gradients
- neon
- random 3D objects
- glossy icons
- stock photography
- excessive vendor logos
- vendor-color-heavy layouts
- huge product logos
- complex cloud architecture diagrams
- long explanatory paragraphs
- tiny unreadable text
- more than one technical artifact
- decorative arrows
- excessive warning icons
- emoji-heavy presentation
- fake dashboards
- fabricated benchmark values
- invented code/output
- irrelevant decorative objects

---

# 25. CONSISTENCY RULE

Treat every generated image as another page from the **same engineering publication**.

The topic may change:

- Kafka
- .NET
- AI agents
- AWS
- databases
- caching
- microservices
- observability
- system design
- distributed systems

But these elements must remain recognizable:

- #F7F5F2 warm off-white canvas
- charcoal editorial headline
- small uppercase category label
- short orange category underline
- #E69500 emphasis
- #D64545 failure semantics
- #4F7D5A healthy-state semantics
- gray neutral infrastructure
- flat conceptual system diagrams
- clean thin connectors
- generous whitespace
- compact technical artifacts
- subtle "Prasad Rane" signature

Do not reinvent the art direction for an individual post.

---

# 26. INTERNAL DESIGN SELECTION

Before generating the image, determine internally:

1. What is the single strongest engineering insight?
2. What is the triggering condition?
3. What is the system mechanism?
4. What is the consequence?
5. Which one of the five approved composition patterns communicates it best?
6. Does a code/log/tool panel materially improve the explanation?
7. Which ONE element deserves orange emphasis?
8. What is the ONE dominant failure or contrast?

Do not display this planning text in the image.

Then generate only the final visual.

---

# 27. FINAL QUALITY CHECK

Before finalizing, verify:

- The image communicates one primary engineering insight.
- The central idea is understandable in 2–3 seconds.
- The headline is no more than two lines.
- The main technical mechanism receives the most space.
- There is one dominant flow or comparison.
- The diagram uses approximately 3–7 major components when possible.
- Supporting text is minimal.
- There is at most one code/log/tool panel.
- No exact facts have been invented.
- Orange is used only for primary emphasis.
- Red represents actual failure/problem state.
- Green represents actual healthy/better state.
- Normal infrastructure remains neutral gray.
- Vendor branding does not dominate.
- Decorative objects are absent.
- Whitespace is preserved.
- "Prasad Rane" appears subtly at bottom-right.
- The image looks like it belongs beside every previous image in this series.

If any condition fails, simplify the design before final output.

---

# 28. POST-SPECIFIC INPUT TEMPLATE

Use the design system above for the following post.

## POST TITLE
[Insert the full LinkedIn post title.]

## POST CONTENT / IDEA
[Insert the LinkedIn post or a concise description.]

## CATEGORY
Choose one:
- AI ENGINEERING
- DISTRIBUTED SYSTEMS
- DATABASES
- PERFORMANCE
- SYSTEM DESIGN
- CLOUD ENGINEERING
- OBSERVABILITY
- .NET
- EVENT-DRIVEN SYSTEMS
- other clearly relevant engineering category

## CORE ENGINEERING PROBLEM
[What exactly is going wrong?]

## TRIGGER
[What starts the problem?]

## MECHANISM TO VISUALIZE
[How does the problem happen internally?]

## CONSEQUENCE
[What does the user/system experience as a result?]

## BETTER STATE / SOLUTION
[Optional. Include only if the post actually discusses a correction or alternative.]

## IMPORTANT TECHNICAL LABELS
[Optional. Include only exact terms that should appear, such as UUIDv4, .Result, WCU, DLQ, traceparent.]

## OPTIONAL TECHNICAL ARTIFACT
[Optional. Provide exact code/log/tool-call text if it must appear. If not supplied, do not invent exact text.]

## EXACT FACTS THAT MAY APPEAR
[List any exact benchmark values, model names, versions, timings, percentages, commands, or numbers that the image is allowed to use.]

---

# 29. CONTENT PRIORITY WHEN SPACE IS LIMITED

If everything cannot fit, preserve information in this order:

1. main engineering mechanism
2. problem and consequence
3. visual hook
4. critical technical labels
5. better state / comparison
6. optional code or log artifact
7. supporting explanation

Remove lower-priority material rather than reducing readability.

---

# 30. FINAL INSTRUCTION

Create a clean, square LinkedIn engineering infographic using this visual system.

Prioritize:

**clarity over decoration**  
**mechanism over branding**  
**accuracy over drama**  
**consistency over novelty**

The final result should look like a professionally art-directed engineering publication graphic created as part of a long-running, recognizable LinkedIn series by Prasad Rane.
