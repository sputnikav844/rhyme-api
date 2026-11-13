# Russian Rhyme API — finite v1.0 completion plan

This document defines the finish line for the first production-candidate release.
It is intentionally not a promise to encode every Russian pronunciation or every
dictionary exception. The goal is a useful, testable, documented API with known
limits and a reproducible offline index.

## Scope of v1.0

Included:
- Preserve the legacy `POST /rhyme` request and response contract.
- Keep the current API endpoints: pair check, rhyme search, line checks and prosody.
- Use the pinned Russian word-form archive and reproducibly build the phonetic index.
- Use neural stress prediction where available and a reviewed override lexicon for
  known exceptions.
- Return explicit distinctions between exact, near and non-rhyme results; do not
  present uncertain stress or weak sound similarity as guaranteed exact rhyme.
- Document model, dictionary, dependency and runtime limitations.

Not included in v1.0:
- Perfect stress prediction for every Russian homograph and inflected form.
- Exhaustive coverage of names, slang, dialects, foreign words and rare forms.
- Semantic, grammatical or artistic judgement of poetic quality.
- Production deployment, bot/n8n changes, or merging into `main` without approval.

## Release gates

### Gate 1 — Compatibility and API behaviour
- Existing legacy API tests pass unchanged.
- Every documented endpoint has success, invalid-input and edge-case tests.
- Response fields and error semantics are documented.

### Gate 2 — Phonetic quality
- Maintain a reviewed regression corpus of at least 100 word pairs.
- Cover exact rhymes, near-rhymes and negatives, including final devoicing,
  softness, ё/е, vowel reduction, consonant clusters and short stressed endings.
- Every corpus case has an explanation and explicit stress positions where needed.
- CI reports failures by pair; all reviewed regression cases must pass.
- Do not claim general linguistic accuracy from this curated corpus alone.

### Gate 3 — Stress quality
- Maintain a reviewed corpus of at least 100 words/forms with reference stress.
- Report raw model accuracy separately from accuracy after curated overrides.
- Record homographs and context-dependent cases as ambiguous rather than silently
  treating one stress as universally correct.
- Keep overrides sourced/reasoned and covered by unit tests.

### Gate 4 — Full dictionary search and performance
- Build the pinned word-form archive and phonetic index in CI from scratch.
- Verify word-form count, source checksum, index schema and deterministic output
  statistics.
- Test search result ordering, duplicates, limits, missing-index fallback and
  common query latency on a documented CI runner.
- Fix release-blocking defects; defer cosmetic or low-impact enhancements.

### Gate 5 — Release candidate
- All CI workflows are green on the release commit.
- README documents installation, index build, endpoints, examples, limitations,
  licensing and rollback considerations.
- Tag a versioned release candidate on the feature branch and prepare a separate
  integration checklist.
- Stop feature work at this point. Further additions become separately scoped
  post-v1.0 issues.

## Current status (2026-11-13)

- Full dictionary/index build has completed in CI: 2,342,711 wordforms,
  2,211 exact phonetic keys and 1,673 near buckets.
- Stress override for `начался` is integrated and covered by unit tests.
- Latest test workflow passed after fixing combining-acute escaping.
- Gates 1–5 are not yet all complete; in particular the rhyme and stress
  regression corpora still need expansion and the final release checklist remains.

## Safety boundary

All development stays on `feature/full-russian-rhyme-engine`. Do not change
`main`, deploy to the production VPS, modify the live bot/API/n8n workflows,
or merge/release for production without the user's explicit approval.
