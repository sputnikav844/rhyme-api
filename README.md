# Russian Rhyme API

Version 2 adds rhyme search, pair/line analysis and prosody endpoints while preserving the legacy `POST /rhyme` response used by existing n8n workflows.

## Run

Python 3.11+:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The first Russian stress-analysis request downloads stressonnx model assets from Hugging Face. Set `HF_HOME` to choose the cache directory. The Russian pipeline is model-based and has documented homograph limitations; results are estimates, not ground truth.

## Endpoints

- `GET /`, `GET /health`
- `POST /rhyme` — legacy compatible pair check.
- `POST /rhyme/check` — pair check with exact/near/none classification.
- `POST /rhyme/search` — candidate search. Supply `candidates` for a larger external lexicon; otherwise the bundled starter list is used.
- `POST /rhyme/check-lines` — checks endings of 2–16 lines.
- `POST /prosody/analyze` — syllable counts and stress marks.

### Search example

```json
{"word":"любовь","limit":10,"strict":true}
```

For production use, populate `data/rhyme_words.txt` with a legally redistributable, normalized Russian word-form lexicon. The included list is intentionally a small starter set, not a claim of comprehensive coverage. Do not redistribute OpenCorpora, Wiktionary or other lexical data until their exact dataset licence and attribution obligations have been reviewed.

### Backward compatibility

The old `POST /rhyme` input fields `word1`, `word2`, optional `stress1`, `stress2` and response keys `word1`, `word2`, `key1`, `key2`, `rhymes` are retained. No n8n workflow changes are required for this code update alone.

## Tests

```bash
pip install -r requirements.txt pytest httpx
pytest -q
```

## Licensing

Application code: see repository history. Runtime dependencies retain their own licences. stressonnx declares Apache-2.0 and documents the upstream model attributions in its repository. Review dependency and model licences before commercial deployment.
