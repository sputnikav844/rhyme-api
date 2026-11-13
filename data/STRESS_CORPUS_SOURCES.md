# Stress quality corpus sources and method

The reference corpus in `data/stress_quality_cases.json` is curated against
normative Russian lexicographic sources, not generated from the model being
evaluated.

## Primary references

1. **Большой словарь ударений русского языка** (М. Л. Каленчук,
   О. В. Антонова, Д. М. Савинов, Н. В. Никитин; Грамота, 2025).
   The publisher describes approximately 30,000 entries and explicitly
   documents current literary stress norms and accepted variants:
   https://gramota.ru/izdatelstvo/catalog/slovari-i-spravochniki/bolshoy-slovar-udareniy-russkogo-yazyka-2025
2. **Русский орфографический словарь**, 6th edition (В. В. Лопатин and
   О. Е. Иванова, 2023). Its electronic version marks normative stress in
   non-monosyllabic headwords and forms:
   https://gramota.ru/biblioteka/slovari/russkij-orfograficheskij-slovar/udarenie-proiznoshenie

The following Gramota references were used for spot-checking high-risk
forms and inflectional stress:
- `оптовый`: https://gramota.ru/meta/optovyy
- `договор`: https://gramota.ru/meta/dogovor
- `принять` and its past-tense forms: https://gramota.ru/meta/prinyat
- `звонишь`: https://gramota.ru/poisk?mode=all&query=звонишь
- `диспансер`: https://gramota.ru/poisk?mode=journal&query=диспансер
- `блага`: https://gramota.ru/poisk?mode=spravka&query=блага

## Corpus conventions

- `expected_stress` is a **zero-based index among vowels**, not a character
  offset or syllable number.
- The isolated unambiguous section contains at least 100 distinct wordforms.
- Contextual homographs are marked `ambiguous: true`, carry a sense-specific
  sentence and are evaluated in a separate context-disambiguation metric.
  They are never assigned a global word-level override.
- `yo_is_stressed: true` is used only where the letter `ё` itself encodes
  the reference stress and the model output does not need a combining acute.
- Corpus accuracy is a curated regression metric only. It is not a claim about
  the model's accuracy on all Russian vocabulary, dialects, names or contexts.
