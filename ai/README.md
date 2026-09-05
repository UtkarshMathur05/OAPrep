# AI / RAG

Plain Python functions calling Gemini. No agent framework.

## Pipeline

| Step | Module | Prompt |
| --- | --- | --- |
| 1. Memory extraction | `extraction/genome.py` | `prompts/extraction_prompt.txt` |
| 2. Problem Genome schema | `models/problem_genome.py` | — |
| 3. Embeddings | `retrieval/embeddings.py` | — |
| 4. Semantic retrieval | `retrieval/vector_search.py` | — |
| 5. Reranking | `retrieval/reranker.py` | `prompts/reranking_prompt.txt` |
| 6. Reconstruction | `reconstruction/reconstruct.py` | `prompts/reconstruction_prompt.txt` |
| 7. Test generation | `verification/test_generator.py` | — |

`gemini_client.py` holds the shared Gemini calls (`generate_text`,
`generate_json`, `embed`, `embed_batch`, `load_prompt`).

Every module is a stub raising `NotImplementedError` — fill them in one at a time.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then set GEMINI_API_KEY
```

Run from the repo root so `import ai.*` resolves:

```bash
python -c "from ai.extraction.genome import extract_genome; print(extract_genome('grid, move right or down, minimize cost'))"
```

## Working independently

The modules take and return Pydantic models, so each step is testable on its own
with a hand-built `ProblemGenome` — no backend or frontend needed. Retrieval is
the only step that needs Postgres running (`docker compose up -d`).
