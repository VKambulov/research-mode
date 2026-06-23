# Research Mode User Guide

[English](#english) | [Русский](#русский)

## English

This guide explains how to ask an OpenClaw agent to use Research Mode. It is
written for people starting or reviewing research, not for maintainers changing
the code.

### When To Use It

Use Research Mode when the work needs continuity:

- a source-backed comparison;
- a market, product, security, architecture, or policy review;
- a local corpus review over notes, PDFs, screenshots, or datasets;
- a decision memo that should be revised before delivery;
- a follow-up investigation based on an approved result.

Use ordinary chat instead when the answer fits in one turn.

### Basic Request Template

```text
Start a Research Mode task.
Goal: <what should be investigated or decided>.
Deliverable: <what should be produced>.
Depth: S | M | L | XL.
Corpus: web | local | hybrid.
Constraints: <source quality, privacy, exclusions, audience, deadline>.
Updates: <milestones only, blockers only, or final review candidate only>.
```

Example:

```text
Start a Research Mode task.
Goal: compare self-hosted RAG evaluation tools for a small private knowledge base.
Deliverable: recommendation memo with a short matrix and source links.
Depth: L.
Corpus: web.
Constraints: prefer official docs and primary sources; mark weak evidence.
Updates: send blockers and the final review candidate only.
```

### Good Request Fields

- **Goal**: the question, comparison, audit, or decision.
- **Deliverable**: memo, report, table, spreadsheet, package, source list,
  implementation plan, or evidence matrix.
- **Depth**: `S`, `M`, `L`, or `XL`.
- **Corpus**: `web`, `local`, or `hybrid`.
- **Constraints**: source policy, privacy limits, excluded sources, geography,
  language, audience, or deadline.
- **Inputs**: URLs, files, notes, screenshots, PDFs, datasets, or examples.
- **Review expectations**: what should be checked before approval.
- **Update cadence**: when the agent should interrupt you.

### What Happens During The Task

1. The agent creates or starts a task.
2. A preflight check records whether the task can start.
3. Scheduled worker turns collect sources, findings, and notes.
4. Research adequacy checks whether the gathered evidence is enough.
5. Finalization prepares candidate user-facing outputs.
6. The task stops at human review.
7. The reviewer approves the result or requests changes.
8. Approved outputs can be delivered.

### Reviewing A Result

Review the candidate output, not every internal file. Check:

- does it answer the goal?
- are weak claims marked?
- are source links useful?
- is the output shape what you requested?
- are there missing files or obvious formatting problems?

Ask for changes with:

```bash
python3 scripts/research_mode.py request-changes --id <research-id> "what to change"
```

Approve with:

```bash
python3 scripts/research_mode.py approve --id <research-id>
```

### Useful Follow-Up Requests

```text
Continue from the approved Research Mode result.
Goal: turn the recommendation into an implementation plan.
Use the approved sources and keep unresolved risks visible.
```

```text
Open a follow-up Research Mode task.
Goal: verify only the weak evidence from the previous result.
Deliverable: short risk note with source links.
Depth: M.
```

### What Not To Do

- Do not ask the agent to hand-edit `state.json`.
- Do not treat `workspace/` drafts as final output.
- Do not approve a result you have not inspected.
- Do not restart a stuck task before checking `summary` and `health`.
- Do not publish task traces without sanitizing paths, chat ids, tokens, and
  private materials.

## Русский

Это руководство объясняет, как просить OpenClaw-агента использовать Research
Mode. Оно написано для людей, которые запускают или проверяют исследования, а
не для сопровождающих, меняющих код.

### Когда использовать

Research Mode подходит, когда работе нужна непрерывность:

- сравнение с источниками;
- обзор рынка, продукта, безопасности, архитектуры или правил;
- разбор локальных заметок, PDF, скриншотов или таблиц;
- записка для решения, которую нужно проверить перед выдачей;
- продолжение исследования от уже утверждённого результата.

Если ответ помещается в один ход чата, Research Mode не нужен.

### Базовый шаблон запроса

```text
Запусти задачу Research Mode.
Цель: <что нужно изучить или решить>.
Результат: <что нужно получить на выходе>.
Глубина: S | M | L | XL.
Корпус: web | local | hybrid.
Ограничения: <качество источников, приватность, исключения, аудитория, срок>.
Обновления: <только важные этапы, только блокеры или только финальный результат на ревью>.
```

Пример:

```text
Запусти задачу Research Mode.
Цель: сравнить self-hosted инструменты оценки RAG для небольшой частной базы знаний.
Результат: рекомендация с короткой матрицей и ссылками на источники.
Глубина: L.
Корпус: web.
Ограничения: предпочитать официальные документы и первичные источники; отмечать слабые доказательства.
Обновления: присылай только блокеры и финальный результат на ревью.
```

### Полезные поля запроса

- **Цель**: вопрос, сравнение, аудит или решение.
- **Результат**: заметка, отчёт, таблица, файл Excel, пакет файлов, список
  источников, план реализации или матрица доказательств.
- **Глубина**: `S`, `M`, `L` или `XL`.
- **Корпус**: `web`, `local` или `hybrid`.
- **Ограничения**: политика источников, приватность, исключённые источники,
  география, язык, аудитория или срок.
- **Материалы**: ссылки, файлы, заметки, скриншоты, PDF, данные или примеры.
- **Ожидания от ревью**: что нужно проверить перед утверждением.
- **Частота обновлений**: когда агенту стоит вас отвлекать.

### Что происходит внутри задачи

1. Агент создаёт или запускает задачу.
2. Предварительная проверка фиксирует, можно ли начинать.
3. Рабочие итерации по расписанию собирают источники, выводы и заметки.
4. Проверка достаточности решает, хватает ли доказательств.
5. Финализация готовит пользовательские результаты.
6. Задача останавливается на ревью.
7. Ревьюер утверждает результат или просит доработку.
8. Утверждённые файлы можно доставить пользователю.

### Как проверять результат

Проверяйте итоговый кандидат, а не каждый внутренний файл. Важно понять:

- отвечает ли результат на цель;
- отмечены ли слабые утверждения;
- полезны ли ссылки на источники;
- совпадает ли форма результата с запросом;
- нет ли отсутствующих файлов или очевидных проблем оформления.

Попросить доработку:

```bash
python3 scripts/research_mode.py request-changes --id <research-id> "что изменить"
```

Утвердить результат:

```bash
python3 scripts/research_mode.py approve --id <research-id>
```

### Полезные запросы на продолжение

```text
Продолжи от утверждённого результата Research Mode.
Цель: превратить рекомендацию в план реализации.
Используй утверждённые источники и сохрани видимыми нерешённые риски.
```

```text
Открой связанную задачу Research Mode.
Цель: проверить только слабые доказательства из предыдущего результата.
Результат: короткая заметка о рисках со ссылками на источники.
Глубина: M.
```

### Чего не делать

- Не просить агента вручную править `state.json`.
- Не считать черновики из `workspace/` финальным результатом.
- Не утверждать результат без просмотра.
- Не перезапускать зависшую задачу до проверки `summary` и `health`.
- Не публиковать трассы задач без очистки путей, id чатов, токенов и приватных
  материалов.
