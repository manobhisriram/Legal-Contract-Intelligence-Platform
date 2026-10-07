# Development

## Setup

```bash
bash scripts/setup.sh
source venv/bin/activate
```

Or manually: Python 3.11, then `pip install -r requirements.txt -r frontend/requirements.txt -r requirements-dev.txt`. System packages `poppler`, `libmagic` and `tesseract` are required for PDF processing.

## Running

```bash
alembic upgrade head
bash scripts/dev.sh                                # API :8000 and UI :8501
# or individually
PYTHONPATH=. uvicorn backend.api.main:app --reload
BACKEND_URL=http://localhost:8000 streamlit run frontend/app.py
```

## Tests and linting

```bash
pip install -r requirements-dev.txt     # lightweight subset used by CI
python -m pytest tests
python -m pyflakes backend frontend tests alembic
```

`requirements-dev.txt` intentionally omits the heavy document-processing stack (`unstructured`, `pdf2image`); tests that touch it mock the boundary. Tests set inert placeholder settings in `tests/conftest.py`, so no keys or services are required.

## Conventions

- Settings: add new variables to `backend/core/config.py` **and** `.env.example`.
- Metrics: define names in `backend/core/metrics.py` using `legal_intel.<subsystem>.<measurement>`; a test enforces the naming convention.
- Agents: new model-backed stages should wrap calls in `LLMSpan`, emit `metrics.agent_call`, and return an empty, well-formed result on failure.
- Milvus filters: build expressions with `contract_filter`; never interpolate request data directly.
- Schema changes: add an Alembic revision and update `backend/db/models.py` together.
- Adversarial cases: add contracts to `ADVERSARIAL_CONTRACTS` in `backend/agents/red_team_agent.py`; the integrity test expects 5 categories of 10 and unique IDs, so update it deliberately if the suite grows.

## Dependency notes

Versions are pinned and were resolved together (`uv pip compile` against Python 3.11). `mcp==1.0.0` constrains `pydantic>=2.8` and `starlette>=0.39`. `marshmallow<4` is required by `ddtrace` 2.9 through `environs`. `unstructured[pdf]` pulls in a large ML stack (PyTorch); expect a large backend image.
