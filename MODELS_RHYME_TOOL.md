# Models tool specification — Russian rhyme assistant

Status: implementation contract for the `feature/full-russian-rhyme-engine` branch. Not deployed.

## Tool identity

- Name: `rhyme_assist`
- Purpose: find phonetic rhyme candidates for a Russian anchor word without forcing them into the lyric.
- HTTP method/path: `POST /rhyme/assist`
- Content type: `application/json`

## Function parameters

```json
{
  "type": "object",
  "properties": {
    "word": {"type": "string", "description": "Одно русское слово — естественное опорное окончание строки."},
    "mode": {"type": "string", "enum": ["natural", "exact", "free"], "default": "natural"},
    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 12},
    "stress": {"type": "integer", "minimum": 0, "description": "Необязательный индекс ударной гласной, начиная с нуля."},
    "syllables": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Необязательное число слогов у кандидата."}
  },
  "required": ["word"],
  "additionalProperties": false
}
```

## Model instructions

1. Сначала сформулируй мысль строки и выбери естественное опорное слово. Не выбирай слово только потому, что к нему легче найти рифму.
2. В обычном режиме вызови `rhyme_assist` с `mode=natural`. Это возвращает точные и приблизительные фонетические совпадения.
3. Используй `mode=exact` только если пользователь явно просит точную рифму или точность важна для выбранной схемы.
4. Используй `mode=free`, когда рифма не нужна или мешает естественности.
5. Рассматривай `results` как фонетические подсказки, а не готовые строки. Самостоятельно проверь значение, часть речи, падеж/время/согласование, естественный порядок слов, образность и возможность пропеть строку.
6. Не вставляй кандидат, если ради него приходится менять смысл, использовать неестественную инверсию, добавлять слова-пустышки или ломать грамматику.
7. Если подходящего слова нет, смени опорное слово или конструкцию строки; допустимы near-rhyme и отсутствие рифмы.
8. Ограничь поиск одной-двумя попытками на пару строк. Не запускай бесконечные циклы перебора.
9. После написания куплета при необходимости проверь окончания через `POST /rhyme/check-lines`. Эта проверка оценивает звук, а не художественное качество.
10. Приоритеты: смысл и история → естественный русский → эмоция и выразительность → ритм и напевность → точность рифмы.

## HTTP request example

```json
{"word":"любовь","mode":"natural","limit":12}
```

## Response handling

- `status=ok`: inspect candidate `word`, `match` (`exact` or `near`) and `syllables`.
- `status=skipped`: free mode intentionally did not search; continue writing without forcing a rhyme.
- Empty `results`: do not invent a result. Change anchor/line structure or accept no rhyme.
- HTTP 422: ask for or derive one valid Russian word; do not retry the same invalid input.
- Timeout/unavailable: continue composition without the tool and do not claim phonetic validation occurred.

## Important limitations

The service does not determine semantic relevance, part of speech, grammatical compatibility, emotional suitability or singability. Candidate stress in the large dictionary may be heuristic; explicit stress and context can matter. The model remains responsible for literary judgement and the user remains the final decision-maker.

## Telegram "Рифма" button

The Telegram button/command should call this same endpoint, not duplicate the phonetic algorithm. Pass the user's anchor word and selected mode. Display candidates with their exact/near label and syllable count. Handle an empty result and API errors explicitly. Keep the existing legacy `/rhyme` mapping and all unrelated bot routes unchanged.

Repository changes do not edit the live n8n workflow. The actual button wiring must be performed in an isolated workflow copy after its export is provided and reviewed; production activation is a separate approval.