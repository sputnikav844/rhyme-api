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
- `POST /rhyme/search` — candidate search. Supply `candidates` for a larger external lexicon; otherwise the full Russian word-form list is used when installed, falling back to the bundled starter list.
- `POST /rhyme/check-lines` — checks endings of 2–16 lines.
- `POST /prosody/analyze` — syllable counts and stress marks.

### Search example

```json
{"word":"любовь","limit":10,"strict":true}
```

A pinned Russian word-form archive (about 2.36 million forms) is available under MPL-2.0. Download and verify it with `python scripts/download_dictionary.py`; the API then loads `data/ru_RU.txt.gz` automatically. The archive is not committed to Git. See `data/DICTIONARY_LICENSE.txt` for source, checksum and licence obligations. Without the archive, only the small starter list is used.

### Backward compatibility

The old `POST /rhyme` input fields `word1`, `word2`, optional `stress1`, `stress2` and response keys `word1`, `word2`, `key1`, `key2`, `rhymes` are retained. No n8n workflow changes are required for this code update alone.

## Tests

```bash
pip install -r requirements.txt pytest httpx
pytest -q
python scripts/download_dictionary.py
```

## Licensing

Application code: see repository history. Runtime dependencies retain their own licences. stressonnx declares Apache-2.0 and documents the upstream model attributions in its repository. Review dependency and model licences before commercial deployment.
