# Salmon

Salmon is a multi-agent reconstruction workspace for case replay, historical backtracing, and causal chain analysis.

It accepts `PDF / TXT / MD` material or direct text input, then runs a staged workflow:

1. Document parsing
2. Relationship graph construction
3. Multi-agent reverse reasoning
4. Final synthesis

## Current Capabilities

- Upload and parse text-based PDF, TXT, and Markdown files
- Build an interactive people-event-clue graph
- Run five specialist agents:
  - `Evidence Agent`
  - `Relationship Agent`
  - `Suspicion Agent`
  - `Reconstruction Agent`
  - `Judge Agent`
- Output:
  - case explanation
  - suspect ranking
  - reenactment timeline with evidence references

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
