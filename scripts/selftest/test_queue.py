"""Global worker queue regressions."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .helpers import assert_eq, json_out, run


def _create_task(root: Path, task_id: str, goal: str | None = None) -> None:
    json_out(
        run(
            "create",
            "--root",
            str(root),
            "--id",
            task_id,
            "--goal",
            goal or f"Queue regression for {task_id}",
            "--skip-preflight",
        )
    )


def _finish_iteration(root: Path, task_id: str, lease: dict) -> dict:
    result_file = Path(lease["paths"]["result_file"])
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "summary": f"Finished {task_id} queue test iteration.",
                "next_angle": "Continue queued work.",
                "meaningful_progress": True,
                "phase": "search",
                "open_questions": [],
                "sources": [{"title": f"{task_id} source"}],
                "findings": [{"kind": "fact", "text": f"{task_id} finding"}],
                "notify_recommendation": "silent",
                "should_complete": False,
                "final_report_markdown": None,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return json_out(
        run(
            "finish",
            "--root",
            str(root),
            "--id",
            task_id,
            "--run-id",
            lease["run_id"],
            "--result-file",
            str(result_file),
        )
    )


def _queue_lock_path(root: Path) -> Path:
    return root / ".research-mode" / "queue" / "global-worker-lock.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_second_task_waits_while_first_task_holds_global_lease(root: Path) -> None:
    root = root / "queue-lock-case"
    _create_task(root, "queue-task-a")
    _create_task(root, "queue-task-b")

    lease_a = json_out(run("begin", "--root", str(root), "--id", "queue-task-a"))
    assert_eq(lease_a.get("status"), "leased", "task A should lease the worker")

    blocked_b = json_out(run("begin", "--root", str(root), "--id", "queue-task-b"))
    assert_eq(blocked_b.get("status"), "skipped", "task B should wait")
    assert_eq(
        blocked_b.get("reason"),
        "global-research-lock-active",
        "task B should report the global queue lock",
    )
    assert_eq(
        blocked_b.get("normalized_reason"),
        "deferred:global-research-lock",
        "task B should expose a normalized queue reason",
    )
    assert_eq(
        blocked_b.get("active_task_id"),
        "queue-task-a",
        "task B should identify the active holder",
    )
    _finish_iteration(root, "queue-task-a", lease_a)


def test_older_waiter_gets_turn_before_recent_holder_reacquires(root: Path) -> None:
    root = root / "queue-fairness-case"
    _create_task(root, "queue-fair-a")
    _create_task(root, "queue-fair-b")

    lease_a = json_out(run("begin", "--root", str(root), "--id", "queue-fair-a"))
    blocked_b = json_out(run("begin", "--root", str(root), "--id", "queue-fair-b"))
    assert_eq(blocked_b.get("status"), "skipped", "task B should become a waiter")

    finished_a = _finish_iteration(root, "queue-fair-a", lease_a)
    assert_eq(finished_a.get("status"), "idle", "task A should finish normally")

    reacquire_a = json_out(run("begin", "--root", str(root), "--id", "queue-fair-a"))
    assert_eq(
        reacquire_a.get("status"),
        "skipped",
        "recent holder should not reacquire before older waiter",
    )
    assert_eq(
        reacquire_a.get("active_task_id"),
        "queue-fair-b",
        "older waiter should be identified as the next eligible task",
    )

    lease_b = json_out(run("begin", "--root", str(root), "--id", "queue-fair-b"))
    assert_eq(lease_b.get("status"), "leased", "older waiter should get the next lease")


def test_stale_global_lease_without_matching_task_lock_can_be_recovered(root: Path) -> None:
    root = root / "queue-stale-global-case"
    _create_task(root, "queue-stale-next")
    _write_json(
        _queue_lock_path(root),
        {
            "status": "held",
            "task_id": "missing-task",
            "task_path": str(root / "missing-task"),
            "run_id": "old-run",
            "lease_token": "old-token",
            "started_at": "2000-01-01T00:00:00Z",
            "stale_timeout_min": 1,
            "policy": "global_iteration_lock",
            "released_at": None,
            "last_released_by": None,
        },
    )

    lease = json_out(run("begin", "--root", str(root), "--id", "queue-stale-next"))
    assert_eq(lease.get("status"), "leased", "stale global holder should be recovered")
    holder = _read_json(_queue_lock_path(root))
    assert_eq(
        holder.get("task_id"),
        "queue-stale-next",
        "new task should own recovered global lease",
    )


def test_queue_status_reports_active_holder_and_waiters(root: Path) -> None:
    root = root / "queue-status-case"
    _create_task(root, "queue-status-a")
    _create_task(root, "queue-status-b")

    lease_a = json_out(run("begin", "--root", str(root), "--id", "queue-status-a"))
    blocked_b = json_out(run("begin", "--root", str(root), "--id", "queue-status-b"))
    assert_eq(blocked_b.get("status"), "skipped", "task B should wait")

    queue_status = json_out(run("queue-status", "--root", str(root)))
    assert_eq(queue_status.get("status"), "running", "queue-status should show active holder")
    assert_eq(
        queue_status.get("active_holder_state"),
        "active",
        "queue-status should classify a fresh holder as active",
    )
    assert_eq(
        queue_status.get("active_task_id"),
        "queue-status-a",
        "queue-status should expose active holder",
    )
    assert_eq(queue_status.get("waiter_count"), 1, "queue-status should count waiters")
    assert_eq(
        queue_status.get("waiters", [{}])[0].get("task_id"),
        "queue-status-b",
        "queue-status should list waiting task",
    )

    summary_text = run(
        "summary",
        "--root",
        str(root),
        "--id",
        "queue-status-b",
        "--format",
        "text",
    ).stdout
    assert "Queue: waiting for global research worker" in summary_text
    _finish_iteration(root, "queue-status-a", lease_a)


def test_queue_status_uses_effective_worker_timeout_for_stale_holder(
    root: Path,
) -> None:
    root = root / "queue-status-effective-stale-case"
    _create_task(root, "queue-status-effective")

    lease = json_out(run("begin", "--root", str(root), "--id", "queue-status-effective"))
    state_path = root / "queue-status-effective" / "state.json"
    state = _read_json(state_path)
    ten_min_ago = (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    state["job"]["schedule_template"] = {"timeout_seconds": 300}
    state["lock"]["started_at"] = ten_min_ago
    state["lock"]["stale_timeout_min"] = 30
    _write_json(state_path, state)

    holder = _read_json(_queue_lock_path(root))
    holder["started_at"] = ten_min_ago
    holder["stale_timeout_min"] = 30
    _write_json(_queue_lock_path(root), holder)

    queue_status = json_out(run("queue-status", "--root", str(root)))
    assert_eq(
        queue_status.get("status"),
        "stale",
        "queue-status should not call a worker-timeout-stale holder running",
    )
    assert_eq(
        queue_status.get("active_holder_state"),
        "stale",
        "queue-status should use the matching task lock's effective timeout",
    )
    assert_eq(queue_status.get("active_run_id"), lease["run_id"], "stale holder should identify run")


def test_stop_stale_running_task_releases_matching_global_lease(root: Path) -> None:
    root = root / "queue-stop-stale-case"
    _create_task(root, "queue-stop-a")
    _create_task(root, "queue-stop-b")
    lease = json_out(run("begin", "--root", str(root), "--id", "queue-stop-a"))

    state_path = root / "queue-stop-a" / "state.json"
    state = _read_json(state_path)
    state["lock"]["started_at"] = "2000-01-01T00:00:00Z"
    state["lock"]["stale_timeout_min"] = 1
    _write_json(state_path, state)
    holder = _read_json(_queue_lock_path(root))
    holder["started_at"] = "2000-01-01T00:00:00Z"
    holder["stale_timeout_min"] = 1
    _write_json(_queue_lock_path(root), holder)

    stopped = json_out(run("stop", "--root", str(root), "--id", "queue-stop-a"))
    assert_eq(stopped.get("status"), "cancelled", "stale stop should cancel task")
    released = _read_json(_queue_lock_path(root))
    assert_eq(
        released.get("status"),
        "released",
        "stale stop should release matching global lease immediately",
    )
    assert_eq(released.get("run_id"), lease["run_id"], "released holder should identify old run")

    lease_b = json_out(run("begin", "--root", str(root), "--id", "queue-stop-b"))
    assert_eq(lease_b.get("status"), "leased", "another task should lease after stale stop")
