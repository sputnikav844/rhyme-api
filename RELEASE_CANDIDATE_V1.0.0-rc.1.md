# Russian Rhyme API — Release Candidate v1.0.0-rc.1

Status: **release candidate prepared; not deployed and not approved for production**.

## Candidate source revision

- Repository: `sputnikav844/rhyme-api`
- Branch: `feature/full-russian-rhyme-engine`
- Tested source commit: `1726928d6d98cf02f48c4e1efa04844bbd6a6cdc`
- Candidate record is maintained on the feature branch. The candidate-recording commit and its subsequent Gate 5 completion documentation were checked by CI; see the final verification below.

## Verification

The following GitHub Actions workflows completed successfully on the tested source commit above:

| Workflow | Run | Result |
|---|---:|---|
| tests | 43619703442 | success |
| Stress model evaluation | 43619703418 | success |

The release gates are recorded as follows:

- Gate 1 — legacy API compatibility and endpoint behaviour: complete.
- Gate 2 — reviewed rhyme regression corpus: complete (116/116 curated cases).
- Gate 3 — stress evaluation: complete (raw model 99/100 on isolated forms; model plus reviewed override 100/100; contextual homographs reported separately at 16/22).
- Gate 4 — deterministic dictionary/index build and search performance: complete.
- Gate 5 — release documentation, integration checklist, proprietary application-code notice, and CI verification: complete.

## Included release documentation

- `README.md` — installation, dictionary/index build, endpoints, examples, evaluation, limitations, licensing and rollback.
- `LICENSE` — proprietary application-code notice naming **Ch. Andrew**.
- `INTEGRATION_CHECKLIST_V1.md` — separately approved staging integration and rollback checks.
- `RELEASE_PLAN_V1.md` — release gates, scope and safety boundary.

Third-party licences remain separate. In particular, the Russian word-form archive remains MPL-2.0; dependency and model notices must be reviewed before commercial deployment.

## Release boundary

This is a versioned release-candidate record on the feature branch, **not a production release**.

No Git tag is created here: Git tags are repository-wide refs, not branch-scoped. Creating one would go beyond the agreed rule that all work remain confined to `feature/full-russian-rhyme-engine`. A repository-wide tag, merge, production deployment, VPS change, or live bot/n8n modification requires separate explicit approval.

No production integration has been performed. Before any future integration, follow `INTEGRATION_CHECKLIST_V1.md` in an isolated staging environment and obtain separate approval for production actions.
