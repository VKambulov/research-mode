from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


class ResearchModeError(RuntimeError):
    pass


class StateNotFoundError(ResearchModeError):
    pass


class ValidationError(ResearchModeError):
    pass


NO_ACTIVE_LEASE: str | None = None


def utc_now() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_ts(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def minutes_since(value: str | None, now: dt.datetime | None = None) -> float | None:
    parsed = parse_ts(value)
    if not parsed:
        return None
    if now is None:
        now = dt.datetime.now(dt.timezone.utc)
    return (now - parsed).total_seconds() / 60.0


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def validate_research_id(research_id: str) -> str:
    value = str(research_id or "").strip()
    if not value:
        raise ValidationError("Invalid research id: id cannot be empty")
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise ValidationError(f"Invalid research id: {research_id}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        raise ValidationError(f"Invalid research id: {research_id}")
    return value


def resolve_under_root(root: Path, child: str | Path, *, label: str) -> Path:
    root_resolved = root.expanduser().resolve()
    path = Path(child).expanduser()
    if not path.is_absolute():
        path = root_resolved / path
    resolved = path.resolve()
    if not is_relative_to(resolved, root_resolved):
        raise ValidationError(f"{label} is outside research root: {child}")
    return resolved


def resolve_under_task(task_dir: Path, child: str | Path, *, label: str) -> Path:
    task_resolved = task_dir.expanduser().resolve()
    path = Path(child).expanduser()
    if not path.is_absolute():
        path = task_resolved / path
    resolved = path.resolve()
    if not is_relative_to(resolved, task_resolved):
        raise ValidationError(f"{label} is outside task directory: {child}")
    return resolved


def atomic_json_write(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)


def atomic_text_write(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    ensure_dir(path.parent)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    addition = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    atomic_text_write(path, existing + addition)


def tsv_escape(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    text = str(value)
    return text.replace("\t", " ").replace("\r", " ").replace("\n", " / ")


def compact_text(value: Any, *, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def append_tsv_row(path: Path, columns: list[str], row: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    header = "\t".join(columns) + "\n"
    values = "\t".join(tsv_escape(row.get(column)) for column in columns) + "\n"
    if not path.exists() or path.stat().st_size == 0:
        atomic_text_write(path, header + values)
        return
    existing = path.read_text(encoding="utf-8")
    if existing and not existing.endswith("\n"):
        existing += "\n"
    atomic_text_write(path, existing + values)


def read_tsv_rows(path: Path) -> list[dict[str, str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    if not lines:
        return []
    header = lines[0].split("\t")
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = line.split("\t")
        if len(values) < len(header):
            values += [""] * (len(header) - len(values))
        rows.append({key: values[idx] for idx, key in enumerate(header)})
    return rows


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    if slug:
        return slug[:48]
    import hashlib

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"task-{digest}"


def json_dump(data: Any) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateNotFoundError(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    records: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                f"Invalid JSONL in {path} at line {idx}: {exc}"
            ) from exc
        if isinstance(payload, dict):
            records.append(payload)
    return records


class StateEditor:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None
        self.state: dict[str, Any] | None = None

    def __enter__(self) -> dict[str, Any]:
        ensure_dir(self.path.parent)
        self.handle = self.path.open("r+", encoding="utf-8")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        try:
            state = json.load(self.handle)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid state file: {self.path}: {exc}") from exc
        if not isinstance(state, dict):
            raise ValidationError(f"Invalid state file: {self.path}: expected object")
        self.state = state
        return self.state

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.handle is None:
            return
        if exc_type is None and self.state is not None:
            self.handle.seek(0)
            self.handle.write(
                json.dumps(self.state, ensure_ascii=False, indent=2) + "\n"
            )
            self.handle.truncate()
            self.handle.flush()
            os.fsync(self.handle.fileno())
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()
