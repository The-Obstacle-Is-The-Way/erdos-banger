# Documentation

This repo uses a **modified Diátaxis** documentation structure:

- **Getting Started** (tutorials) — install, run, and see value fast
- **How-to / Developer Guides** — accomplish specific tasks (testing, configuration, extending)
- **Reference** — precise, factual surfaces (CLI flags, env vars, schemas)
- **Explanation / Architecture** — why the system is structured the way it is

Design history and engineering process docs (specs, ADRs, debt, bugs) are kept, but are **not** the primary onboarding path.

## Getting Started

- [Quickstart](./getting-started/quickstart.md)
- [Common Usage](./getting-started/usage.md)

## Developer Guides

- [Configuration](./developer/configuration.md) (env vars, paths, caches)
- [Testing](./developer/testing.md)
- [E2E Testing](./developer/e2e-testing.md)
- [CLI Reference (generated)](./developer/cli-reference.md)
- [PDF Conversion](./developer/pdf-conversion.md) (optional `[pdf]` extra)

## Architecture

- [Overview](./architecture/overview.md)
- [CLI Design](./architecture/cli.md)
- [Data Pipeline](./architecture/data-pipeline.md)

## Project & Process Docs

| Category | Index | Next ID |
|----------|-------|---------|
| [Specs](./_specs/README.md) | Design specs + roadmap (mostly archived) | SPEC-036 |
| [ADRs](./adr/README.md) | Architecture decision records | ADR-004 |
| [Bugs](./_bugs/README.md) | Bug reports & adversarial reviews | BUG-034 |
| [Debt](./_debt/README.md) | Technical debt tracking | DEBT-108 |
| [Vendor Docs](./vendor-docs/README.md) | External API notes | — |
| [Ralph Wiggum Protocol](./_ralphwiggum/protocol.md) | Autonomous sprint loop | — |
| [Archive](https://github.com/The-Obstacle-Is-The-Way/erdos-banger/tree/main/docs/_archive) | Completed specs, bugs, debt, and process docs | — |

## Master Documents

- [Master Vision](./_specs/master-vision.md) — long-range architecture and roadmap
- [Master Qualifications](./_specs/master-qualifications.md) — scope and requirements

## Future / Brainstorming

- [Future Ideations](./future/future-ideations.md)
- [Research State Management (v3)](./future/research-state-management-v3.md)

## Numbering Convention (Process Docs)

- **Specs:** Sequential, permanent (`SPEC-001`, `SPEC-002`, …)
- **Bugs:** Sequential (`BUG-001`, `BUG-002`, …)
- **Debt:** Sequential (`DEBT-001`, `DEBT-002`, …)

Numbers are never reused. Each category README is the SSOT for that category.
