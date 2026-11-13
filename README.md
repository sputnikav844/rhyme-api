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

### Rhyme classification

The legacy `POST /rhyme` keeps its original phonetic-library key generation and
`do_rhyme` boolean. The newer `POST /rhyme/check` uses the model-aware stress
resolver when stress is omitted; explicit `stress1` and `stress2` values are
zero-based vowel positions.

Both new pair and line checks use the same classifier:
- `exact`: complete stressed phonetic keys match;
- `near`: the complete keys differ, but their final three phoneme symbols match;
- `none`: neither condition is met.

For `POST /rhyme/check-lines`, `strict: true` suppresses `near` results.
The ending key uses the stress mark found in the complete line when available.

### Stress quality evaluation

Run the curated stress evaluation after installing `requirements.txt`:

```bash
python scripts/evaluate_stress.py
```

The reference set contains 100 distinct unambiguous isolated wordforms and 22
contextual homograph examples. The evaluator reports raw-model and
model-plus-overrides metrics separately; contextual disambiguation is reported
as its own group. Stress indices are zero-based vowel positions. Reviewed
word-level exceptions require a reason and a lexicographic source in
`data/stress_overrides.json`. Corpus sources and conventions are documented in
[`data/STRESS_CORPUS_SOURCES.md`](data/STRESS_CORPUS_SOURCES.md).

These figures describe only the curated regression set, not general Russian
stress accuracy.

## Tests

```bash
pip install -r requirements.txt pytest httpx
pytest -q
python scripts/download_dictionary.py
```

## Licensing

Application code: see repository history. Runtime dependencies retain their own licences. stressonnx declares Apache-2.0 and documents the upstream model attributions in its repository. Review dependency and model licences before commercial deployment.


## Полный фонетический индекс

Словарь загружается отдельно, а фонетический индекс строится офлайн:

```bash
python scripts/download_dictionary.py
python scripts/build_phonetic_index.py
```

По умолчанию создаётся `data/phonetic_index.json.gz`. API загружает готовый индекс при первом поиске, не строит его при запуске сервиса и не прогоняет весь словарь на каждом запросе. Путь можно переопределить переменной `RHYME_PHONETIC_INDEX`.

Индекс содержит:
- точные фонетические ключи от ударной гласной до конца слова;
- отдельные корзины по последним трём фонемам для приблизительных рифм;
- контрольную сумму исходного архива и число проиндексированных словоформ.

**Важное ограничение ударений:** словарные формы индексируются с fallback-эвристикой библиотеки `phonetic-rhyme`, а не с нейросетевым определением ударения для каждой из миллионов форм. Для целевого слова API использует `stressonnx`, если модель доступна. Поэтому омографы и исключения могут требовать явного параметра `stress` и отдельной лингвистической проверки. Индекс обеспечивает поиск по фонетическим ключам, но сам по себе не гарантирует безошибочное ударение каждой словоформы.
