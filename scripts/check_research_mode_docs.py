#!/usr/bin/env python3
"""Smoke-check Research Mode skill and documentation contracts."""
from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from research_mode import build_parser  # noqa: E402

REQUIRED_DOC_PATHS = [
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "README.md",
    SKILL_DIR / "TROUBLESHOOTING.md",
    SKILL_DIR / "ARCHITECTURE.md",
    SKILL_DIR / "RELEASING.md",
    SKILL_DIR / "RELEASE_NOTES.md",
    SKILL_DIR / "LICENSE",
    SKILL_DIR / "SECURITY.md",
    SKILL_DIR / "AGENTS.md",
    SKILL_DIR / "examples" / "README.md",
    SKILL_DIR / "assets" / "README.md",
]

REQUIRED_ASSET_PATHS = [
    SKILL_DIR / "assets" / "social-preview.png",
]

OPTIONAL_DOC_PATHS: list[Path] = []

FORBIDDEN_PATTERNS = {
    r"request-changes[^\n]*--feedback": "request-changes uses positional feedback text",
    r"Important v1\.2": "current docs should not lead with v1.2-era labels",
    r"Дата: 2026-04-0[45]": "current canonical docs should carry the refreshed date",
    r"MVP-движок": "current docs should not frame the baseline as MVP",
    r"Create a manual demo task": "README should be chat-first, not CLI-first",
    r"Acquire one worker lease": "README should not present worker lease acquisition as user quickstart",
    r"Создать demo-задачу": "README should be chat-first, not CLI-first",
    r"Взять одну рабочую блокировку": "README should not present worker lease acquisition as user quickstart",
}

REQUIRED_SNIPPETS = {
    "SKILL.md": [
        "Do **not** use this skill for:",
        "Do not install dangerous or suspicious packages",
        "request-changes --id <research-id> \"what to change\"",
        "Research adequacy gate",
        "phase=verify",
        "result.adequacy",
        "delivery.review_ready=true",
        "scripts/check_research_mode.sh",
    ],
    "README.md": [
        "[English](#english) | [Русский](#русский)",
        "## English",
        "## Русский",
        "OpenClaw cron-based skill",
        "OpenClaw cron architecture",
        "### Installation",
        "### Установка",
        "### User Guide",
        "### Руководство пользователя",
        "#### How A Task Is Started",
        "#### Как запускается задача",
        "#### Launch Parameters",
        "#### Параметры запуска",
        "### Operations",
        "### Операции",
        "personal OpenClaw workflow",
        "поставляется как есть",
        "OPENCLAW_SKILLS_DIR",
        "openclaw skills check",
        'git clone https://github.com/VKambulov/research-mode.git "$OPENCLAW_SKILLS_DIR/research-mode"',
        "reject symlinks",
        "git init",
        "normal user entrypoint",
        "обычная пользовательская точка входа",
        "Launch Parameters",
        "Параметры запуска",
        "Depth Selection",
        "Выбор глубины",
        "During The Task",
        "Работа во время задачи",
        "Review And Delivery",
        "Ревью и доставка",
        "Research Adequacy Gate",
        "Проверка достаточности исследования",
        "phase=verify",
        "result.adequacy",
        "Common Work Patterns",
        "Частые рабочие сценарии",
        "Launch Mode 1: Chat-First Start",
        "Вариант запуска 1: через чат",
        "Launch Mode 2: Create And Schedule In One Step",
        "Вариант запуска 2: создать и запланировать одной командой",
        "Launch Mode 3: Create, Attach, Then Schedule",
        "Вариант запуска 3: создать, прикрепить материалы, затем запланировать",
        "Launch Mode 4: Manual Worker Iteration",
        "Вариант запуска 4: ручная рабочая итерация",
        "Review And Delivery Commands",
        "Команды ревью и доставки",
        "Quality Gates",
        "Проверки качества",
        "`attach-url-as-md` accepts only `http://` and `https://` URLs and blocks local",
        "including redirect targets",
        "attach-url-as-md` принимает только URL с `http://` и `https://` и блокирует",
        "включая redirect targets",
        "ARCHITECTURE.md",
        "TROUBLESHOOTING.md",
        "RELEASING.md",
        "RELEASE_NOTES.md",
        "SECURITY.md",
        "AGENTS.md",
        "examples/",
        "At A Glance",
        "Why It Stands Out",
        "Showcase",
        "Apache License, Version 2.0",
        "LICENSE",
        "check_research_mode_docs.py",
        "check_research_mode.sh",
    ],
    "ARCHITECTURE.md": [
        "[English](#english) | [Русский](#русский)",
        "## English",
        "## Русский",
        "```mermaid",
        "distributed as an OpenClaw skill package",
        "state.json",
        "operator_next_action",
        "Why This Architecture Is Better For Durable Research",
        "Почему эта архитектура лучше для длительных исследований",
        "not as a standalone Python daemon",
        "Review before delivery",
        "Research Adequacy Gate",
        "result.adequacy",
        "Проверка достаточности исследования",
    ],
    "TROUBLESHOOTING.md": [
        "[English](#english) | [Русский](#русский)",
        "## English",
        "## Русский",
        "Diagnosis Order",
        "Порядок диагностики",
        "Task Does Not Progress",
        "Задача не продвигается",
        "Completion Was Rejected",
        "Завершение отклонено",
        "adequacy.operator_next_action",
        "проверка достаточности исследования",
        "Documentation Smoke Fails",
        "Не прошёл docs smoke",
        "Full Gate Fails",
        "Не прошла полная проверка",
        "manual edits to `state.json`",
        "Ручное редактирование файлов",
    ],
    "RELEASING.md": [
        "[English](#english) | [Русский](#русский)",
        "## English",
        "## Русский",
        "OpenClaw cron-based skill package",
        "## Package boundary",
        "## Граница пакета",
        "Include in the public package",
        "Включать в публичный пакет",
        "Exclude from the public package",
        "Исключать из публичного пакета",
        "## Release gate",
        "## Контур релиза",
        "## Release safety review",
        "## Проверка безопасности релиза",
        "## Finalization contract",
        "README explains installation",
        "README объясняет установку",
        "TROUBLESHOOTING.md",
        "operator_next_action",
        "scripts/release_smoke.py",
        "scripts/check_research_mode.sh",
        "ARCHITECTURE.md",
        "RELEASE_NOTES.md",
        "SECURITY.md",
        "AGENTS.md",
        "examples/",
        "assets/",
        "Apache License, Version 2.0",
    ],
    "examples/README.md": [
        "Research Mode Examples",
        "web-capture-evaluation/",
        "rag-eval-tooling-matrix/",
        "research-trace/",
        "Showcase",
        "sanitized copy",
        "private workspace paths",
        "chat identifiers",
    ],
    "assets/README.md": [
        "Research Mode Assets",
        "social-preview.png",
        "1280x640 GitHub social preview image",
        "generated visual background",
        "deterministic text",
    ],
    "RELEASE_NOTES.md": [
        "[English](#english) | [Русский](#русский)",
        "## English",
        "## Русский",
        "v0.1.0",
        "GitHub Actions CI",
        "OpenClaw cron-based skill",
        "Known limitations",
        "Известные ограничения",
        "Apache License, Version 2.0",
        "LICENSE",
        "scripts/release_smoke.py",
    ],
    "LICENSE": [
        "Apache License",
        "Version 2.0",
        "Copyright 2026 Vladislav Kambulov and Research Mode contributors",
        "Grant of Patent License",
        "END OF TERMS AND CONDITIONS",
    ],
    "SECURITY.md": [
        "[English](#english) | [Русский](#русский)",
        "## English",
        "## Русский",
        "tokens, webhooks, chat ids",
        "URL capture accepts only `http://` and `https://` and blocks local",
        "task-local",
        "untrusted data",
        "private security advisory",
    ],
    "AGENTS.md": [
        "Human-facing project documentation",
        "Keep The Boundary Clear",
        "Do not mix hidden prompts or agent-only instructions into human-facing docs",
        "Research Mode is an OpenClaw skill",
        "scripts/check_research_mode.sh",
    ],
}

BASH_BLOCK_PATTERN = re.compile(r"```(?:bash|sh|shell)\n(.*?)```", re.DOTALL)


def _command_names() -> set[str]:
    parser = build_parser()
    commands: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            commands.update(action.choices)
    return commands


def _command_options() -> dict[str, set[str]]:
    parser = build_parser()
    options: dict[str, set[str]] = {}
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for command, subparser in action.choices.items():
            command_options = {"--help", "-h"}
            for sub_action in subparser._actions:
                command_options.update(sub_action.option_strings)
            options[command] = command_options
    return options


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _doc_key(path: Path) -> str:
    try:
        return str(path.relative_to(SKILL_DIR))
    except ValueError:
        return _relative(path)


def _read_docs() -> dict[Path, str]:
    docs: dict[Path, str] = {}
    for path in REQUIRED_DOC_PATHS:
        if not path.exists():
            raise AssertionError(f"missing documented file: {_relative(path)}")
        docs[path] = path.read_text(encoding="utf-8")
    for path in OPTIONAL_DOC_PATHS:
        if path.exists():
            docs[path] = path.read_text(encoding="utf-8")
    return docs


def _validate_no_forbidden(docs: dict[Path, str]) -> list[str]:
    errors: list[str] = []
    for path, text in docs.items():
        for pattern, reason in FORBIDDEN_PATTERNS.items():
            match = re.search(pattern, text)
            if match:
                errors.append(
                    f"{_relative(path)}: forbidden pattern {pattern!r}: {reason}"
                )
    return errors


def _validate_required_snippets(docs: dict[Path, str]) -> list[str]:
    errors: list[str] = []
    by_relative = {_doc_key(path): text for path, text in docs.items()}
    optional_rel_paths = {_relative(path) for path in OPTIONAL_DOC_PATHS}
    for rel_path, snippets in REQUIRED_SNIPPETS.items():
        text = by_relative.get(rel_path)
        if text is None:
            if rel_path in optional_rel_paths:
                continue
            errors.append(f"required snippet target missing: {rel_path}")
            continue
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"{rel_path}: missing required snippet: {snippet!r}")
    return errors


def _validate_documented_commands(docs: dict[Path, str]) -> list[str]:
    commands = _command_names()
    errors: list[str] = []
    command_pattern = re.compile(r"research_mode\.py\s+([a-z][a-z0-9-]+)")
    for path, text in docs.items():
        for command in command_pattern.findall(text):
            if command not in commands:
                errors.append(
                    f"{_relative(path)}: documented unknown command: {command}"
                )
    return errors


def _logical_shell_lines(block: str) -> list[str]:
    lines: list[str] = []
    current = ""
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if current:
            current = f"{current} {line}"
        else:
            current = line
        if current.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        lines.append(current)
        current = ""
    if current:
        lines.append(current)
    return lines


def _research_mode_invocations(line: str) -> list[list[str]]:
    try:
        tokens = shlex.split(line)
    except ValueError:
        return []

    invocations: list[list[str]] = []
    for index, token in enumerate(tokens):
        if Path(token).name != "research_mode.py":
            continue
        invocation: list[str] = []
        for part in tokens[index + 1 :]:
            if part in {"&&", ";", "||", "|"}:
                break
            invocation.append(part)
        if invocation:
            invocations.append(invocation)
    return invocations


def _normalize_option(token: str) -> str | None:
    if token.startswith("[--"):
        token = token[1:]
    if token.endswith("]"):
        token = token[:-1]
    if not token.startswith("-"):
        return None
    return token.split("=", 1)[0]


def _validate_documented_bash_blocks(docs: dict[Path, str]) -> list[str]:
    commands = _command_names()
    command_options = _command_options()
    errors: list[str] = []

    for path, text in docs.items():
        for block in BASH_BLOCK_PATTERN.findall(text):
            for line in _logical_shell_lines(block):
                for invocation in _research_mode_invocations(line):
                    command = invocation[0]
                    if command not in commands:
                        continue
                    valid_options = command_options[command]
                    for token in invocation[1:]:
                        option = _normalize_option(token)
                        if option and option not in valid_options:
                            errors.append(
                                f"{_relative(path)}: documented unknown option "
                                f"for {command}: {option}"
                            )
    return errors


def _validate_required_assets() -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_ASSET_PATHS:
        if not path.exists():
            errors.append(f"missing documented asset: {_relative(path)}")
        elif path.stat().st_size == 0:
            errors.append(f"documented asset is empty: {_relative(path)}")
    return errors


def main() -> int:
    docs = _read_docs()
    errors = [
        *_validate_no_forbidden(docs),
        *_validate_required_snippets(docs),
        *_validate_documented_commands(docs),
        *_validate_documented_bash_blocks(docs),
        *_validate_required_assets(),
    ]
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("research-mode docs smoke check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
