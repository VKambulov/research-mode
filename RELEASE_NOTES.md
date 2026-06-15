# Research Mode Release Notes

[English](#english) | [Русский](#русский)

License: Apache License, Version 2.0.

## English

### v0.1.0

`research-mode` is an **OpenClaw cron-based skill** for durable background
research.

It is meant for OpenClaw users who want durable, review-gated background
research with local task state and inspectable artifacts. It is not yet a
standalone Python package, daemon, hosted service, or general research library.

### Highlights

- Durable task state stored on disk under a selected research root.
- Bounded worker iterations driven by OpenClaw cron.
- `begin` / `finish` lifecycle with lease-aware state updates.
- Pause, resume, stop, reopen, request-changes, approve, and delivery helpers.
- Review-gated finalization with `awaiting_review` separated from delivery.
- Finalization trace contract through `result.finalization`.
- Lightweight candidate artifact inspection for Markdown and XLSX deliverables.
- Operator surfaces: `summary`, `status`, `task-playbook.md`, and `runs.tsv`.
- `operator_next_action` for review candidate, worker rework, operator
  intervention, review-state verification, or continued research.
- RU+EN README and maintainer release procedure.
- Local release gate through `scripts/check_research_mode.sh`.
- Clean lifecycle smoke through `scripts/release_smoke.py`.
- GitHub Actions CI for the release gate and Bandit security smoke scan.

### Known limitations

- Cron execution is OpenClaw-specific; the helper scripts are not a standalone
  scheduler.
- Package governance is intentionally lightweight; task-local packages are
  allowed, but there is no lockfile or allowlist policy yet.
- Artifact inspection is structural and lightweight, not a domain-complete
  quality audit.
- Optional internal notes can exist in a private workspace, but they are not
  required for the public skill package.
- Licensed under Apache License, Version 2.0.

### Required release checks

Run from the repository or package root:

```bash
scripts/check_research_mode.sh
python3 scripts/release_smoke.py
```

Then review:

```bash
git diff --stat
```

Before publishing, confirm `LICENSE` is included in the public package.

## Русский

### v0.1.0

`research-mode` — это **OpenClaw skill**, который запускает длительное фоновое
исследование через cron.

Он предназначен для пользователей OpenClaw, которым нужно длительное фоновое
исследование с локальным состоянием задачи, проверкой результата перед выдачей
и артефактами, которые можно посмотреть. Это пока не самостоятельный
Python-пакет, не демон, не размещённый сервис и не универсальная библиотека для
исследований.

### Главное

- Состояние задачи хранится на диске внутри выбранного корня исследований.
- Ограниченные рабочие итерации запускаются через OpenClaw cron.
- Жизненный цикл `begin` / `finish` обновляет состояние с учётом рабочей блокировки.
- Есть команды `pause`, `resume`, `stop`, `reopen`, `request-changes`, `approve`
  и вспомогательные команды для выдачи результата.
- Финальная проверка отделяет `awaiting_review` от фактической выдачи результата.
- След финальной проверки записывается в `result.finalization`.
- Лёгкая проверка кандидатных артефактов для Markdown и XLSX.
- Поверхности оператора: `summary`, `status`, `task-playbook.md`, `runs.tsv`.
- `operator_next_action` показывает следующий шаг: проверить кандидата,
  отправить на доработку, вмешаться оператору, проверить состояние ревью или
  продолжить исследование.
- README и процедура релиза доступны на русском и английском.
- Локальная проверка релиза запускается через `scripts/check_research_mode.sh`.
- Чистый smoke-тест жизненного цикла запускается через `scripts/release_smoke.py`.
- GitHub Actions CI запускает полную проверку релиза и Bandit security smoke scan.

### Известные ограничения

- Запуск через cron завязан на OpenClaw; вспомогательные скрипты не являются
  самостоятельным планировщиком.
- Политика пакетов пока лёгкая: пакеты, локальные для задачи, разрешены, но
  lockfile или allowlist ещё нет.
- Проверка артефактов структурная и лёгкая, это не полноценный доменный аудит
  качества.
- Внутренние заметки могут существовать в приватной рабочей области, но они не
  требуются для публичного пакета skill.
- Лицензия: Apache License, Version 2.0.

### Обязательные проверки релиза

Из корня репозитория:

```bash
scripts/check_research_mode.sh
python3 scripts/release_smoke.py
```

Затем проверить:

```bash
git diff --stat
```

Перед публикацией нужно проверить, что `LICENSE` входит в публичный пакет.
