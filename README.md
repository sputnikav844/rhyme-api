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

Application-code licence: **not yet declared** in this repository. The repository owner must select and add an explicit licence before public redistribution or commercial integration; this release candidate must not be treated as granting permission to reuse the application code. Runtime dependencies retain their own licences. `stressonnx` declares Apache-2.0 and documents upstream model attributions in its repository. The word-form archive is MPL-2.0; see `data/DICTIONARY_LICENSE.txt`. Review dependency and model licences before commercial deployment.


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
- SHA-256 исходного архива, число строк источника, число повторов, число уникальных
  проиндексированных форм, размеры ключевых пространств и максимальные размеры корзин;
- версию схемы и идентификатор алгоритма сборки.

Сборка детерминирована: формы и ключи сортируются, повторные словоформы исключаются,
gzip записывается с фиксированными метаданными. Повторная сборка из того же архива
должна давать побайтно одинаковый файл. Проверки этого свойства и checksum входят
в CI. Индекс старого алгоритма без нужной сортировки API отвергает с явным сообщением:
его необходимо пересобрать приведённой ниже командой перед запуском обновлённого API.
Для воспроизведения локально:

```bash
python scripts/download_dictionary.py
python scripts/build_phonetic_index.py
python scripts/benchmark_search.py
```

CI также проверяет порядок выдачи, удаление дубликатов, лимит результатов, fallback
на полный словарь и резервный seed-словарь. Benchmark измеряет время первого холодного
запроса (включая ленивую загрузку индекса и модели ударений), а также p50/p95 пяти
частых запросов в строгом и relaxed режимах на GitHub Actions ubuntu-latest. Warm p95
должен быть не более 1000 мс. Это измерение на CI runner, а не гарантия задержки
на любом сервере.

### Последний контрольный прогон полного индекса (GitHub Actions ubuntu-latest)

Для закреплённого архива с SHA-256
`8ac7fbc26204d437d3e8be8609ba6a6e2a0afae17548cdfa0ff01c13de55e3fa`
сборка дала следующие показатели:

| Показатель | Значение |
|---|---:|
| Строк в исходном архиве | 2 367 159 |
| Повторных записей | 12 780 |
| Исключено невалидных / непроиндексируемых строк | 24 448 |
| Уникальных словоформ в индексе | 2 329 931 |
| Точных фонетических ключей | 2 211 |
| Корзин приблизительных рифм | 1 673 |
| Максимальная корзина | 414 322 |

Сборка полного индекса заняла около 71 секунды на этом CI runner.

В том же контрольном прогоне benchmark выполнил 50 тёплых запросов
(5 частых слов, строгий и relaxed режимы): медиана — **2,71 мс**,
p95 — **3,53 мс**, максимум — **6,24 мс**. Первый холодный запрос —
**1 938,87 мс**; он включает ленивую загрузку индекса и модели ударений.
Порог CI для warm p95 — 1 000 мс. Эти значения характеризуют только
GitHub Actions ubuntu-latest и не являются обещанием задержки на любом VPS.

**Важное ограничение ударений:** словарные формы индексируются с fallback-эвристикой библиотеки `phonetic-rhyme`, а не с нейросетевым определением ударения для каждой из миллионов форм. Для целевого слова API использует `stressonnx`, если модель доступна. Поэтому омографы и исключения могут требовать явного параметра `stress` и отдельной лингвистической проверки. Индекс обеспечивает поиск по фонетическим ключам, но сам по себе не гарантирует безошибочное ударение каждой словоформы.


## Endpoint request examples

All request bodies are JSON. Validation failures from the new endpoints return HTTP
`422` with FastAPI/Pydantic validation details.

Pair check:

```json
{"word1":"рад","word2":"брат","stress1":0,"stress2":0}
```

Rhyme search (optional `stress` is a zero-based vowel index; `strict:false`
allows near-rhymes):

```json
{"word":"любовь","limit":10,"strict":false}
```

Line endings (2–16 lines):

```json
{"lines":["Я вижу свет","И слышу ответ"],"strict":false}
```

Prosody and stress:

```json
{"text":"Молоко и хлеб"}
```

Legacy `POST /rhyme` deliberately retains its original permissive input schema
and boolean semantics for existing integrations. Do not assume that its validation
behaviour matches the newer endpoints.

## Rollback considerations

This repository is not deployed by CI. For a future self-managed deployment,
record the currently deployed commit and keep the previous application package
and data files before upgrading. If a release causes a regression:

1. Stop the API service using the deployment's service manager.
2. Restore the previous known-good application commit/package and its matching
   dependency lock/environment.
3. Restore the previous compatible phonetic index. An index built with an older
   algorithm may be rejected by a newer application; do not mix application and
   index versions.
4. Start the service and verify `GET /health`, then run smoke tests for
   `POST /rhyme` and the endpoints actually used by the integration.
5. Keep the failed release and logs for diagnosis; do not delete the only backup.

Exact service commands, paths and snapshot procedure must be supplied by the
target host's deployment runbook. No production rollback or deployment is
performed by this repository workflow.
