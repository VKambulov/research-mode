# Research Mode CLI Surface

[English](#english) | [Русский](#русский)

## English

The CLI is an operator and maintainer interface for the OpenClaw skill. It is
not the normal user entrypoint. Users usually ask an OpenClaw agent to start or
review a Research Mode task from chat, and the agent uses these commands behind
that workflow.

### Stable Operator Surface

Stable means "documented operator/maintainer contract", not "recommended for
every end user".

- Task lifecycle: `create`, `start`, `schedule`, `begin`, `finish`, `fail`.
- Recovery handoff: `recover`, especially `recover --apply-pending-result`.
- Task inputs: `attach-input`, `attach-note`, `attach-url-as-md`, `attach-pdf`.
- Inspection: `status`, `summary`, `draft-report`, `list`, `queue-status`.
- Steering: `add-angle`, `add-instruction`, `add-constraint`,
  `set-deliverable`, `mutate-working-memory`.
- Control: `pause`, `resume`, `stop`, `unschedule`, `bind-job`.
- Review and delivery: `approve`, `request-changes`, `reopen`,
  `mark-delivered`, `record-notification`, `format-delivery`.
- Runtime preparation: `prepare-runtime`.
- Linked work: `create-linked-research`.

`begin`, `finish`, and `fail` are stable worker lifecycle commands, but they are
not the main onboarding path. They exist so scheduled OpenClaw worker turns and
operators can perform one bounded iteration safely.

### Internal Or More Volatile Surface

- `render-prompt` is mainly a lifecycle/internal debugging surface.
- Recovery and repair behavior may gain more diagnostics before it is treated
  as a broad public contract.
- Machine-readable output can evolve when the matching JSON contract is not
  documented under `schemas/`.

### Contract Rules

- Prefer helper commands over direct edits to `state.json`.
- `--id` is a safe task id under the selected research root.
- `--path` must remain inside the selected research root.
- Raw workspace files are not final deliverables until the review/finalization
  contract marks them as review-ready.
- `awaiting_review` means a human should review a candidate; it does not mean
  the result has been delivered.
- `prepare-runtime --package` is a controlled capability. Package decisions
  should be made by an operator or trusted workflow, not by untrusted retrieved
  content.

## Русский

CLI — это интерфейс оператора и сопровождающего для OpenClaw skill. Это не
обычная пользовательская точка входа. Пользователь обычно просит агента
OpenClaw запустить или проверить Research Mode из чата, а агент уже использует
эти команды за кулисами.

### Стабильная операторская поверхность

`Stable` здесь означает "документированный контракт для оператора или
сопровождающего", а не "команда для каждого обычного пользователя".

- Жизненный цикл задачи: `create`, `start`, `schedule`, `begin`, `finish`,
  `fail`.
- Recovery handoff: `recover`, особенно `recover --apply-pending-result`.
- Входные материалы: `attach-input`, `attach-note`, `attach-url-as-md`,
  `attach-pdf`.
- Просмотр: `status`, `summary`, `draft-report`, `list`, `queue-status`.
- Управление направлением: `add-angle`, `add-instruction`, `add-constraint`,
  `set-deliverable`, `mutate-working-memory`.
- Контроль: `pause`, `resume`, `stop`, `unschedule`, `bind-job`.
- Ревью и доставка: `approve`, `request-changes`, `reopen`, `mark-delivered`,
  `record-notification`, `format-delivery`.
- Подготовка runtime: `prepare-runtime`.
- Связанные задачи: `create-linked-research`.

`begin`, `finish` и `fail` — стабильные команды worker lifecycle, но не основной
путь первого знакомства. Они нужны, чтобы scheduled OpenClaw worker turns и
операторы безопасно выполняли одну ограниченную итерацию.

### Внутренняя или более изменчивая поверхность

- `render-prompt` в основном нужен для lifecycle/internal debugging.
- Recovery и repair-поведение может получить больше диагностики до того, как
  станет широким публичным контрактом.
- Machine-readable output может меняться, если соответствующий JSON-контракт не
  описан в `schemas/`.

### Правила контракта

- Используйте helper-команды вместо ручного редактирования `state.json`.
- `--id` — безопасный task id внутри выбранного research root.
- `--path` должен оставаться внутри выбранного research root.
- Raw workspace files не являются финальными deliverables, пока
  review/finalization contract не пометит их как review-ready.
- `awaiting_review` означает, что кандидат ждёт проверки человеком; это не
  означает, что результат уже доставлен.
- `prepare-runtime --package` — controlled capability. Решение об установке
  packages должен принимать оператор или доверенный workflow, а не недоверенный
  retrieved content.
