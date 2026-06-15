"""Basic lifecycle: create, begin, finish, fail, status, summary, stale lock, salvage."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .helpers import assert_eq, assert_in, assert_true, json_out, run


def test_basic_lifecycle(root: Path) -> None:
    created = json_out(
        run(
            "create", "--root", str(root), "--id", "task-a",
            "--goal", "Self-test main lifecycle", "--title", "Task A",
        )
    )
    assert_eq(created["status"], "created", "create status")

    status0 = run("status", "--root", str(root), "--id", "task-a", "--format", "text").stdout
    assert_in("Status: idle", status0, "task-a should start idle")

    lease = json_out(run("begin", "--root", str(root), "--id", "task-a"))
    assert_eq(lease["status"], "leased", "begin status")
    run_id = lease["run_id"]
    result_file = Path(lease["paths"]["result_file"])
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "summary": "Lifecycle finish path works.",
                "next_angle": "Test fail path next.",
                "meaningful_progress": True,
                "code_used": True,
                "phase": "search",
                "open_questions": ["Need more tests?"],
                "sources": [{"title": "selftest-source"}],
                "findings": [{"kind": "fact", "text": "finish ok"}],
                "analysis_artifacts": [
                    {"path": "workspace/analysis/lifecycle_probe.py", "kind": "script", "note": "sanity-check helper"},
                    {"path": "workspace/outputs/lifecycle_probe.json", "kind": "dataset", "note": "probe output"},
                ],
                "packages_used": ["pandas"],
                "database_used": True,
                "database_artifacts": [
                    {"path": "workspace/data/analysis.sqlite", "kind": "sqlite-db", "note": "task-local structured store"},
                    {"path": "workspace/analysis/schema.sql", "kind": "schema", "note": "bootstrap schema"},
                    {"path": "workspace/analysis/queries/reviewed.sql", "kind": "query", "note": "sample view"},
                ],
                "database_summary": {
                    "db_path": "workspace/data/analysis.sqlite",
                    "purpose": "structured dedup and ranking",
                    "tables": ["_rm_meta", "records"],
                    "row_counts": {"_rm_meta": 3, "records": 12},
                },
                "vision_used": True,
                "vision_artifacts": [
                    {"path": "workspace/outputs/screenshots/map-cluster.png", "kind": "screenshot", "note": "map cluster screenshot"},
                    {"path": "workspace/outputs/vision/map-cluster-notes.md", "kind": "vision-note", "note": "visual triage notes"},
                ],
                "vision_summary": {"purpose": "map triage", "images_reviewed": 2, "confidence": "medium"},
                "notify_recommendation": "silent",
                "should_complete": False,
                "final_report_markdown": None,
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    finished = json_out(
        run("finish", "--root", str(root), "--id", "task-a", "--run-id", run_id, "--result-file", str(result_file))
    )
    assert_eq(finished["status"], "idle", "finish should return to idle")
    assert_eq(finished["update_text"], None, "silent finish should not emit update text")

    summary_text = run("summary", "--root", str(root), "--id", "task-a", "--format", "text").stdout
    assert_in("Working summary: Lifecycle finish path works.", summary_text, "summary should show working summary")
    assert_in("Recent findings", summary_text, "summary should include findings block")
    summary_json = json_out(run("summary", "--root", str(root), "--id", "task-a", "--format", "json"))
    assert_eq(summary_json["totals"]["findings"], 1, "summary json should count findings")
    assert_eq(summary_json["totals"]["sources"], 1, "summary json should count sources")
    assert_true(summary_json["analysis"]["code_used_recently"], "summary json should expose recent code-assisted work")
    assert_eq(summary_json["analysis"]["last_packages_used"], ["pandas"], "summary json should preserve packages_used from result payload")
    assert_eq(len(summary_json["analysis"]["last_analysis_artifacts"]), 2, "summary json should preserve analysis_artifacts from result payload")
    assert_true(summary_json["analysis"]["database_used_recently"], "summary json should expose recent database-backed work")
    assert_eq(summary_json["analysis"]["last_database_summary"]["purpose"], "structured dedup and ranking", "summary json should preserve database_summary from result payload")
    assert_eq(len(summary_json["analysis"]["last_database_artifacts"]), 3, "summary json should preserve database_artifacts from result payload")
    assert_true(summary_json["analysis"]["vision_used_recently"], "summary json should expose recent vision-assisted work")
    assert_eq(summary_json["analysis"]["last_vision_summary"]["purpose"], "map triage", "summary json should preserve vision_summary from result payload")
    assert_eq(len(summary_json["analysis"]["last_vision_artifacts"]), 2, "summary json should preserve vision_artifacts from result payload")
    state_after_finish = json.loads((root / "task-a" / "state.json").read_text(encoding="utf-8"))
    finish_transaction = state_after_finish.get("transactions", {}).get("finish")
    assert_eq(
        finish_transaction.get("status"),
        "committed",
        "finish should record a committed transaction marker for crash recovery",
    )
    assert_eq(
        finish_transaction.get("run_id"),
        run_id,
        "finish transaction marker should identify the committed run",
    )
    iteration_md = (root / "task-a" / "iterations" / "001.md").read_text(encoding="utf-8")
    assert_in("## Analysis artifacts", iteration_md, "iteration markdown should include analysis artifacts section")
    assert_in("## Packages used", iteration_md, "iteration markdown should include packages used section")
    assert_in("## Database artifacts", iteration_md, "iteration markdown should include database artifacts section")
    assert_in("## Database summary", iteration_md, "iteration markdown should include database summary section")
    assert_in("## Vision artifacts", iteration_md, "iteration markdown should include vision artifacts section")
    assert_in("## Vision summary", iteration_md, "iteration markdown should include vision summary section")

    lease2 = json_out(run("begin", "--root", str(root), "--id", "task-a"))
    failed = json_out(
        run("fail", "--root", str(root), "--id", "task-a", "--run-id", lease2["run_id"], "--error", "intentional selftest failure")
    )
    assert_eq(failed["status"], "idle", "fail should unlock and return idle")
    assert_eq(failed["update_text"], None, "non-blocking fail should stay silent")

    lease3 = json_out(run("begin", "--root", str(root), "--id", "task-a"))
    failed_blocker = json_out(
        run("fail", "--root", str(root), "--id", "task-a", "--run-id", lease3["run_id"], "--error", "need clarification from user", "--requires-user-input")
    )
    assert_eq(failed_blocker["status"], "failed", "blocker fail should mark task failed")
    assert_true(
        "нужен" in failed_blocker["update_text"].lower() or "остановилось" in failed_blocker["update_text"].lower(),
        "blocker fail should emit human update text",
    )

    resumed_from_failed = json_out(run("resume", "--root", str(root), "--id", "task-a"))
    assert_eq(resumed_from_failed["status"], "failed", "resume should not change failed state")


def test_milestone_and_control(root: Path) -> None:
    created_d = json_out(
        run(
            "create", "--root", str(root), "--id", "task-d",
            "--goal", "Self-test milestone update text", "--title", "Task D",
            "--constraint", "use strong sources only",
            "--instruction", "highlight contradictions",
            "--deliverable", "short memo",
            "--open-question", "what is still weak?",
        )
    )
    assert_eq(created_d["status"], "created", "task-d create")
    state_d = json_out(run("status", "--root", str(root), "--id", "task-d", "--format", "json"))
    assert_in("use strong sources only", state_d["working_memory"]["constraints"], "create should seed constraints")
    assert_in("highlight contradictions", state_d["working_memory"]["user_instructions"], "create should seed instructions")
    assert_eq(state_d["working_memory"]["deliverable"], "short memo", "create should seed deliverable")
    assert_in("what is still weak?", state_d["working_memory"]["open_questions"], "create should seed open questions")
    lease_d = json_out(run("begin", "--root", str(root), "--id", "task-d"))
    result_file_d = Path(lease_d["paths"]["result_file"])
    result_file_d.parent.mkdir(parents=True, exist_ok=True)
    result_file_d.write_text(
        json.dumps(
            {
                "summary": "Нашла первую существенную связку источников.",
                "next_angle": "Проверить контраргументы и добрать первичку.",
                "meaningful_progress": True,
                "phase": "analyze",
                "open_questions": [],
                "sources": [{"title": "source-d", "url": "https://example.com/d"}],
                "findings": [{"kind": "fact", "text": "Есть подтверждение по двум независимым источникам.", "source_urls": ["https://example.com/d"]}],
                "notify_recommendation": "milestone",
                "should_complete": False,
                "final_report_markdown": None,
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    finished_d = json_out(
        run("finish", "--root", str(root), "--id", "task-d", "--run-id", lease_d["run_id"], "--result-file", str(result_file_d))
    )
    assert_eq(finished_d["status"], "idle", "milestone finish should return to idle")
    assert_true(bool(finished_d["update_text"]), "milestone finish should emit update text")
    assert_in("Апдейт по исследованию", finished_d["update_text"], "milestone text should be human-readable")

    pause = json_out(run("pause", "--root", str(root), "--id", "task-d"))
    assert_eq(pause["status"], "paused", "pause status")
    resumed = json_out(run("resume", "--root", str(root), "--id", "task-d"))
    assert_eq(resumed["status"], "idle", "resume status")

    stop = json_out(run("stop", "--root", str(root), "--id", "task-d"))
    assert_eq(stop["status"], "cancelled", "stop status")
    assert_eq(stop["normalized_reason"], "stopped:user", "stop should expose normalized terminal reason")


def test_stale_lock_detection_and_recovery(root: Path) -> None:
    created_b = json_out(
        run("create", "--root", str(root), "--id", "task-b", "--goal", "Self-test stale lock", "--title", "Task B", "--stale-timeout-min", "1")
    )
    assert_eq(created_b["status"], "created", "task-b create")
    lease_b = json_out(run("begin", "--root", str(root), "--id", "task-b"))
    state_path = root / "task-b" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["lock"]["started_at"] = "2020-01-01T00:00:00Z"
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status_before = json_out(run("status", "--root", str(root), "--id", "task-b"))
    lock_before = status_before.get("lock", {})
    assert_true(lock_before.get("is_stale"), "status should detect stale lock before recovery")
    assert_true(lock_before.get("lock_age_min") is not None and lock_before.get("lock_age_min") > 0, "status should show lock_age_min > 0 for stale lock")

    recovered = json_out(run("begin", "--root", str(root), "--id", "task-b"))
    assert_eq(recovered["status"], "leased", "stale lock recovery begin")
    state_after = json.loads(state_path.read_text(encoding="utf-8"))
    assert_eq(state_after["lock"]["recovered_count"], 1, "recovered_count should increment")
    assert_eq(state_after["lock"]["last_recovered_from_run"], lease_b["run_id"], "should remember recovered run")

    status_after = json_out(run("status", "--root", str(root), "--id", "task-b"))
    assert_in("lock", status_after, "status should include lock info")
    lock_info = status_after.get("lock", {})
    assert_in("lock_age_min", lock_info, "status should expose lock_age_min")
    assert_in("is_stale", lock_info, "status should expose is_stale")
    assert_true(not lock_info.get("is_stale"), "after recovery, lock should not be stale")

    summary_after = json_out(run("summary", "--root", str(root), "--id", "task-b", "--format", "json"))
    assert_in("lock", summary_after, "summary should include lock info")
    lock_in_summary = summary_after.get("lock", {})
    assert_in("lock_age_min", lock_in_summary, "summary should expose lock_age_min")
    assert_in("is_stale", lock_in_summary, "summary should expose is_stale")
    summary_text = run("summary", "--root", str(root), "--id", "task-b", "--format", "text").stdout
    assert_in("Lock:", summary_text, "summary text should include lock line")
    assert_in("workspace_dir", recovered["paths"], "work order should expose task-local workspace/runtime paths")
    assert_in("venv_dir", recovered["paths"], "work order should expose task-local workspace/runtime paths")

    recovery_note_path = (state_after.get("artifacts") or {}).get("last_recovery_note_path")
    assert_true(recovery_note_path is None, "recovery note should NOT be created when no result file exists")


def test_abandoned_run_without_result(root: Path) -> None:
    json_out(
        run("create", "--root", str(root), "--id", "task-abandoned", "--goal", "Self-test abandoned run without result file", "--title", "Task Abandoned", "--stale-timeout-min", "1")
    )
    _lease_d = json_out(run("begin", "--root", str(root), "--id", "task-abandoned"))
    state_path_d = root / "task-abandoned" / "state.json"
    state_d = json.loads(state_path_d.read_text(encoding="utf-8"))
    state_d["lock"]["started_at"] = "2020-01-01T00:00:00Z"
    state_d["phase"] = "search"
    state_path_d.write_text(json.dumps(state_d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    recovered_d = json_out(run("begin", "--root", str(root), "--id", "task-abandoned"))
    assert_eq(recovered_d["status"], "leased", "stale recovery should get lease")
    state_after_d = json.loads(state_path_d.read_text(encoding="utf-8"))
    assert_true((state_after_d.get("artifacts") or {}).get("abandoned_run_id"), "state should have abandoned_run_id when no result file")
    assert_true((state_after_d.get("artifacts") or {}).get("abandoned_at"), "state should have abandoned_at when no result file")
    audit_trail_d = state_after_d.get("history", {}).get("audit_trail", [])
    assert_true(any(e.get("event") == "run_abandoned" for e in audit_trail_d), "audit_trail should have run_abandoned event")


def test_stop_with_stale_lock(root: Path) -> None:
    json_out(
        run("create", "--root", str(root), "--id", "task-stop-abandoned", "--goal", "Self-test stop with stale lock", "--title", "Task Stop Abandoned", "--stale-timeout-min", "1")
    )
    _lease_e = json_out(run("begin", "--root", str(root), "--id", "task-stop-abandoned"))
    state_path_e = root / "task-stop-abandoned" / "state.json"
    state_e = json.loads(state_path_e.read_text(encoding="utf-8"))
    state_e["lock"]["started_at"] = "2020-01-01T00:00:00Z"
    state_e["phase"] = "search"
    state_path_e.write_text(json.dumps(state_e, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    stopped_e = json_out(run("stop", "--root", str(root), "--id", "task-stop-abandoned"))
    assert_eq(stopped_e["status"], "cancelled", "stop should cancel with stale lock")
    assert_true(stopped_e.get("abandoned_run_id"), "stop response should include abandoned_run_id")
    state_after_e = json.loads(state_path_e.read_text(encoding="utf-8"))
    assert_eq(state_after_e["status"], "cancelled", "state should be cancelled")
    lock_after_e = state_after_e.get("lock", {})
    assert_eq(lock_after_e.get("status"), "free", "lock should be free after stop")


def test_partial_progress_salvage(root: Path) -> None:
    json_out(
        run("create", "--root", str(root), "--id", "task-salvage", "--goal", "Self-test partial progress salvage", "--title", "Task Salvage", "--stale-timeout-min", "1")
    )
    lease_c = json_out(run("begin", "--root", str(root), "--id", "task-salvage"))
    result_file_c = Path(lease_c["paths"]["result_file"])
    result_file_c.parent.mkdir(parents=True, exist_ok=True)
    result_file_c.write_text(
        json.dumps(
            {
                "summary": "Partial progress from stale run.",
                "next_angle": "Continue from here.",
                "meaningful_progress": True,
                "phase": "analyze",
                "open_questions": ["What else to find?"],
                "sources": [{"title": "partial-source", "url": "https://example.com/partial"}],
                "findings": [{"kind": "fact", "text": "Partial finding saved."}],
                "notify_recommendation": "silent",
                "should_complete": False,
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    state_path_c = root / "task-salvage" / "state.json"
    state_c = json.loads(state_path_c.read_text(encoding="utf-8"))
    state_c["lock"]["started_at"] = "2020-01-01T00:00:00Z"
    state_c["phase"] = "analyze"
    state_path_c.write_text(json.dumps(state_c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    recovered_c = json_out(run("begin", "--root", str(root), "--id", "task-salvage"))
    assert_eq(recovered_c["status"], "leased", "stale recovery should get lease")
    assert_in("recovery_note", recovered_c, "recovery should include recovery_note in work order")
    recovery_note_info = recovered_c.get("recovery_note") or {}
    assert_true(recovery_note_info.get("exists"), "recovery_note should exist")
    assert_in("recovery-note-", recovery_note_info.get("path", ""), "recovery_note path should have recovery-note prefix")

    state_after_c = json.loads(state_path_c.read_text(encoding="utf-8"))
    assert_true((state_after_c.get("artifacts") or {}).get("last_recovery_note_path"), "state should have last_recovery_note_path")
    assert_true((state_after_c.get("artifacts") or {}).get("last_recovery_run_id"), "state should have last_recovery_run_id")
    assert_true((state_after_c.get("artifacts") or {}).get("last_recovery_at"), "state should have last_recovery_at")

    iteration_count_before = state_after_c["progress"]["iteration_count"]
    _lease_d2 = json_out(run("begin", "--root", str(root), "--id", "task-salvage"))
    state_with_d = json.loads(state_path_c.read_text(encoding="utf-8"))
    iteration_count_after = state_with_d["progress"]["iteration_count"]
    assert_eq(iteration_count_before, iteration_count_after, "iteration_count should NOT increase from recovery")

    summary_c = json_out(run("summary", "--root", str(root), "--id", "task-salvage", "--format", "json"))
    artifacts_c = summary_c.get("artifacts") or {}
    assert_true(artifacts_c.get("last_recovery_note_path"), "summary artifacts should show recovery note path")

    summary_text_c = run("summary", "--root", str(root), "--id", "task-salvage", "--format", "text").stdout
    assert_in("Recovery note:", summary_text_c, "summary text should show recovery note line")


def test_schedule_and_runtime(root: Path) -> None:
    json_out(
        run("create", "--root", str(root), "--id", "task-sched", "--goal", "Schedule and runtime test", "--stale-timeout-min", "1")
    )
    dry = json_out(run("schedule", "--root", str(root), "--id", "task-sched", "--dry-run"))
    assert_eq(dry["status"], "dry-run", "schedule dry-run status")
    assert_true(dry["command"][:3] == ["openclaw", "cron", "add"], "schedule should build cron add command")
    assert_in("--no-deliver", dry["command"], "schedule should keep cron delivery internal by default")
    prompt = run("render-prompt", "--root", str(root), "--id", "task-sched").stdout
    assert_in("message tool", prompt, "worker prompt should explain explicit messaging in internal-delivery mode")
    assert_in("--no-deliver", prompt, "worker prompt should explain explicit messaging in internal-delivery mode")
    assert_in("prepare-runtime", prompt, "worker prompt should mention task-local runtime preparation")
    assert_in("paths.venv_dir", prompt, "worker prompt should tell workers to use the task-local venv Python")
    assert_in("not the system python3", prompt, "worker prompt should avoid false cron failures from missing task-local packages")
    assert_in("paths.workspace_analysis_dir", prompt, "worker prompt should mention task-local runtime preparation")
    assert_in("code as a first-class helper", prompt, "worker prompt should encourage code-assisted analysis when useful")
    assert_in("SQLite as a first-class helper", prompt, "worker prompt should describe SQLite guidance for structured workloads")
    assert_in("paths.sqlite_db_path", prompt, "worker prompt should describe SQLite guidance for structured workloads")
    assert_in("vision/image analysis as a first-class helper", prompt, "worker prompt should describe vision guidance for visual workloads")
    assert_in("paths.workspace_screenshots_dir", prompt, "worker prompt should describe vision guidance for visual workloads")

    prepared = json_out(run("prepare-runtime", "--root", str(root), "--id", "task-sched"))
    assert_eq(prepared["status"], "prepared", "prepare-runtime status")
    assert_true(Path(prepared["workspace_dir"]).exists(), "prepare-runtime should create workspace directory")
    assert_true(Path(prepared["workspace_analysis_dir"]).exists(), "prepare-runtime should create workspace/analysis directory")
    assert_true(Path(prepared["workspace_tools_dir"]).exists(), "prepare-runtime should create workspace/tools directory")
    assert_true(Path(prepared["workspace_outputs_dir"]).exists(), "prepare-runtime should create workspace/outputs directory")
    assert_true(Path(prepared["workspace_screenshots_dir"]).exists(), "prepare-runtime should create workspace/outputs/screenshots directory")
    assert_true(Path(prepared["workspace_vision_dir"]).exists(), "prepare-runtime should create workspace/outputs/vision directory")
    assert_true(prepared["sqlite_ready"], "prepare-runtime should mark SQLite helper as ready")
    assert_true(Path(prepared["default_sqlite_db_path"]).exists(), "prepare-runtime should create the task-local SQLite DB")
    assert_true(Path(prepared["sqlite_queries_dir"]).exists(), "prepare-runtime should create SQLite queries directory")
    assert_true(Path(prepared["sqlite_schema_path"]).exists(), "prepare-runtime should materialize a SQLite bootstrap schema file")
    assert_true(Path(prepared["python"]).exists(), "prepare-runtime should provision a runnable Python interpreter")
    sqlite_probe = subprocess.run(
        [prepared["python"], "-c",
         f"import sqlite3; conn=sqlite3.connect({prepared['default_sqlite_db_path']!r}); "
         "tables=[r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name\")]; "
         "assert '_rm_meta' in tables; print('sqlite-ok')"],
        capture_output=True, text=True, cwd=str(Path(prepared["task_dir"])), check=True,
    )
    assert_true(sqlite_probe.stdout.strip() == "sqlite-ok", "SQLite bootstrap schema should be queryable from task runtime")
    probe = subprocess.run(
        [prepared["python"], "-c", "from pathlib import Path; Path('workspace/probe.txt').write_text('ok', encoding='utf-8'); print('ok')"],
        capture_output=True, text=True, cwd=str(Path(prepared["task_dir"])), check=True,
    )
    assert_true(probe.stdout.strip() == "ok", "task runtime probe should succeed")
    assert_true((Path(prepared["task_dir"]) / "workspace" / "probe.txt").exists(), "task runtime probe should be able to create workspace files")


def test_start_and_list(root: Path) -> None:
    started = json_out(
        run("start", "--root", str(root), "--id", "task-c", "--goal", "Self-test start command", "--title", "Task C", "--no-schedule")
    )
    assert_eq(started["status"], "created", "start --no-schedule status")
    assert_eq(started["id"], "task-c", "start should preserve explicit id")
    listed = json_out(run("list", "--root", str(root)))
    listed_ids = {task.get("id") for task in listed.get("tasks", [])}
    assert_true("task-c" in listed_ids, "list should include the started task")


def test_deduplication(root: Path) -> None:
    json_out(run("create", "--root", str(root), "--id", "task-e", "--goal", "Dedupe test"))
    lease_e1 = json_out(run("begin", "--root", str(root), "--id", "task-e"))
    res_e1 = Path(lease_e1["paths"]["result_file"])
    res_e1.parent.mkdir(parents=True, exist_ok=True)
    res_e1.write_text(
        json.dumps({"summary": "Iteration 1", "phase": "search", "sources": [{"url": "https://dup.com", "title": "Dup Source"}], "findings": [{"text": "Dup finding"}], "notify_recommendation": "silent"}),
        encoding="utf-8",
    )
    run("finish", "--root", str(root), "--id", "task-e", "--run-id", lease_e1["run_id"], "--result-file", str(res_e1))

    lease_e2 = json_out(run("begin", "--root", str(root), "--id", "task-e"))
    res_e2 = Path(lease_e2["paths"]["result_file"])
    res_e2.write_text(
        json.dumps({"summary": "Iteration 2", "phase": "search", "sources": [{"url": "https://dup.com", "title": "Dup Source"}, {"url": "https://new.com"}], "findings": [{"text": "Dup finding"}, {"text": "New finding"}], "notify_recommendation": "silent"}),
        encoding="utf-8",
    )
    run("finish", "--root", str(root), "--id", "task-e", "--run-id", lease_e2["run_id"], "--result-file", str(res_e2))

    summary_e = json_out(run("summary", "--root", str(root), "--id", "task-e", "--format", "json"))
    assert_eq(summary_e["totals"]["sources"], 2, "sources should be deduped (1 old + 1 new)")
    assert_eq(summary_e["totals"]["findings"], 2, "findings should be deduped (1 old + 1 new)")

    draft_md = run("draft-report", "--root", str(root), "--id", "task-e", "--format", "markdown").stdout
    assert_in("# Draft report — task-e", draft_md, "draft report should render markdown title")
    assert_in("Dup finding", draft_md, "draft report should include accumulated findings")
    assert_in("New finding", draft_md, "draft report should include accumulated findings")
    assert_in("https://dup.com", draft_md, "draft report should include accumulated sources")
    assert_in("https://new.com", draft_md, "draft report should include accumulated sources")

    draft_json = json_out(run("draft-report", "--root", str(root), "--id", "task-e", "--format", "json"))
    assert_eq(draft_json["totals"]["sources"], 2, "draft json should expose source totals")
    assert_eq(draft_json["totals"]["findings"], 2, "draft json should expose findings totals")


def test_saturation(root: Path) -> None:
    json_out(run("create", "--root", str(root), "--id", "task-f", "--goal", "Saturation test", "--phase", "synthesize"))
    lease_f1 = json_out(run("begin", "--root", str(root), "--id", "task-f"))
    res_f1 = Path(lease_f1["paths"]["result_file"])
    res_f1.write_text(
        json.dumps({"summary": "No new signal in synthesis pass 1.", "phase": "synthesize", "meaningful_progress": False, "sources": [], "findings": [], "notify_recommendation": "silent"}),
        encoding="utf-8",
    )
    fin_f1 = json_out(run("finish", "--root", str(root), "--id", "task-f", "--run-id", lease_f1["run_id"], "--result-file", str(res_f1)))
    assert_eq(fin_f1["status"], "idle", "first low-yield synth pass should stay idle")
    assert_eq(fin_f1["consecutive_low_yield"], 1, "first low-yield pass should increment streak")
    assert_eq(fin_f1["topic_saturated"], False, "first low-yield pass should not saturate yet")

    lease_f2 = json_out(run("begin", "--root", str(root), "--id", "task-f"))
    res_f2 = Path(lease_f2["paths"]["result_file"])
    res_f2.write_text(
        json.dumps({"summary": "No new signal in synthesis pass 2.", "phase": "synthesize", "meaningful_progress": False, "sources": [], "findings": [], "notify_recommendation": "silent"}),
        encoding="utf-8",
    )
    fin_f2 = json_out(run("finish", "--root", str(root), "--id", "task-f", "--run-id", lease_f2["run_id"], "--result-file", str(res_f2)))
    assert_eq(fin_f2["status"], "awaiting_review", "topic saturation auto-completion should enter review gate")
    assert_eq(fin_f2["topic_saturated"], True, "second low-yield synth pass should mark saturation")
    assert_true(bool(fin_f2["final_report_path"]), "saturation completion should render final report")
    assert_eq(fin_f2["normalized_reason"], "completed:topic_saturated", "saturation completion should expose normalized terminal reason")
    assert_true(fin_f2["review_gated"], "topic saturation auto-completion should be review-gated")
    state_f = json.loads((root / "task-f" / "state.json").read_text(encoding="utf-8"))
    assert_eq(state_f["delivery"]["review_ready"], True, "topic saturation should mark report review-ready")
    assert_eq(state_f["delivery"]["ready"], False, "topic saturation must not mark report delivery-ready")

    summary_f = json_out(run("summary", "--root", str(root), "--id", "task-f", "--format", "json"))
    assert_eq(summary_f["saturation"]["consecutive_low_yield"], 2, "summary should expose low-yield streak")
    assert_eq(summary_f["saturation"]["topic_saturated"], True, "summary should expose topic saturation")
    assert_eq(summary_f["history"]["last_terminal_reason"], "completed:topic_saturated", "summary should expose last terminal reason")

    draft_f_md = run("draft-report", "--root", str(root), "--id", "task-f", "--format", "markdown").stdout
    assert_in("Topic saturated: yes", draft_f_md, "draft report should expose saturation status")
    final_f = (root / "task-f" / "final-report.md").read_text(encoding="utf-8")
    assert_in("## Final summary", final_f, "final report should render final summary block")
    assert_in("## Metadata", final_f, "final report should render metadata block")
    assert_in("Total findings accumulated", final_f, "final report should include accumulated totals")
    assert_in("Topic saturated: yes", final_f, "final report should include saturation status")


def test_active_task_resolution(root: Path) -> None:
    active_root = root / "active-root"
    active_root.mkdir(parents=True, exist_ok=True)
    json_out(run("create", "--root", str(active_root), "--id", "active-1", "--goal", "Active task resolution"))
    status_active = run("status", "--root", str(active_root), "--format", "text").stdout
    assert_in("Resolved active task automatically.", status_active, "status should disclose implicit active-task resolution")
    assert_in("Research: active-1", status_active, "status should resolve the only active task")
    summary_active = run("summary", "--root", str(active_root), "--format", "text").stdout
    assert_in("Resolved active task automatically.", summary_active, "summary should disclose implicit active-task resolution")
    assert_in("Research: active-1", summary_active, "summary should resolve the only active task")
    stopped_active = json_out(run("stop", "--root", str(active_root)))
    assert_eq(stopped_active["status"], "cancelled", "stop should resolve the only active task")
    assert_eq(stopped_active["normalized_reason"], "stopped:user", "implicit stop should preserve normalized reason")

    run("create", "--root", str(active_root), "--id", "active-2", "--goal", "Ambiguous active task A")
    run("create", "--root", str(active_root), "--id", "active-3", "--goal", "Ambiguous active task B")
    ambiguous = run("status", "--root", str(active_root), check=False)
    assert_true(ambiguous.returncode != 0, "ambiguous active task resolution should fail")
    assert_in("Multiple active research tasks found", ambiguous.stderr, "ambiguous error should mention explicit id/path")


def test_begin_on_terminal_states(root: Path) -> None:
    json_out(run("create", "--root", str(root), "--id", "task-term-complete", "--goal", "Terminal complete test", "--phase", "synthesize"))
    lease = json_out(run("begin", "--root", str(root), "--id", "task-term-complete"))
    res = Path(lease["paths"]["result_file"])
    res.write_text(
        json.dumps({"summary": "Done.", "phase": "synthesize", "meaningful_progress": False, "sources": [], "findings": [], "notify_recommendation": "silent"}),
        encoding="utf-8",
    )
    run("finish", "--root", str(root), "--id", "task-term-complete", "--run-id", lease["run_id"], "--result-file", str(res))
    lease2 = json_out(run("begin", "--root", str(root), "--id", "task-term-complete"))
    res2 = Path(lease2["paths"]["result_file"])
    res2.write_text(
        json.dumps({"summary": "Done2.", "phase": "synthesize", "meaningful_progress": False, "sources": [], "findings": [], "notify_recommendation": "silent"}),
        encoding="utf-8",
    )
    run("finish", "--root", str(root), "--id", "task-term-complete", "--run-id", lease2["run_id"], "--result-file", str(res2))
    json_out(run("approve", "--root", str(root), "--id", "task-term-complete"))

    begin_complete = json_out(run("begin", "--root", str(root), "--id", "task-term-complete"))
    assert_eq(begin_complete["status"], "complete", "begin should short-circuit on completed tasks")

    json_out(run("create", "--root", str(root), "--id", "task-term-cancel", "--goal", "Terminal cancel test"))
    json_out(run("stop", "--root", str(root), "--id", "task-term-cancel"))
    begin_cancelled = json_out(run("begin", "--root", str(root), "--id", "task-term-cancel"))
    assert_eq(begin_cancelled["status"], "cancelled", "begin should short-circuit on cancelled tasks")


def test_start_no_schedule(root: Path) -> None:
    started_noschedule = json_out(
        run("start", "--root", str(root), "--id", "task-start-local", "--goal", "Start wrapper no-schedule path", "--corpus-mode", "local", "--no-schedule")
    )
    assert_eq(started_noschedule["status"], "created", "start --no-schedule should return create payload")
    assert_eq(started_noschedule["corpus_mode"], "local", "start --no-schedule should preserve corpus mode")
    schedule_dry = json_out(run("schedule", "--root", str(root), "--id", "task-start-local", "--every", "15m", "--dry-run"))
    assert_eq(schedule_dry["status"], "dry-run", "schedule --dry-run should not attempt to create a cron job")
    assert_true(schedule_dry["command"][:3] == ["openclaw", "cron", "add"], "schedule dry-run should show openclaw cron add command")
    assert_in("--no-deliver", schedule_dry["command"], "scheduled worker should keep internal delivery mode")
    assert_in("python3", schedule_dry["prompt"], "schedule dry-run should expose worker prompt")
    assert_in("begin --root", schedule_dry["prompt"], "schedule dry-run should expose worker prompt")


def test_pause_on_corpus_and_begin_paused(root: Path) -> None:
    json_out(run("create", "--root", str(root), "--id", "task-pause-corpus", "--goal", "Pause corpus test", "--corpus-mode", "local"))
    paused = json_out(run("pause", "--root", str(root), "--id", "task-pause-corpus"))
    assert_eq(paused["status"], "paused", "pause should work on idle corpus task")
    begin_paused = json_out(run("begin", "--root", str(root), "--id", "task-pause-corpus"))
    assert_eq(begin_paused["status"], "paused", "begin should not lease paused corpus task")
    resumed = json_out(run("resume", "--root", str(root), "--id", "task-pause-corpus"))
    assert_eq(resumed["status"], "idle", "resume should restore paused corpus task to idle")
