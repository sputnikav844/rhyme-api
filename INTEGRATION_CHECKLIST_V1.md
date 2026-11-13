# Integration checklist — Russian Rhyme API v1.0 candidate

This checklist is for a future, separately approved integration. It is not
permission to deploy, merge, or modify a live bot or n8n workflow.

## Before integration
- [ ] Owner has selected and added an explicit application-code licence.
- [ ] Review licences/notices for the application, dependencies, stress model and
      MPL-2.0 dictionary archive; preserve required notices.
- [ ] Select the exact candidate commit and record its SHA-256/commit SHA.
- [ ] Confirm Python 3.11+, dependency installation and model-cache/network policy.
- [ ] Download the pinned word-form archive and verify its SHA-256.
- [ ] Build the phonetic index from that archive; record build metadata and checksum.
- [ ] Confirm application and index use the same required build-algorithm ID.
- [ ] Capture a backup of the currently deployed application, environment,
      dependency set, index and service configuration.

## API contract smoke tests
- [ ] GET /health returns HTTP 200 and status=ok.
- [ ] POST /rhyme retains legacy fields word1, word2, key1, key2, rhymes.
- [ ] Compare legacy /rhyme outputs against the currently deployed API on a
      fixed set of representative pairs before switching traffic.
- [ ] POST /rhyme/check returns exact, near or none as documented.
- [ ] POST /rhyme/search returns bounded, de-duplicated results and expected source.
- [ ] POST /rhyme/check-lines handles 2–16 lines and strict/relaxed modes.
- [ ] POST /prosody/analyze returns syllable counts and stress metadata.
- [ ] Invalid payloads return documented 422 responses on new endpoints.
- [ ] Test ambiguous words with explicit stress; do not treat model estimates as
      authoritative linguistic truth.

## n8n / Музыкальный продюсер integration (future approval required)
- [ ] Identify the exact workflow and HTTP request block that will call the API.
- [ ] Keep the existing legacy POST /rhyme request/response mapping unchanged
      unless a separately reviewed migration is approved.
- [ ] Test in an isolated workflow or staging copy, never on the live workflow first.
- [ ] Verify timeout, retry, error handling and response-field mapping.
- [ ] Confirm no changes to project state, lyrics, payments or unrelated bot routes.
- [ ] Run a small manually approved test set and compare expected results.

## Rollback readiness
- [ ] Previous application commit/package is restorable.
- [ ] Previous compatible phonetic index and dependency environment are backed up.
- [ ] Service restart and health-check commands are documented for the target host.
- [ ] Rollback has been rehearsed in staging.
- [ ] Production switch occurs only after explicit owner approval.

## Release boundary
- No production deployment, VPS changes, bot/n8n edits, branch merge or main
  update is authorized by this checklist.
