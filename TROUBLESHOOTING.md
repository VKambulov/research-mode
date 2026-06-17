# Research Mode Troubleshooting

[English](#english) | [Русский](#русский)

This guide describes practical diagnosis and safe repair paths. It assumes that
normal operation goes through helper commands, not manual edits to `state.json`.

## English

### Diagnosis Order

Use the highest-level surfaces first:

```bash
python3 scripts/research_mode.py health --id <research-id> --format text
python3 scripts/research_mode.py reconcile --id <research-id> --format text
python3 scripts/research_mode.py summary --id <research-id> --format text
python3 scripts/research_mode.py status --id <research-id> --format text
```

`health` is read-only. Its JSON output has stable top-level `status`,
`findings`, and `recommended_actions` fields for operator automation. Use it
before repair or resume when task state and artifacts may disagree.
`reconcile` is the same read-only diagnostic surface. `repair_needed` means a
valid stale pending worker result can be applied explicitly; `blocked` means
the operator should wait or gather more context before changing state.

Then inspect task-local surfaces:

- `task-playbook.md`;
- `runs.tsv`;
- `recovery-log.jsonl`;
- `state.json`;
- `final-report.md`;
- `workspace/` artifacts only when the operator needs deeper evidence.

The usual order is:

1. Run `health` for read-only diagnosis and recommended actions.
2. Check semantic state: status, review, delivery, finalization.
3. Check physical artifacts: declared files actually exist and are readable.
4. Check execution trail: `runs.tsv`, latest run id, active lock, finish
   transaction.
5. Choose the narrowest helper command that matches the state.

Manual file surgery is a last resort. If it is unavoidable, make a rollback
checkpoint first and verify `summary` and `status` after the repair.

### Task Does Not Progress

Likely causes:

- task is `paused`;
- task is `awaiting_review`;
- cron job was removed or disabled;
- active lock is still held;
- failure threshold was reached;
- no worker is scheduled.

Checks:

```bash
python3 scripts/research_mode.py health --id <research-id> --format text
python3 scripts/research_mode.py reconcile --id <research-id> --format text
python3 scripts/research_mode.py summary --id <research-id> --format text
python3 scripts/research_mode.py status --id <research-id> --format text
```

Safe actions:

- `resume` only for `paused`;
- `request-changes`, `reopen`, `approve`, or `stop` for `awaiting_review`;
- `schedule` when the task is `idle` and has no job;
- operator inspection before any action when a lock is active.

### Task Is In `awaiting_review`

This is not a failure. It means a candidate result needs a review decision.

Safe actions:

```bash
python3 scripts/research_mode.py approve --id <research-id>
python3 scripts/research_mode.py request-changes --id <research-id> "what must change"
python3 scripts/research_mode.py reopen --id <research-id> --feedback "why more work is needed"
python3 scripts/research_mode.py stop --id <research-id>
```

Do not use `resume` as a substitute for review. `resume` is for `paused` tasks.

### Task Is Stuck In `running`

Likely causes:

- worker crashed before `finish` or `fail`;
- result file was not written;
- stale lock recovery has not happened yet;
- an operator is inspecting an active run.

Checks:

- `lock.run_id`;
- lock age and stale timeout;
- `transactions.finish.status`;
- `.tmp/result-<run-id>.json`;
- latest row in `runs.tsv`;
- latest row in `recovery-log.jsonl`;
- any recovery note under `workspace/`.

Safe actions:

- wait if the lease is fresh and a worker is still active;
- if `.tmp/result-<run-id>.json` exists and the lock is stale, run
  `python3 scripts/research_mode.py recover --id <research-id> --apply-pending-result`;
- if `health` reports `missing_task_playbook`, run
  `python3 scripts/research_mode.py recover --id <research-id> --refresh-derived`;
- if `health` reports `invalid_pending_result`, keep the pending file for bug
  context and inspect manually before running recovery;
- use `fail` if the leased run is known to be broken and the run id is known;
- avoid starting another worker blindly over an active lock;
- if the state is inconsistent, inspect `task-playbook.md` before manual repair.

### Task Is Waiting In The Global Queue

Likely causes:

- another research task under the same root currently holds the global worker;
- a previous worker turn left stale queue state;
- an older waiter is ahead of this task.

Checks:

- `python3 scripts/research_mode.py queue-status --root <root>`;
- task `status --format json` and `summary --format text`;
- `queue.status`, `queue.position`, and `queue.blocked_by_task_id`.

Safe actions:

- wait for the active task to finish if the holder is fresh;
- treat `deferred:global-research-lock` as normal waiting, not a failed cron tick;
- inspect stale queue state before manual repair.

### Completion Was Rejected

Likely causes:

- research adequacy did not pass, so the task was routed to `phase=verify` or
  back to `search`, `analyze`, or `synthesize`;
- `result.finalization.status` is missing or not `passed`;
- validation evidence is empty;
- blocking defects remain;
- candidate artifact is missing, outside the task directory, unreadable, or too
  raw for delivery;
- generated report has weak Markdown structure;
- declared `.xlsx` candidate is not a readable workbook.

Checks:

```bash
python3 scripts/research_mode.py summary --id <research-id> --format json
python3 scripts/research_mode.py draft-report --id <research-id> --format markdown
```

Safe actions:

- inspect `summary --format json` or `task-playbook.md` for
  `adequacy.operator_next_action`, `coverage_gaps`, and `blocking_reasons`;
- let the next worker turn handle `needs_research`, `needs_analysis`, or
  `needs_synthesis`;
- request user input only when adequacy reports `needs_user_input` or the
  operator can see that a required constraint is impossible to satisfy;
- let the next worker turn repair `worker_rework`;
- use `request-changes` if the task reached review but the human review found
  defects;
- inspect candidate artifacts before approving;
- do not approve a missing or raw workspace artifact.

### `missing_reviewable_artifact`

Meaning:

- task claims to be reviewable, but the final report or primary file is missing
  or not readable.

Checks:

- `artifacts.final_report_path`;
- `delivery.primary_file`;
- physical file existence;
- `finalization.last_validation_findings`.

Safe action:

- do not approve;
- request changes or reopen the task so a valid candidate can be produced;
- restore the artifact only if there is a known safe source of truth.

### `delivery_ready_but_missing_primary`

Meaning:

- `delivery.ready=true`, but `delivery.primary_file` is missing or invalid.

Safe action:

```bash
python3 scripts/research_mode.py mark-delivered \
  --id <research-id> \
  --primary-file final-report.md \
  --summary-text "Final report is ready." \
  --channel-strategy attach \
  --ready
```

Only run this after confirming that `final-report.md` exists inside the task
directory and is the intended deliverable.

### Command Fails Because Task Id Is Ambiguous

Meaning:

- more than one active non-final task exists and the helper cannot infer the
  target.

Safe action:

```bash
python3 scripts/research_mode.py list --format text
python3 scripts/research_mode.py summary --id <research-id> --format text
```

Then repeat the original command with explicit `--id` or `--path`.

### Path Or Artifact Is Rejected

Likely causes:

- id contains a path separator or traversal;
- `--path` points outside `--root`;
- `--primary-file`, `--attachment`, or `--approved-artifact` escapes the task
  directory;
- a symlink resolves outside the allowed task directory.

Safe action:

- keep task ids as simple path segments;
- copy required files into the task directory before using them as delivery or
  approval artifacts;
- avoid symlink-based delivery paths.

### Attach Command Fails

Checks:

- source file exists;
- directory or glob matches the expected files;
- PDF path is local and readable;
- URL uses `http://` or `https://`, is not a local/private network host, does
  not redirect to one, and is reachable within the timeout;
- attached material does not include secrets that should not enter the task
  corpus.

Safe actions:

```bash
python3 scripts/research_mode.py attach-input --id <research-id> --file ./file.md
python3 scripts/research_mode.py attach-note --id <research-id> --title "Manual note" --text "..."
python3 scripts/research_mode.py attach-url-as-md --id <research-id> --url "https://example.com" --timeout-seconds 30
```

If URL capture fails, attach a manually saved note or local snapshot instead of
pretending the source was captured.

### Runtime Or Package Install Fails

Likely causes:

- Python executable is unavailable;
- virtual environment creation failed;
- package installation failed;
- package source is risky or unavailable;
- network is unavailable.

Safe actions:

```bash
python3 scripts/research_mode.py prepare-runtime --id <research-id>
python3 scripts/research_mode.py prepare-runtime --id <research-id> --recreate
```

For packages, check whether the package is necessary and trustworthy before
retrying. Record packages that materially affect the result in the worker
payload.

### Schedule Or Cron Binding Fails

Checks:

- task state is not terminal;
- OpenClaw cron is available in the installation;
- existing job id, if any, still exists;
- `--every` value is valid;
- `--dry-run` was not used by accident.

Safe actions:

```bash
python3 scripts/research_mode.py schedule --id <research-id> --every 5m
python3 scripts/research_mode.py unschedule --id <research-id>
```

For `awaiting_review`, use review commands rather than scheduling more normal
worker turns.

### Installation Fails Because Of Symlink Policy

Some OpenClaw installations reject skills that are symlinks escaping the
configured skills root.

Safe action:

```bash
export OPENCLAW_SKILLS_DIR="/path/to/your/openclaw/skills"
git clone https://github.com/<owner>/research-mode.git "$OPENCLAW_SKILLS_DIR/research-mode"
openclaw skills check
```

Keep the repository physically inside the skills directory when symlink escape
is blocked.

### Documentation Smoke Fails

Run:

```bash
python3 scripts/check_research_mode_docs.py
```

Common causes:

- required public documentation file is missing;
- README no longer links to required guides;
- documented command or option does not match `argparse`;
- human docs regained forbidden CLI-first quickstart wording;
- project docs contain stale internal or agent-only phrasing.

Fix the documentation contract, then run the full gate.

### Full Gate Fails

Run:

```bash
scripts/check_research_mode.sh
```

The gate includes compile checks, `ruff`, docs smoke, release smoke, `pyright`,
selftest, and pytest-compatible tests. Use the first failing stage as the repair
target. Do not treat a later passing stage as proof that an earlier failing
stage is safe to ignore.

## Русский

### Порядок диагностики

Сначала используются самые высокоуровневые представления:

```bash
python3 scripts/research_mode.py health --id <research-id> --format text
python3 scripts/research_mode.py reconcile --id <research-id> --format text
python3 scripts/research_mode.py summary --id <research-id> --format text
python3 scripts/research_mode.py status --id <research-id> --format text
```

`health` ничего не исправляет. В JSON-выводе есть стабильные верхние поля
`status`, `findings` и `recommended_actions`, которые можно использовать для
операторской автоматизации. Запускайте её перед repair или resume, если state и
artifacts могли разойтись.
`reconcile` — такой же read-only диагностический интерфейс. `repair_needed`
означает, что валидный stale pending worker result можно применить явно;
`blocked` означает, что оператору нужно подождать или собрать больше контекста
до изменения state.

Затем проверяются файлы внутри задачи:

- `task-playbook.md`;
- `runs.tsv`;
- `recovery-log.jsonl`;
- `state.json`;
- `final-report.md`;
- артефакты `workspace/` только тогда, когда оператору нужны более глубокие
  доказательства.

Обычный порядок:

1. Запустить `health` для read-only диагностики и recommended actions.
2. Проверить смысловое состояние: статус, ревью, доставку, финальную проверку.
3. Проверить физические артефакты: объявленные файлы существуют и читаются.
4. Проверить след выполнения: `runs.tsv`, последний run id, активную блокировку,
   транзакцию `finish`.
5. Выбрать самую узкую helper-команду, соответствующую состоянию.

Ручное редактирование файлов — крайний вариант. Если оно неизбежно, сначала
нужен rollback checkpoint, а после ремонта — повторная проверка `summary` и
`status`.

### Задача не продвигается

Вероятные причины:

- задача в `paused`;
- задача в `awaiting_review`;
- cron job удалён или отключён;
- активная блокировка всё ещё удерживается;
- достигнут порог ошибок;
- рабочие итерации не запланированы.

Проверки:

```bash
python3 scripts/research_mode.py health --id <research-id> --format text
python3 scripts/research_mode.py reconcile --id <research-id> --format text
python3 scripts/research_mode.py summary --id <research-id> --format text
python3 scripts/research_mode.py status --id <research-id> --format text
```

Безопасные действия:

- `resume` только для `paused`;
- `request-changes`, `reopen`, `approve` или `stop` для `awaiting_review`;
- `schedule`, если задача в `idle` и без job;
- операторская проверка перед любым действием, если активна блокировка.

### Задача в `awaiting_review`

Это не ошибка. Это значит, что кандидат на результат ждёт решения по ревью.

Безопасные действия:

```bash
python3 scripts/research_mode.py approve --id <research-id>
python3 scripts/research_mode.py request-changes --id <research-id> "что нужно изменить"
python3 scripts/research_mode.py reopen --id <research-id> --feedback "почему нужна дополнительная работа"
python3 scripts/research_mode.py stop --id <research-id>
```

`resume` не заменяет ревью. `resume` предназначен для задач в `paused`.

### Задача застряла в `running`

Вероятные причины:

- worker упал до `finish` или `fail`;
- JSON-результат не был записан;
- stale lock recovery ещё не сработал;
- оператор проверяет активный запуск.

Проверки:

- `lock.run_id`;
- возраст блокировки и stale timeout;
- `transactions.finish.status`;
- последняя строка в `runs.tsv`;
- последняя строка в `recovery-log.jsonl`;
- recovery note внутри `workspace/`.

Безопасные действия:

- подождать, если lease свежий и worker ещё работает;
- если `.tmp/result-<run-id>.json` существует и блокировка stale, запустить
  `python3 scripts/research_mode.py recover --id <research-id> --apply-pending-result`;
- если `health` сообщает `missing_task_playbook`, запустить
  `python3 scripts/research_mode.py recover --id <research-id> --refresh-derived`;
- если `health` сообщает `invalid_pending_result`, сохранить pending-файл как
  контекст для bug report и проверить вручную до recovery;
- использовать `fail`, если известно, что запуск сломан, и известен run id;
- не запускать ещё один worker вслепую поверх активной блокировки;
- при противоречивом состоянии сначала читать `task-playbook.md`.

### Задача ждёт global queue

Вероятные причины:

- другая research-задача в том же root сейчас держит global worker;
- предыдущая итерация оставила stale queue state;
- более старый waiter стоит впереди этой задачи.

Проверки:

- `python3 scripts/research_mode.py queue-status --root <root>`;
- `status --format json` и `summary --format text` для задачи;
- `queue.status`, `queue.position` и `queue.blocked_by_task_id`.

Безопасные действия:

- подождать завершения активной задачи, если holder свежий;
- считать `deferred:global-research-lock` штатным ожиданием, а не ошибкой cron tick;
- перед ручным исправлением проверить stale queue state.

### Завершение отклонено

Вероятные причины:

- проверка достаточности исследования не пройдена, поэтому задача перешла в
  `phase=verify` или вернулась в `search`, `analyze` либо `synthesize`;
- отсутствует `result.finalization.status` или он не равен `passed`;
- нет доказательств проверки;
- остались блокирующие дефекты;
- кандидатный артефакт отсутствует, лежит вне задачи, не читается или слишком
  сырой для выдачи;
- сгенерированный отчёт имеет слабую Markdown-структуру;
- заявленный `.xlsx` не открывается как workbook.

Проверки:

```bash
python3 scripts/research_mode.py summary --id <research-id> --format json
python3 scripts/research_mode.py draft-report --id <research-id> --format markdown
```

Безопасные действия:

- проверить в `summary --format json` или `task-playbook.md` поля
  `adequacy.operator_next_action`, `coverage_gaps` и `blocking_reasons`;
- дать следующей рабочей итерации обработать `needs_research`,
  `needs_analysis` или `needs_synthesis`;
- запрашивать ввод пользователя только при `needs_user_input` или когда
  оператор видит, что обязательное ограничение невозможно выполнить;
- позволить следующей итерации исправить `worker_rework`;
- использовать `request-changes`, если задача дошла до ревью, но проверка
  человеком нашла дефекты;
- проверять кандидатные артефакты перед утверждением;
- не утверждать отсутствующий или сырой workspace-артефакт.

### `missing_reviewable_artifact`

Значение:

- задача считает себя готовой к ревью, но финальный отчёт или primary file
  отсутствует либо не читается.

Проверки:

- `artifacts.final_report_path`;
- `delivery.primary_file`;
- физическое существование файла;
- `finalization.last_validation_findings`.

Безопасное действие:

- не утверждать задачу;
- запросить доработки или открыть задачу снова, чтобы появился валидный
  кандидат;
- восстанавливать артефакт только при наличии понятного источника истины.

### `delivery_ready_but_missing_primary`

Значение:

- `delivery.ready=true`, но `delivery.primary_file` отсутствует или невалиден.

Безопасное действие:

```bash
python3 scripts/research_mode.py mark-delivered \
  --id <research-id> \
  --primary-file final-report.md \
  --summary-text "Итоговый отчёт готов." \
  --channel-strategy attach \
  --ready
```

Команда допустима только после проверки, что `final-report.md` существует
внутри задачи и действительно является нужным результатом.

### Команда не может выбрать задачу

Значение:

- активных незавершённых задач больше одной, и helper не может вывести цель
  команды автоматически.

Безопасное действие:

```bash
python3 scripts/research_mode.py list --format text
python3 scripts/research_mode.py summary --id <research-id> --format text
```

Затем исходная команда повторяется с явным `--id` или `--path`.

### Путь или артефакт отклонён

Вероятные причины:

- id содержит разделитель пути или traversal;
- `--path` указывает наружу из `--root`;
- `--primary-file`, `--attachment` или `--approved-artifact` выходит из
  директории задачи;
- символическая ссылка ведёт наружу из разрешённой директории.

Безопасное действие:

- использовать простые id без разделителей пути;
- копировать нужные файлы внутрь задачи перед использованием в delivery или
  approval;
- избегать delivery-путей через символические ссылки.

### Не сработало прикрепление материала

Проверки:

- исходный файл существует;
- директория или glob действительно находят ожидаемые файлы;
- PDF локальный и читаемый;
- URL использует `http://` или `https://`, не указывает на локальный или
  приватный сетевой хост, не перенаправляет на него и доступен в пределах
  timeout;
- прикрепляемый материал не содержит секреты, которые не должны попадать в
  корпус задачи.

Безопасные действия:

```bash
python3 scripts/research_mode.py attach-input --id <research-id> --file ./file.md
python3 scripts/research_mode.py attach-note --id <research-id> --title "Manual note" --text "..."
python3 scripts/research_mode.py attach-url-as-md --id <research-id> --url "https://example.com" --timeout-seconds 30
```

Если URL не удалось снять автоматически, лучше прикрепить вручную сохранённую
заметку или локальный snapshot, а не делать вид, что источник был захвачен.

### Сломалось локальное окружение или установка пакета

Вероятные причины:

- Python executable недоступен;
- virtual environment не создался;
- пакет не установился;
- источник пакета рискованный или недоступный;
- сеть недоступна.

Безопасные действия:

```bash
python3 scripts/research_mode.py prepare-runtime --id <research-id>
python3 scripts/research_mode.py prepare-runtime --id <research-id> --recreate
```

Перед повторной установкой пакета нужно проверить, нужен ли он и можно ли ему
доверять. Пакеты, существенно влияющие на результат, фиксируются в payload
рабочей итерации.

### Не сработало расписание или привязка cron

Проверки:

- задача не в terminal-состоянии;
- OpenClaw cron доступен в установке;
- существующий job id, если он указан, всё ещё существует;
- значение `--every` валидно;
- `--dry-run` не был указан случайно.

Безопасные действия:

```bash
python3 scripts/research_mode.py schedule --id <research-id> --every 5m
python3 scripts/research_mode.py unschedule --id <research-id>
```

Для `awaiting_review` используются review-команды, а не планирование новых
обычных рабочих итераций.

### Установка не проходит из-за symlink policy

Некоторые установки OpenClaw отклоняют skills, если символическая ссылка
выходит за пределы настроенной директории skills.

Безопасное действие:

```bash
export OPENCLAW_SKILLS_DIR="/path/to/your/openclaw/skills"
git clone https://github.com/<owner>/research-mode.git "$OPENCLAW_SKILLS_DIR/research-mode"
openclaw skills check
```

Если symlink escape заблокирован, репозиторий должен физически находиться внутри
директории skills.

### Не прошёл docs smoke

Запуск:

```bash
python3 scripts/check_research_mode_docs.py
```

Частые причины:

- отсутствует обязательный публичный doc-файл;
- README больше не ссылается на обязательные руководства;
- описанная команда или опция не совпадает с `argparse`;
- в пользовательские docs вернулась старая CLI-first инструкция быстрого
  старта;
- в публичных docs появились устаревшие внутренние или agent-only формулировки.

После исправления документационного контракта запускается полная проверка.

### Не прошла полная проверка

Запуск:

```bash
scripts/check_research_mode.sh
```

Проверка включает compile checks, `ruff`, docs smoke, release smoke, `pyright`,
selftest и pytest-compatible tests. Исправление начинается с первого упавшего
этапа. Успешный более поздний этап не доказывает, что ранний сбой можно
игнорировать.
