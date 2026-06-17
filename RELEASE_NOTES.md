# Research Mode Release Notes

[English](#english) | [Русский](#русский)

License: Apache License, Version 2.0.

## English

### Unreleased

- Added public `ROADMAP.md` and `CONTRIBUTING.md` so GitHub readers can see
  project direction, development checks, public contracts, and privacy rules
  without private workspace notes.
- Added GitHub issue templates for bug reports, feature requests, and security
  hardening proposals.
- Documented the current lightweight security baseline: release gate plus
  Bandit smoke scan, with CodeQL not enabled by default.
- Added public CLI, state-versioning, and JSON schema contract docs for task
  state, worker results, adequacy, finalization, and delivery intents.
- Clarified the `prepare-runtime --package` threat model as a controlled
  task-local capability, not an accidental code-execution surface.
- Added read-only `health` diagnostics, plus `reconcile` as a read-only alias,
  with JSON/text output for state/artifact consistency warnings and safe
  operator next actions.
- Tightened pending-result recovery guidance: `health` reports explicit repair
  only for valid stale pending worker results, flags invalid pending payloads
  for manual review, and blocks `resume` when a paused task has unresolved
  pending-result inconsistency.
- Added `recovery-log.jsonl` as an inspectable task-local recovery log for
  applied or rejected pending worker results.

### v0.2.3 - 2026-06-16

- Documented ClawHub installation and the ClawHub text-only package boundary:
  binary files such as the social preview PNG and the RAG evaluation XLSX
  workbook are available from GitHub, but not from `clawhub install`.
- Clarified the distribution-license boundary: the GitHub source repository is
  Apache-2.0, while ClawHub registry skill packages use the ClawHub platform
  skill license.
- Made the documentation smoke check compatible with text-only ClawHub installs
  where binary presentation/example assets are absent.

### v0.2.2 - 2026-06-16

- Added public examples under `examples/`, including a safe web-to-Markdown
  capture package and a RAG evaluation tooling decision-matrix package with an
  XLSX workbook.
- Added sanitized `research-trace/` directories for the examples so reviewers
  can inspect task state, runs, iterations, source/finding logs, result
  payloads, playbooks, and selected analysis artifacts without exposing local
  system paths or chat identifiers.
- Clarified finalization guidance for multi-file deliverables: workers should
  expose one `package` / `final_package` candidate directory instead of listing
  each package file as a separate final candidate artifact.
- Added docs smoke coverage for `examples/README.md` and the examples link in
  the main README.
- Improved the GitHub-facing repository presentation with README badges, an
  at-a-glance overview, a lifecycle diagram, stronger examples showcase text,
  a generated PNG social preview, and a static Apache-2.0 license badge.

### v0.2.1

Patch release for delivery-state consistency.

- `record-notification --status sent` now clears stale
  `delivery.notification_blocked` and intent `blocked_reason` markers when an
  operator or adapter successfully sends an intent that was previously blocked.
- Added regression coverage for the `blocked -> sent` transition.

### v0.2.0

`research-mode` v0.2.0 is a reliability release for long-running research
tasks, especially tasks that run under cron, recover from interrupted worker
turns, and produce review-ready file deliverables.

### Highlights

- Added a research adequacy gate before finalization, so tasks verify whether
  accumulated evidence actually answers the goal before producing a final
  deliverable.
- Added a root-local fair worker queue for cron iterations, including stale
  holder/waiter cleanup and compatibility defaults for older `state.json`
  files.
- Added pending result recovery for worker turns that wrote a result file but
  did not reach `finish`.
- Added review-ready package deliverables with explicit entrypoints,
  attachments, manifest handling, and task-directory containment checks.
- Added delivery intents as the public handoff contract for platform-specific
  notification adapters.
- Added `record-notification` so delivery counters are updated only after a
  notification is confirmed as sent.
- Added owner binding fields for chat-launched tasks, including optional
  `thread_id` / `topic_id` and explicit `--no-owner`.
- Added stricter XLSX compatibility validation, including detection of
  worksheet `autoFilter` and Excel Table conflicts on the same range.
- Hardened URL capture, approval/delivery file handling, task path handling,
  and runtime prompts as part of the same reliability line.
- Updated GitHub Actions to current action versions and removed ineffective
  cache configuration without a lockfile.

### Migration notes

- Existing task state is normalized lazily when read; older tasks should not
  require manual migration.
- Platform-specific notification sending is still intentionally outside the
  public skill package. The public contract is `delivery_intent` plus
  `record-notification`.
- `awaiting_review` still means "ready for human review", not "already
  delivered".

### Required release checks

Run from the repository or package root:

```bash
scripts/check_research_mode.sh
uvx --from bandit bandit -q -r scripts -x scripts/selftest
detect-secrets scan --all-files --exclude-files '(^|/)\.(pytest|ruff)_cache/'
```

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

### Unreleased

- Добавлены публичные `ROADMAP.md` и `CONTRIBUTING.md`: теперь GitHub-читатель
  видит направление проекта, проверки разработки, публичные контракты и правила
  приватности без приватных workspace-заметок.
- Добавлены GitHub issue templates для bug reports, feature requests и security
  hardening proposals.
- Документирован текущий лёгкий security baseline: release gate плюс Bandit
  smoke scan; CodeQL по умолчанию не включён.
- Добавлены публичные docs для CLI, state versioning и JSON schema contracts:
  task state, worker results, adequacy, finalization и delivery intents.
- Уточнён threat model для `prepare-runtime --package`: это controlled
  task-local capability, а не случайная поверхность выполнения кода.
- Добавлена read-only диагностика `health` и read-only alias `reconcile` с
  JSON/text output для state/artifact consistency warnings и безопасных
  следующих шагов оператора.
- Уточнён recovery flow для pending result: `health` предлагает repair только
  для валидных stale pending worker results, invalid pending payloads отправляет
  на manual review, а `resume` блокируется, если paused-задача имеет
  нерешённое pending-result расхождение.
- Добавлен `recovery-log.jsonl`: task-local recovery log для применённых или
  отклонённых pending worker results.

### v0.2.3 - 2026-06-16

- Документирована установка через ClawHub и text-only граница ClawHub package:
  бинарные файлы вроде social preview PNG и RAG evaluation XLSX workbook
  доступны из GitHub, но не из `clawhub install`.
- Уточнена граница лицензирования дистрибуции: GitHub source repository
  распространяется под Apache-2.0, а ClawHub registry skill packages используют
  платформенную лицензию ClawHub для skills.
- Docs smoke теперь совместим с text-only ClawHub installs, где бинарные
  презентационные/example assets отсутствуют.

### v0.2.2 - 2026-06-16

- Добавлены публичные примеры в `examples/`: package для безопасного
  web-to-Markdown capture и package с decision matrix по RAG evaluation tooling,
  включая XLSX workbook.
- Для примеров добавлены очищенные `research-trace/` директории: можно посмотреть
  состояние задачи, runs, итерации, журналы sources/findings, result payloads,
  playbook и выбранные analysis artifacts без раскрытия локальных системных
  путей или идентификаторов чатов.
- Уточнена guidance для финализации multi-file deliverables: worker должен
  отдавать одну директорию-кандидат `package` / `final_package`, а не перечислять
  каждый файл пакета отдельным final candidate artifact.
- Добавлено docs smoke покрытие для `examples/README.md` и ссылки на examples в
  основном README.
- Улучшена GitHub-витрина репозитория: badges в README, короткое описание,
  lifecycle-диаграмма, более сильное описание examples, сгенерированный PNG
  social preview и статический badge лицензии Apache-2.0.

### v0.2.1

Patch-релиз для согласованности delivery-state.

- `record-notification --status sent` теперь очищает устаревшие маркеры
  `delivery.notification_blocked` и `blocked_reason` у intent, если оператор
  или адаптер успешно отправил intent, который раньше был заблокирован.
- Добавлен regression test для перехода `blocked -> sent`.

### v0.2.0

`research-mode` v0.2.0 — релиз надёжности для длительных исследований,
особенно для задач, которые идут через cron, восстанавливаются после
прерванных рабочих итераций и готовят файлы для проверки человеком.

### Главное

- Добавлена проверка достаточности исследования перед финализацией: задача
  сначала проверяет, отвечает ли накопленная доказательная база цели.
- Добавлена честная очередь рабочих итераций на уровне корня исследований,
  включая очистку устаревших holder/waiter записей и совместимость со старыми
  `state.json`.
- Добавлено восстановление pending result для случаев, когда рабочая итерация
  успела записать result-файл, но не дошла до `finish`.
- Добавлены review-ready package deliverables: явный entrypoint, attachments,
  manifest и проверки, что файлы не выходят за пределы директории задачи.
- Добавлен `delivery_intent` как публичный контракт передачи уведомлений в
  platform-specific адаптеры.
- Добавлена команда `record-notification`: счётчики доставки обновляются
  только после подтверждённой отправки уведомления.
- Добавлена привязка owner для задач, запущенных из чата, включая опциональные
  `thread_id` / `topic_id` и явный `--no-owner`.
- Добавлена более строгая XLSX-проверка совместимости, включая конфликт
  worksheet `autoFilter` и Excel Table на одном диапазоне.
- Усилены URL capture, обработка approval/delivery файлов, проверка путей задач
  и runtime prompts в рамках той же линии надёжности.
- GitHub Actions обновлены на актуальные версии actions; удалён неэффективный
  cache без lockfile.

### Заметки по миграции

- Старое состояние задач нормализуется лениво при чтении; ручная миграция
  старых задач не должна требоваться.
- Отправка уведомлений через конкретную платформу по-прежнему намеренно
  находится вне публичного пакета skill. Публичный контракт — `delivery_intent`
  плюс `record-notification`.
- `awaiting_review` по-прежнему означает "готово к проверке человеком", а не
  "уже доставлено".

### Обязательные проверки релиза

Из корня репозитория:

```bash
scripts/check_research_mode.sh
uvx --from bandit bandit -q -r scripts -x scripts/selftest
detect-secrets scan --all-files --exclude-files '(^|/)\.(pytest|ruff)_cache/'
```

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
