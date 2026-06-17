# Research Mode Roadmap

[English](#english) | [Русский](#русский)

## English

Research Mode is an OpenClaw-first skill for durable, review-gated background
research. It is not a standalone Python package yet. The roadmap below describes
the public direction of the GitHub repository and avoids private workspace,
operator, or task-specific context.

### Now

- Improve repository onboarding for external contributors: clearer first-read
  documentation, issue templates, and contribution guidance.
- Document public contracts: stable operator CLI surface, important JSON state
  and worker-result shapes, and compatibility expectations for older task state.
- Clean up security-audit follow-ups: avoid leaking unnecessary absolute host
  paths in public/package-facing summaries while keeping local diagnostics useful.
- Add a read-only `health` / `reconcile` diagnostic surface for state, artifacts,
  runtime, delivery, and recovery status.
- Improve partial-failure recovery so operators can distinguish `resume ok`,
  `repair needed`, `manual review needed`, and `fresh continuation recommended`.

### Next

- Make task-local package installation more governed without making ordinary
  research tasks painful: audit trails, optional strict policy, and reproducible
  package snapshots where useful.
- Add a refine/pivot ladder for repeated low-yield iterations so long-running
  tasks change strategy instead of repeating weak searches.
- Persist reusable research lessons across similar tasks when that can be done
  transparently and safely.
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

### Сейчас

- Улучшить вход в репозиторий для внешних участников: яснее первый экран
  документации, issue templates и правила участия.
- Описать публичные контракты: стабильную операторскую CLI-поверхность, важные
  JSON-форматы состояния и worker-result, а также ожидания совместимости для
  старых task state.
- Закрыть follow-up по security audit: не раскрывать лишние абсолютные пути
  машины в public/package-facing summaries, но сохранить полезную локальную
  диагностику.
- Добавить read-only `health` / `reconcile` диагностику для состояния,
  артефактов, runtime, delivery и recovery.
- Улучшить восстановление после частичных сбоев, чтобы оператор различал
  `resume ok`, `repair needed`, `manual review needed` и
  `fresh continuation recommended`.

### Дальше

- Сделать установку task-local packages управляемее без лишней бюрократии для
  обычных исследований: audit trail, optional strict policy и воспроизводимые
  package snapshots там, где это полезно.
- Добавить refine/pivot ladder для серий слабых итераций, чтобы долгие задачи
  меняли стратегию, а не повторяли неудачный поиск.
- Переиспользовать уроки между похожими исследованиями, если это можно сделать
  прозрачно и безопасно.
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
