# Research Mode Roadmap

[English](#english) | [Русский](#русский)

## English

Research Mode is an OpenClaw-first skill for durable, review-gated background
research. It is not a standalone Python package yet. The roadmap below describes
the public direction of the GitHub repository and avoids private workspace,
operator, or task-specific context.

### Completed in v0.3.0

- Added public repository onboarding: `ROADMAP.md`, `CONTRIBUTING.md`, issue
  templates, support/security docs, and release-boundary checks.
- Documented public contracts: stable/internal CLI surface, JSON schemas,
  `state_version`, migration policy, and architecture decision context.
- Hardened public/package-facing path surfaces so generated summaries avoid
  leaking unnecessary host layout details while local diagnostics stay useful.
- Added read-only `health` diagnostics and `reconcile` as a read-only alias for
  state, artifacts, runtime, delivery, and recovery status.
- Improved partial-failure recovery so operators can distinguish `ok`,
  `repair_needed`, `manual_review_needed`, `blocked`, and
  `fresh_continuation_recommended`.

### Now

- Make task-local package installation more governed without making ordinary
  research tasks painful: audit trails, optional strict policy, and reproducible
  package snapshots where useful.
- Add a refine/pivot ladder for repeated low-yield iterations so long-running
  tasks change strategy instead of repeating weak searches.
- Persist reusable research lessons across similar tasks when that can be done
  transparently and safely.

### Next

- Add versioned deliverable profiles for repeated output shapes such as briefs,
  source matrices, reports, and implementation plans.

### Later

- Improve portability beyond the current Linux/OpenClaw-first baseline,
  including lock abstractions and a cross-platform state strategy.
- Revisit larger-scale storage if traces become too large for simple task-local
  files, with a migration path toward SQLite or PostgreSQL-backed views.
- Consider a `pyproject.toml` and CLI entrypoint only if it improves maintainer
  ergonomics without implying that Research Mode is a standalone product.

### Not planned

- A hosted research service.
- A generic agent framework.
- A replacement for OpenClaw cron, skill loading, or messaging adapters.
- Publishing private task roots, corpora, generated reports, chat identifiers,
  webhooks, owner-specific configuration, or local workspace paths.

## Русский

Research Mode — OpenClaw-first skill для длительных фоновых исследований с
ревью перед выдачей результата. Это пока не самостоятельный Python package.
Roadmap ниже описывает публичное направление GitHub-репозитория и не включает
приватный workspace-контекст, операторские заметки или детали конкретных задач.

### Выполнено в v0.3.0

- Добавлен публичный onboarding репозитория: `ROADMAP.md`, `CONTRIBUTING.md`,
  issue templates, support/security docs и проверки release boundary.
- Описаны публичные контракты: stable/internal CLI surface, JSON schemas,
  `state_version`, migration policy и архитектурные решения.
- Усилены public/package-facing path surfaces: generated summaries не должны
  раскрывать лишние детали host layout, но локальная диагностика остается
  полезной.
- Добавлена read-only диагностика `health` и read-only alias `reconcile` для
  state, artifacts, runtime, delivery и recovery status.
- Улучшено восстановление после частичных сбоев: оператор видит `ok`,
  `repair_needed`, `manual_review_needed`, `blocked` и
  `fresh_continuation_recommended`.

### Сейчас

- Сделать установку task-local packages управляемее без лишней бюрократии для
  обычных исследований: audit trail, optional strict policy и воспроизводимые
  package snapshots там, где это полезно.
- Добавить refine/pivot ladder для серий слабых итераций, чтобы долгие задачи
  меняли стратегию, а не повторяли неудачный поиск.
- Переиспользовать уроки между похожими исследованиями, если это можно сделать
  прозрачно и безопасно.

### Дальше

- Добавить версионированные deliverable profiles для повторяемых форматов:
  briefs, source matrices, reports и implementation plans.

### Позже

- Улучшить portability за пределами текущего Linux/OpenClaw-first baseline:
  абстракции блокировок и cross-platform strategy для состояния.
- Вернуться к storage scaling, если traces станут слишком большими для простых
  task-local files, с возможным migration path к SQLite или PostgreSQL-backed
  представлениям.
- Подумать о `pyproject.toml` и CLI entrypoint только если это реально улучшит
  сопровождение и не создаст впечатление standalone-продукта.

### Не планируется

- Hosted research service.
- Универсальный agent framework.
- Замена OpenClaw cron, skill loading или messaging adapters.
- Публикация приватных task roots, corpora, generated reports, chat identifiers,
  webhooks, owner-specific configuration или локальных workspace paths.
