# Research Mode Operations

[English](#english) | [Русский](#русский)

## English

This document is for operators and maintainers who run, inspect, recover, or
release Research Mode tasks. The user-facing entrypoint remains chat-first; the
commands below are the stable operator surface behind that workflow.

### Roles

- **User**: asks for research and reviews the final candidate.
- **Agent**: creates tasks, schedules work, records results, and reports
  milestones.
- **Worker**: performs one bounded iteration after `begin`.
- **Operator**: inspects state, repairs problems, and manages review/delivery.
- **Maintainer**: changes code, docs, tests, and release packaging.

### Normal Task Flow

1. `create` or `start` creates the task directory and `state.json`.
2. Default preflight runs first unless explicitly skipped.
3. `schedule` binds a task to OpenClaw cron.
4. Each worker turn uses `begin` and then `finish` or `fail`.
5. Adequacy and finalization checks decide whether the task can enter review.
6. `request-changes` reopens the review loop.
7. `approve` marks the reviewed output as accepted.
8. Delivery adapters use delivery intents or structured delivery fields.

### Common Commands

Create and schedule in one step:

```bash
python3 scripts/research_mode.py start \
  --id <research-id> \
  --goal "Compare..." \
  --depth L \
  --every 30m
```

Inspect:

```bash
python3 scripts/research_mode.py summary --id <research-id> --format text
python3 scripts/research_mode.py health --id <research-id> --format text
python3 scripts/research_mode.py status --id <research-id>
python3 scripts/research_mode.py queue-status --format text
```

Review:

```bash
python3 scripts/research_mode.py request-changes --id <research-id> "what to change"
python3 scripts/research_mode.py approve --id <research-id>
```

Recovery:

```bash
python3 scripts/research_mode.py recover --id <research-id> --refresh-derived
python3 scripts/research_mode.py recover --id <research-id> --apply-pending-result
```

### Operator Surfaces

Use these before reading raw JSON:

- `summary`: current status, phase, review state, delivery state, next action.
- `health`: read-only diagnosis and safe recovery recommendation.
- `status`: compact state view.
- `queue-status`: root-level queue holder/waiter findings.
- `task-playbook.md`: task-local operator guide.
- `runs.tsv`: worker turn history.
- `recovery-log.jsonl`: applied or rejected recovery events.

`health` is read-only. `reconcile` is the same read-only diagnostic surface.
Use explicit recovery commands when a repair is needed.

### Review And Delivery Rules

`awaiting_review` means "ready for human review", not "already delivered".

Do not:

- edit final artifacts after review without using `request-changes`;
- use `resume` to bypass review;
- mark a task complete because a draft exists;
- send raw workspace files as the final user-facing result.

Use `approve` only after the candidate output has been inspected. For structured
outputs, verify `delivery.outputs[]`; `primary_file` and `attachments` are
compatibility mirrors.

### Scheduling Notes

- Use `schedule` for repeated worker turns.
- Use `unschedule` when a task should stop receiving cron ticks.
- If a worker times out, inspect `health` before starting a replacement run.
- If timeout settings change, remember that old leases may still carry the
  timeout that was active when `begin` ran.

### Quality Gates

Before pushing or releasing:

```bash
python3 scripts/check_research_mode_docs.py
./scripts/check_research_mode.sh
git diff --check
uvx --from bandit bandit -q -r scripts -x scripts/selftest
detect-secrets scan --all-files --exclude-files '(^|/)\.(pytest|ruff)_cache/'
```

The full gate runs ruff, documentation smoke checks, release smoke, pyright,
selftest, and pytest.

### Public Safety

Public examples and reports must not contain:

- private workspace paths;
- chat, thread, topic, cron, or webhook ids;
- tokens or API keys;
- private task roots;
- personal memory or Obsidian notes;
- non-redistributable input material.

## Русский

Этот документ предназначен для операторов и сопровождающих: тех, кто запускает,
проверяет, чинит или выпускает Research Mode. Пользовательский вход остаётся
чатовым; команды ниже — стабильный операторский слой за этим сценарием.

### Роли

- **Пользователь**: просит исследование и проверяет итоговый кандидат.
- **Агент**: создаёт задачи, ставит работу в расписание, записывает результаты
  и сообщает о важных этапах.
- **Рабочая итерация**: выполняет один ограниченный шаг после `begin`.
- **Оператор**: смотрит состояние, чинит проблемы и управляет ревью/доставкой.
- **Сопровождающий**: меняет код, документацию, тесты и релизный пакет.

### Обычный ход задачи

1. `create` или `start` создаёт директорию задачи и `state.json`.
2. Сначала выполняется предварительная проверка, если её явно не пропустили.
3. `schedule` привязывает задачу к OpenClaw cron.
4. Каждая рабочая итерация использует `begin`, а затем `finish` или `fail`.
5. Проверка достаточности и финальная проверка решают, можно ли идти на ревью.
6. `request-changes` открывает цикл доработки.
7. `approve` отмечает проверенный результат как утверждённый.
8. Адаптеры доставки используют намерения доставки или структурированные поля
   доставки.

### Частые команды

Создать и поставить в расписание:

```bash
python3 scripts/research_mode.py start \
  --id <research-id> \
  --goal "Compare..." \
  --depth L \
  --every 30m
```

Посмотреть состояние:

```bash
python3 scripts/research_mode.py summary --id <research-id> --format text
python3 scripts/research_mode.py health --id <research-id> --format text
python3 scripts/research_mode.py status --id <research-id>
python3 scripts/research_mode.py queue-status --format text
```

Ревью:

```bash
python3 scripts/research_mode.py request-changes --id <research-id> "что изменить"
python3 scripts/research_mode.py approve --id <research-id>
```

Восстановление:

```bash
python3 scripts/research_mode.py recover --id <research-id> --refresh-derived
python3 scripts/research_mode.py recover --id <research-id> --apply-pending-result
```

### Представления оператора

Сначала используйте их, а не сырой JSON:

- `summary`: текущий статус, фаза, ревью, доставка и следующее действие.
- `health`: диагностика только для чтения и безопасная рекомендация.
- `status`: короткое представление состояния.
- `queue-status`: проблемы очереди на уровне корня задач.
- `task-playbook.md`: локальная подсказка оператора для конкретной задачи.
- `runs.tsv`: история рабочих итераций.
- `recovery-log.jsonl`: применённые или отклонённые события восстановления.

`health` ничего не исправляет. `reconcile` — такой же диагностический интерфейс
только для чтения. Если нужен ремонт, используйте явную команду восстановления.

### Правила ревью и доставки

`awaiting_review` означает "готово к проверке человеком", а не "уже
доставлено".

Нельзя:

- править итоговые артефакты после ревью без `request-changes`;
- использовать `resume`, чтобы обойти ревью;
- считать задачу завершённой только потому, что появился черновик;
- отправлять сырые файлы рабочей папки как финальный результат.

Используйте `approve` только после просмотра кандидата. Для структурированных
результатов проверяйте `delivery.outputs[]`; `primary_file` и `attachments`
остаются совместимыми полями для старых интеграций.

### Расписание

- `schedule` запускает повторяющиеся рабочие итерации.
- `unschedule` останавливает cron-запуски для задачи.
- Если рабочая итерация истекла по времени, сначала смотрите `health`.
- Если меняется timeout, старые блокировки могут сохранять timeout, который
  действовал в момент `begin`.

### Проверки качества

Перед push или релизом:

```bash
python3 scripts/check_research_mode_docs.py
./scripts/check_research_mode.sh
git diff --check
uvx --from bandit bandit -q -r scripts -x scripts/selftest
detect-secrets scan --all-files --exclude-files '(^|/)\.(pytest|ruff)_cache/'
```

Полная проверка запускает ruff, проверку документации, релизный smoke-тест,
pyright, selftest и pytest.

### Публичная безопасность

Публичные примеры и отчёты не должны содержать:

- приватные пути рабочей области;
- id чатов, веток, тем, cron-заданий или webhook;
- токены и API-ключи;
- приватные директории задач;
- личную память или Obsidian-заметки;
- материалы, которые нельзя распространять.
