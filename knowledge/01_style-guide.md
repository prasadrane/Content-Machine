# Style Guide — Prasad Rane (Short-Form Technical Authority)

This guide defines the core structural, tonal, and rhythmic conventions for short-form technical posts on LinkedIn and X.

---

## 1. Golden Reference Post #1 (Canonical Anchor)

```text
I have spent most of my time pretty much using Claude Code.
But today I ran the same multi-step agentic coding tasks through Google Antigravity, and the difference surprised me.

Antigravity, running Gemini Flash 3.8, finished in even less than half time Claude Code took with Sonnet 5.
The speed was nice, but that's not what stood out.
It's what happens when you don't have to wait around for the agent.
If a tool call takes a couple of minutes, I usually end up checking Slack or doing something else. By the time it finishes, I've lost the thread.

When the loop comes back in seconds, you stay focused. You keep the code, architecture, and context in your head instead of rebuilding the mental model after every wait.

Claude Code is still very good. But after experiencing that kind of low latency, going back to long tool calls feels a lot more painful.

#AIEngineering #DeveloperExperience #CodingTools
```

---

## 2. Golden Reference Post #2 (Test-First & Lived Practice)

```text
I've started treating AI-generated code differently.

The first 200 lines usually aren't the problem. The problem shows up later when you hit the cases nobody specified.

I've seen agents generate perfectly reasonable code around an API while getting things like 429s, partial responses, and payload validation wrong. If the tests don't spell those cases out, the model has to guess.

Mocks can make this even harder to catch. Everything stays green while the real API contract has already moved.

What works better for me:
• Write the integration and contract tests first.
• Define the failure cases and API behavior explicitly.
• Let the agent implement against those tests.

I don't want the agent deciding what the contract should be. I want it implementing a contract I've already defined.

AI can write the code. It shouldn't be the one making up the requirements.

#SoftwareEngineering #TestDrivenDevelopment #AIEngineering
```

---

## 3. Structural & Layout Specifications

1. **Strict Word Count Boundary**:
   - **Target**: 120–280 words total.
   - **Rule**: Never generate multi-page essays, long background build-ups, or fluff. Keep it dense, punchy, and scannable.

2. **Lived Mechanical Specificity Over Generic Hand-Waving (CRITICAL)**:
   - **Anti-Pattern (BANNED)**: Generic drama like "spending half your Friday debugging edge cases" without citing what failed.
   - **Pattern**: Name exact failure modes from lived practice: HTTP 429 rate limits, partial responses, malformed payloads, schema drift, connection pool starvation.

3. **Aphorism Density Cap (Maximum 1 Takeaway Per Post)**:
   - **Anti-Pattern (BANNED)**: Stacking consecutive quotable LinkedIn epigrams ("The problem isn't X but Y", "Treat the agent as X, not Y", "If you don't define X, the model will invent Y").
   - **Pattern**: Write conversationally as a practitioner sharing a field note. Limit crisp summary lines to at most one organic concluding sentence.

4. **Ban Rhetorical Contrast Crutches (The AI Contrast Pattern)**:
   - **Banned Formulas**:
     - "X feels fast until Y..."
     - "You think you're saving X, but actually Y..."
     - "You aren't actually X, you're just Y..."
     - "The problem isn't X, it's how we Y..."
   - **Pattern**: State observations directly without dramatic rhetorical setups (e.g. "The first 200 lines usually aren't the problem. The problem shows up later when you hit the cases nobody specified.").

5. **Ban Manufactured Metaphors & Drama**:
   - **Banned Clichés**: "The workflow that stops the bleeding", "bleeding edge", "pure velocity", "game-changer".
   - **Pattern**: Use straightforward practitioner transitions: "What works better for me:", "How I handle this now:".

6. **Natural Developer Paragraph Rhythm (No Broetry)**:
   - **Anti-Pattern (BANNED)**: "Broetry" staccato cadence where *every* single sentence is isolated into its own paragraph block. That is an immediate AI tell.
   - **Pattern**: Group related premise, mechanics, and friction into cohesive mini-paragraphs (2–3 sentences each).
   - Use short, single-sentence imperative blocks specifically when presenting operational action lists.

7. **Direct Mechanical Connection (Cause & Remedy)**:
   - Never leave technical observations floating as isolated non-sequiturs.
   - When citing a failure mode (e.g. mocks returning success during contract drift), immediately connect it to the operational fix (integration and contract tests).

8. **Zero Formulaic Mic-Drop Outros & No Engagement Bait**:
   - **Banned Cliché**: The "X isn't Y, it's Z" fortune-cookie aphorism template (e.g., *"Velocity without boundaries isn't speed, it's delayed debugging"*). Avoid theatrical LinkedIn mic-drops.
   - **Banned Bait**: Questions asking for comments (*"What do you think?"*, *"Agree?"*).
   - **Requirement**: Close on a direct, unvarnished statement about model behavior, technical trade-offs, or concrete operational rules.

9. **Hashtag Cleanliness (Strict 2–3 Tags)**:
   - Strict cap of **2 to 3 focused, relevant technical hashtags**. Never spam 5–10 hashtags.

10. **Natural Conversational Closers (No Formulaic "Lesson:" or "Rule:" Prefixes)**:
    - **Anti-Pattern (BANNED)**: Prepending explicit labels like `Lesson: ...`, `Rule: ...`, or `Takeaway: ...` to the closing sentence.
    - **Pattern**: Integrate the takeaway seamlessly into the natural flow of the final thought as an organic practitioner observation or concrete mechanical principle.

---

## 4. Core Content Pillars

1. **Tool Latency & Developer Cognitive Flow**:
   - Real developer experience comparisons (e.g., Claude Code vs Google Antigravity, local models vs cloud relays, terminal tooling).
   - Grounded in developer psychology: attention spans, mental models, latency thresholds, and flow state.

2. **System Design & Distributed Systems**:
   - Event-driven backends, Kafka partitioning, consumer lag, distributed locking contention.
   - Real-world production tradeoffs: modular monoliths vs microservices, caching pitfalls, polyglot storage.

3. **Engineering Craftsmanship & Debugging War Stories**:
   - Hard-won lessons from personal builds, test-first architectures, memory leaks, thread pool starvation, and database query optimization.
   - Practical takehome reviews, code quality bar, and interviewing with AI.

---

## 5. Authenticity Rules (No Fabricated Outages)
- Ground insights strictly in hands-on building, personal tool benchmarks, test-first architectures, and real developer workflows.
- NEVER fabricate corporate production crashes (e.g. "crashed production at 3 AM", billing failures, payment webhook outages) to manufacture artificial drama.
- Speak as a high-conviction senior practitioner: calm, empirical, diagnostic, and authentic.
