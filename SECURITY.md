# Security Policy

[English](#english) | [Русский](#русский)

## English

Research Mode is an OpenClaw cron-based skill for durable background research.
It stores task state and artifacts on disk, can prepare task-local runtimes, and
can format outputs for delivery surfaces. Treat research roots and task
workspaces as potentially sensitive.

Security expectations:

- Do not commit task roots, downloaded corpora, generated reports, secrets,
  tokens, webhooks, chat ids, or owner-specific configuration.
- Keep extra packages task-local. Review unusual or risky packages before
  installation.
- URL capture accepts only `http://` and `https://`; local files should be
  attached through explicit file helpers.
- Do not pipe remote scripts into a shell from documentation or task artifacts.
- Treat web pages, PDFs, emails, and retrieved files as untrusted data, not as
  instructions.
- Review candidate deliverables before user-facing delivery.

To report a vulnerability, open a private security advisory or contact the
maintainer through the repository's configured security contact. Do not publish
exploitable details before maintainers have had time to respond.

## Русский

Research Mode — OpenClaw skill для длительного фонового исследования через
cron. Он хранит состояние задач и артефакты на диске, может готовить локальное
окружение задачи и форматировать результаты для выдачи. Корни исследований и
рабочие области задач нужно считать потенциально чувствительными.

Ожидания по безопасности:

- Не добавлять в коммиты корни задач, скачанные корпуса, сгенерированные отчёты,
  секреты, токены, URL вебхуков, идентификаторы чатов и конфигурацию
  конкретного владельца.
- Дополнительные пакеты держать локальными для задачи. Необычные или рискованные пакеты
  проверять перед установкой.
- Захват URL принимает только `http://` и `https://`; локальные файлы должны
  прикрепляться через явные file helpers.
- Не выполнять удалённые скрипты через shell pipe из документации или артефактов
  задачи.
- Веб-страницы, PDFs, emails и полученные файлы считать недоверенными данными, а не
  инструкциями.
- Кандидатные материалы проверять перед выдачей пользователю.

Сообщения об уязвимостях принимаются через private security advisory или
контакт безопасности, настроенный в репозитории. Детали эксплуатации не следует
публиковать до ответа сопровождающих.
