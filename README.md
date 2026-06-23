# Research Mode

[English](#english) | [Русский](#русский)

[![CI](https://img.shields.io/github/actions/workflow/status/VKambulov/research-mode/ci.yml?branch=main&label=CI)](https://github.com/VKambulov/research-mode/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/VKambulov/research-mode?label=release)](https://github.com/VKambulov/research-mode/releases)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
![OpenClaw skill](https://img.shields.io/badge/OpenClaw-skill-2f6fed)
![Review gated](https://img.shields.io/badge/review-gated-0f766e)

## English

Research Mode is an OpenClaw cron-based skill for long-running research tasks.
It lets an agent work in bounded iterations, keep sources and notes on disk,
stop for human review, and deliver only an approved result.

Use it when a question is too large for one chat answer and the result should
survive restarts, retries, and review. Do not use it for quick lookups, ordinary
one-turn summaries, or small coding tasks.

Research Mode is not a standalone Python package. The helper scripts can be run
directly, but the normal product model assumes OpenClaw cron architecture for
scheduled work, task control, owner-channel updates, review, and delivery.

This project was originally created for a personal OpenClaw workflow and is
published for people who want to study, adapt, or run a similar setup. It is
provided as-is, without warranty or a promise that every OpenClaw installation
will work without local adjustment.

### Why It Exists

Ordinary chat is good for short answers. Long research is different:

- sources and findings need to accumulate over time;
- the agent may need several bounded work turns;
- the result should be inspectable before anyone treats it as final;
- failures should be visible instead of hidden inside a long chat session;
- follow-up work should start from the approved result, not from memory alone.

Research Mode gives that work a task folder, state file, worker loop, review
gate, and operator commands.

### Installation

Quick install from ClawHub:

```bash
clawhub install research-mode
openclaw skills check
```

ClawHub skill installs are text-only. Binary repository assets, such as
`assets/social-preview.png` and example `.xlsx` files, remain available from the
GitHub repository and GitHub releases.

Install from GitHub:

```bash
export OPENCLAW_SKILLS_DIR="/path/to/your/openclaw/skills"
git clone https://github.com/VKambulov/research-mode.git "$OPENCLAW_SKILLS_DIR/research-mode"
openclaw skills check
```

Some OpenClaw installations reject symlinks that resolve outside the configured
skills root. If that applies to your setup, keep the repository physically
inside the skills directory.

For local development when the skill already exists inside a larger OpenClaw
workspace:

```bash
cd /path/to/your/openclaw/skills/research-mode
git init
git add .
git status
```

### Quick Start

The normal user entrypoint is chat-first. Ask an OpenClaw agent to start a
Research Mode task and describe the work in plain language.

```text
Start a Research Mode task.
Goal: compare three tools for evaluating RAG quality in a small private knowledge base.
Deliverable: short recommendation memo with trade-offs and source links.
Depth: L.
Constraints: use primary sources where possible, mark weak evidence, avoid vendor-only claims.
Updates: send only milestones, blockers, and the final review candidate.
```

Another useful shape:

```text
Start Research Mode for a local corpus review.
Goal: review the attached notes and identify recurring architecture decisions.
Deliverable: concise decision map with open questions.
Depth: M.
Corpus: local only.
Updates: send blockers and the review candidate.
```

The request does not need to mention Python scripts. The scripts are the agent
and maintainer interface behind the chat workflow.

### What To Include In A Request

Good requests usually include:

- **Goal**: the question, comparison, audit, or decision target.
- **Deliverable**: memo, report, table, source list, evidence matrix, package, or
  another expected result.
- **Depth**: `S`, `M`, `L`, or `XL`.
- **Corpus**: `web`, `local`, or `hybrid`.
- **Constraints**: source quality, privacy, excluded sources, language,
  geography, deadline, or audience.
- **Updates**: how often the agent should interrupt you.
- **Inputs**: URLs, PDFs, screenshots, notes, datasets, or workspace files.

Depth is a planning hint:

- `S`: narrow task or short memo;
- `M`: normal background research;
- `L`: broader comparison or careful synthesis;
- `XL`: large investigation with possible review and rework cycles.

### Main Capabilities

- Durable task state stored on disk.
- Bounded worker turns through OpenClaw cron.
- Default preflight check before new tasks start.
- Source, finding, iteration, and result artifacts.
- Research adequacy check before finalization.
- Structured output contracts through `output_contract.outputs[]`.
- Human review before delivery.
- `request-changes` / `approve` review loop.
- Recovery and health commands for stalled or inconsistent tasks.
- Follow-up research based on an approved task.

### Review And Delivery

Research Mode does not treat raw workspace output as final. A task moves toward
review first. The human reviewer can approve it or request changes.

Typical review commands:

```bash
python3 scripts/research_mode.py request-changes --id <research-id> "what to change"
python3 scripts/research_mode.py approve --id <research-id>
```

For structured outputs, `delivery.outputs[]` records the user-facing files that
were delivered or are ready for review. `primary_file` and `attachments` remain
compatibility mirrors for older integrations.

### Where To Read Next

- `docs/USER_GUIDE.md` — practical user guide and request examples.
- `docs/OPERATIONS.md` — operator flows, scheduling, review, recovery, and
  quality gates.
- `docs/OUTPUTS.md` — output contracts, delivery outputs, candidate artifacts,
  and provenance links.
- `docs/CLI.md` — command reference for operators and maintainers.
- `docs/STATE_VERSIONING.md` — state compatibility and migration policy.
- `ARCHITECTURE.md` — system model and design decisions.
- `TROUBLESHOOTING.md` — diagnosis order and safe repair paths.
- `examples/README.md` — public example packages and sanitized traces.
- `ROADMAP.md`, `CONTRIBUTING.md`, `SECURITY.md`, `RELEASING.md`,
  `RELEASE_NOTES.md` — project status, contribution, safety, and release
  details.
- `.github/ISSUE_TEMPLATE/` — public issue templates.

### Project Status

Research Mode is under active development. The current priority is stable,
observable, recoverable research runs. Long-running tasks may still hit
scheduling, lifecycle, delivery, or environment issues. If a task looks stuck,
ask your OpenClaw agent to inspect `summary` and `health` before restarting the
research from scratch.

GitHub Actions runs the release gate and a Bandit security smoke scan. CodeQL is not enabled in the baseline.

License: Apache License, Version 2.0. See `LICENSE`.

## Русский

Research Mode — это OpenClaw skill для длительных исследовательских задач. Он
позволяет агенту работать короткими ограниченными итерациями, сохранять
источники и заметки на диск, останавливаться на проверку человеком и выдавать
только утверждённый результат.

Используйте его, когда вопрос слишком большой для одного ответа в чате, а
результат должен переживать перезапуски, доработки и проверку. Не используйте
его для быстрых справок, обычных коротких пересказов и небольших задач по коду.

Research Mode пока не является самостоятельным Python-пакетом. Скрипты можно
запускать напрямую, но обычная модель работы опирается на OpenClaw cron:
расписание рабочих итераций, управление задачей, сообщения владельцу, проверку
и доставку результата.

Проект вырос из личного OpenClaw-процесса и опубликован для тех, кто хочет
изучить, адаптировать или запустить похожую схему. Он поставляется как есть, без
гарантии, что подойдёт каждой установке OpenClaw без локальной настройки.

### Зачем это нужно

Обычный чат удобен для коротких ответов. Долгое исследование устроено иначе:

- источники и выводы накапливаются постепенно;
- агенту может понадобиться несколько ограниченных рабочих итераций;
- результат нужно проверить до того, как считать его финальным;
- сбои должны быть видны, а не прятаться внутри длинной переписки;
- продолжение работы должно опираться на утверждённый результат, а не только на
  память чата.

Research Mode даёт такой задаче папку, файл состояния, рабочий цикл, проверку
человеком и операторские команды.

### Установка

Быстрая установка из ClawHub:

```bash
clawhub install research-mode
openclaw skills check
```

Установка через ClawHub содержит только текстовые файлы. Бинарные файлы
репозитория, например `assets/social-preview.png` и примеры `.xlsx`, остаются
доступны в GitHub-репозитории и релизах GitHub.

Установка из GitHub:

```bash
export OPENCLAW_SKILLS_DIR="/path/to/your/openclaw/skills"
git clone https://github.com/VKambulov/research-mode.git "$OPENCLAW_SKILLS_DIR/research-mode"
openclaw skills check
```

Некоторые установки OpenClaw отклоняют символические ссылки, если они указывают за пределы
директории skills. В таком случае держите репозиторий физически внутри этой
директории.

Для локальной разработки, если skill уже лежит внутри большой рабочей области
OpenClaw:

```bash
cd /path/to/your/openclaw/skills/research-mode
git init
git add .
git status
```

### Быстрый старт

Здесь обычная пользовательская точка входа — чат. Попросите OpenClaw-агента
запустить задачу Research Mode и опишите работу обычным языком.

```text
Запусти задачу Research Mode.
Цель: сравнить три подхода к оценке качества RAG для небольшой частной базы знаний.
Результат: короткая рекомендация с компромиссами и ссылками на источники.
Глубина: L.
Ограничения: по возможности использовать первичные источники, отмечать слабые доказательства, не опираться только на материалы вендоров.
Обновления: присылай только важные этапы, блокеры и финальный результат на ревью.
```

Ещё один рабочий пример:

```text
Запусти Research Mode для обзора локальных заметок.
Цель: найти повторяющиеся архитектурные решения в приложенных материалах.
Результат: короткая карта решений и открытых вопросов.
Глубина: M.
Корпус: только локальные материалы.
Обновления: присылай блокеры и результат на проверку.
```

В запросе не нужно упоминать Python-скрипты. Скрипты — это интерфейс для агента
и сопровождающих за кулисами чатового сценария.

### Что указать в запросе

Хороший запрос обычно содержит:

- **цель**: вопрос, сравнение, аудит или решение, которое нужно подготовить;
- **результат**: заметка, отчёт, таблица, список источников, матрица
  доказательств, пакет файлов или другой ожидаемый итог;
- **глубину**: `S`, `M`, `L` или `XL`;
- **корпус**: `web`, `local` или `hybrid`;
- **ограничения**: качество источников, приватность, исключённые источники,
  язык, география, срок или аудитория;
- **обновления**: когда агенту стоит отвлекать вас сообщениями;
- **материалы**: ссылки, PDF, скриншоты, заметки, таблицы, наборы данных или
  файлы рабочей области.

Глубина — это ориентир планирования:

- `S`: узкая задача или короткая заметка;
- `M`: обычное фоновое исследование;
- `L`: более широкое сравнение или аккуратный синтез;
- `XL`: большое исследование с возможными ревью и доработками.

### Основные возможности

- Состояние задачи хранится на диске.
- Рабочие итерации запускаются через OpenClaw cron и имеют границы.
- Перед новыми задачами по умолчанию выполняется предварительная проверка.
- Источники, выводы, итерации и результаты сохраняются как артефакты.
- Перед финализацией есть проверка достаточности исследования.
- Ожидаемые результаты описываются через `output_contract.outputs[]`.
- Перед доставкой результата есть проверка человеком.
- Поддержан цикл `request-changes` / `approve`.
- Есть команды диагностики и восстановления для зависших или несогласованных
  задач.
- Можно запускать связанное исследование от уже утверждённого результата.

### Ревью и доставка

Research Mode не считает сырые файлы рабочей папки финальным результатом.
Сначала задача приходит на ревью. Человек может утвердить результат или
попросить доработку.

Типовые команды ревью:

```bash
python3 scripts/research_mode.py request-changes --id <research-id> "что изменить"
python3 scripts/research_mode.py approve --id <research-id>
```

Для структурированных результатов `delivery.outputs[]` хранит пользовательские
файлы, которые были доставлены или готовы к проверке. `primary_file` и
`attachments` остаются совместимыми полями для старых интеграций.

### Что читать дальше

- `docs/USER_GUIDE.md` — практическое руководство и примеры запросов.
- `docs/OPERATIONS.md` — запуск, расписания, ревью, восстановление и проверки
  качества.
- `docs/OUTPUTS.md` — контракты результатов, доставка, артефакты-кандидаты и
  связи происхождения.
- `docs/CLI.md` — справочник команд для операторов и сопровождающих.
- `docs/STATE_VERSIONING.md` — совместимость состояния и политика миграций.
- `ARCHITECTURE.md` — модель системы и архитектурные решения.
- `TROUBLESHOOTING.md` — порядок диагностики и безопасные способы ремонта.
- `examples/README.md` — публичные примеры и очищенные трассы исследований.
- `ROADMAP.md`, `CONTRIBUTING.md`, `SECURITY.md`, `RELEASING.md`,
  `RELEASE_NOTES.md` — статус проекта, вклад, безопасность и релизы.
- `.github/ISSUE_TEMPLATE/` — шаблоны публичных issues.

### Статус проекта

Research Mode активно развивается. Текущий приоритет — стабильные,
наблюдаемые и восстанавливаемые исследования. Долгие задачи всё ещё могут
упираться в проблемы расписания, жизненного цикла, доставки или окружения. Если
задача выглядит зависшей, сначала попросите OpenClaw-агента проверить `summary`
и `health`, а не запускайте исследование заново.

GitHub Actions запускает релизную проверку и Bandit security smoke scan. CodeQL
не включён в базовую проверку.

Лицензия: Apache License, Version 2.0. См. `LICENSE`.
