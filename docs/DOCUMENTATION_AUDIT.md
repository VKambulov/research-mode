# Research Mode Documentation Audit

[English](#english) | [Русский](#русский)

## English

This audit records the documentation redesign that made the repository easier
to read before deeper documentation polish.

### Findings

- `README.md` had grown into a mixed first page, user guide, operator guide,
  command reference, architecture summary, and release checklist.
- The Russian README path contained too many English operational words where
  normal Russian wording was clearer.
- Advanced details such as worker leases, queue findings, recovery files,
  output contracts, and delivery internals appeared too early for new readers.
- `ARCHITECTURE.md`, `TROUBLESHOOTING.md`, `docs/CLI.md`, and
  `docs/STATE_VERSIONING.md` were still useful and should not be removed just to
  make the root look smaller.
- After `v0.5.0`, the current model is structured outputs:
  `output_contract.outputs[]` and `delivery.outputs[]`. Legacy single-output
  fields should be described as compatibility, not as the preferred model.

### Decisions

- Keep `README.md` as the short first-entry document.
- Add `docs/USER_GUIDE.md` for practical user examples.
- Add `docs/OPERATIONS.md` for operator commands, review, recovery, and release
  gates.
- Add `docs/OUTPUTS.md` for structured output artifacts and legacy fields.
- Keep root `ARCHITECTURE.md` and `TROUBLESHOOTING.md` to avoid breaking public
  links; link to them from the README.
- Update docs smoke checks so the simpler structure is protected.

### Follow-Up Polish

- A later PR can move or mirror `ARCHITECTURE.md` and `TROUBLESHOOTING.md` into
  `docs/` if public links are handled carefully.
- The advanced Russian docs still deserve a dedicated language pass. This PR
  fixes the first reader path and creates room for that pass.

## Русский

Этот аудит фиксирует перестройку документации, которая делает репозиторий
проще для первого чтения до более глубокой редакторской чистки.

### Наблюдения

- `README.md` разросся в смесь первой страницы, руководства пользователя,
  операторского руководства, справочника команд, архитектурной сводки и
  релизного чеклиста.
- Русский путь в README содержал слишком много английских рабочих слов там, где
  нормальная русская формулировка понятнее.
- Сложные детали про рабочие блокировки, очередь, файлы восстановления,
  контракты результатов и внутренности доставки появлялись слишком рано для
  нового читателя.
- `ARCHITECTURE.md`, `TROUBLESHOOTING.md`, `docs/CLI.md` и
  `docs/STATE_VERSIONING.md` остаются полезными, поэтому их не стоит удалять
  только ради более короткого корня репозитория.
- После `v0.5.0` текущая модель — структурированные результаты:
  `output_contract.outputs[]` и `delivery.outputs[]`. Старые single-output поля
  нужно описывать как совместимость, а не как предпочтительный путь.

### Решения

- Оставить `README.md` короткой входной страницей.
- Добавить `docs/USER_GUIDE.md` с практическими пользовательскими примерами.
- Добавить `docs/OPERATIONS.md` для операторских команд, ревью, восстановления
  и проверок релиза.
- Добавить `docs/OUTPUTS.md` для структурированных результатов и старых полей.
- Оставить корневые `ARCHITECTURE.md` и `TROUBLESHOOTING.md`, чтобы не ломать
  публичные ссылки; дать на них ясные ссылки из README.
- Обновить smoke-проверку документации, чтобы новая структура не расползлась.

### Следующая редакторская чистка

- В отдельном PR можно перенести или продублировать `ARCHITECTURE.md` и
  `TROUBLESHOOTING.md` в `docs/`, если аккуратно обработать публичные ссылки.
- Продвинутые русские документы всё ещё заслуживают отдельного языкового
  прохода. Этот PR чинит первый путь читателя и освобождает место для такой
  чистки.
