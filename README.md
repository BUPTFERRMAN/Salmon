# Salmon

**Reconstruct the past, not just predict the future.**  
**Salmon：从结果逆流而上，重建形成过程。**

Salmon is a multi-agent reconstruction workspace for case replay, historical backtracing, and causal chain analysis.

Most agent systems are designed to forecast what happens next. Salmon is built for a different mission: reconstruct how an outcome was formed. It turns scattered material into structured evidence, then derives multiple plausible paths with visible support, counter-evidence, and uncertainty.

Whether you are reviewing a case, replaying a historical process, diagnosing a complex situation, or repairing a narrative chain, Salmon provides a traceable reasoning workflow instead of a single rigid answer.

## Why Salmon

- Reverse-first by design: infer causes from outcomes, not future branches from prompts.
- Evidence-constrained reconstruction: every path is bound to evidence nodes in the source material.
- Multi-hypothesis output: compare competing explanations instead of overcommitting to one story.
- Replay-oriented results: inspect turning points, challenge assumptions, and rerun analysis.

## Staged Reconstruction Pipeline

1. `Document Parsing`  
   Parse PDF / TXT / MD content and extract entities, events, and temporal signals.
2. `Graph Construction`  
   Build people-event-clue structure and candidate causal links.
3. `Multi-Agent Reverse Reasoning`  
   Specialist agents collaborate and challenge each other across evidence, motives, suspicion, and reconstruction.
4. `Final Synthesis`  
   Deliver a primary path, alternatives, key evidence, uncertainty markers, and missing-data gaps.

## Technical Highlights

### 1) Reverse-First Multi-Agent Architecture
Salmon reasons from observed outcomes back to hidden drivers, rather than planning forward from goals.

### 2) Evidence-Constrained Reconstruction
Generated explanations must map to evidence and are tested against counter-signals to reduce plausible-but-wrong hallucinations.

### 3) Graph-Native Reasoning
Text is converted into graph structures so the system can expose overlooked nodes, latent couplings, role shifts, and necessary preconditions.

### 4) Multi-Hypothesis, Not Single Answer
Salmon compares multiple causal paths and surfaces strengths, weaknesses, and confidence levels for each.

### 5) From Fragments to Replay
The end goal is replayability: reconstructing how a situation evolved from early clues to final outcome.

## Current Capabilities

- Upload and parse text-based PDF, TXT, and Markdown files.
- Build an interactive people-event-clue graph.
- Run five specialist agents:
  - `Evidence Agent`
  - `Relationship Agent`
  - `Suspicion Agent`
  - `Reconstruction Agent`
  - `Judge Agent`
- Goal-conditioned output (not fixed templates):
  - reconstructed causal paths and key turning points
  - competing hypotheses with evidence and counter-evidence
  - uncertainty and confidence annotations
  - user-requested report structure (for example: narrative replay, role analysis, timeline, or gap checklist)

## Model Access

The backend uses an OpenAI-compatible API pattern.

Default local configuration is set for DeepSeek:

- `provider_name = DeepSeek`
- `base_url = https://api.deepseek.com`
- `model = deepseek-reasoner`

If `api.txt` exists in the workspace root, Salmon will read the API key automatically.

## Run

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Open [http://127.0.0.1:8010](http://127.0.0.1:8010)

## API

- `GET /api/model-config`
- `POST /api/model-config`
- `POST /api/case-parse`
- `POST /api/case-reason`
- `POST /api/case-workflow`

## Notes

- The current PDF parser is optimized for text-based PDFs, not scanned-image OCR.
- The current agent layer is a role-based analytical workflow, not a full autonomous society simulation.
- The graph view is interactive and 3D, with node and relation inspection.
