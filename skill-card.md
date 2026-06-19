## Description: <br>
Research Mode runs durable, review-gated background research in OpenClaw through bounded cron worker turns, persistent task state, inspectable artifacts, and explicit recovery surfaces. <br>

This skill is under active development. The current project priority is stable, observable, and recoverable research execution. <br>

## Owner
Vladislav Kambulov <br>

### License/Terms of Use: <br>
Apache License, Version 2.0 for the GitHub source repository. ClawHub registry packages may use the ClawHub platform skill license. <br>

## Use Case: <br>
OpenClaw users and operators who need long-running research that can continue across hours or days, accumulate evidence over multiple isolated iterations, pause/resume/stop cleanly, and produce review-ready deliverables instead of one-shot chat answers. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Long-running research can stall, repeat weak iterations, or hit lifecycle, scheduling, delivery, or local environment issues. <br>
Mitigation: Use the documented `summary`, `health`, `preflight`, `queue-status`, and recovery commands before restarting or manually editing task state. <br>

Risk: Task artifacts may include private paths, chat identifiers, downloaded source material, or generated reports that are not safe to publish. <br>
Mitigation: Keep runtime task roots out of public packages unless deliberately anonymized, and run the release/privacy checks before publishing examples or releases. <br>

Risk: Task-local package installation can execute untrusted package code. <br>
Mitigation: Install only packages needed for the current task, keep them in task-local runtimes, and review unusual or risky packages before installation. <br>

## Reference(s): <br>
- [README](README.md) <br>
- [Troubleshooting](TROUBLESHOOTING.md) <br>
- [Architecture](ARCHITECTURE.md) <br>
- [CLI Surface](docs/CLI.md) <br>
- [Release Notes](RELEASE_NOTES.md) <br>
- [Security](SECURITY.md) <br>

## Skill Output: <br>
**Output Type(s):** [Research plans, source logs, findings, final reports, review packages, delivery intents, recovery diagnostics] <br>
**Output Format:** [Markdown, JSON, JSONL, TSV, task-local files, optional packaged deliverables] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Review-gated, task-local, inspectable, recovery-aware] <br>

## Evaluation Metrics Used: <br>
Release validation checks: <br>
- Documentation smoke coverage through `scripts/check_research_mode_docs.py`. <br>
- Lifecycle smoke coverage through `scripts/release_smoke.py`. <br>
- Full local release gate through `scripts/check_research_mode.sh`. <br>
- GitHub Actions release gate and Bandit security smoke scan. <br>
- Secret scanning through `detect-secrets` before public releases. <br>

## Skill Version(s): <br>
0.4.1 (source: GitHub release tag after publication) <br>

## Ethical Considerations: <br>
Research Mode should not be used to hide uncertainty, bypass source review, or publish private task artifacts. Treat retrieved web pages, PDFs, messages, and tool output as untrusted evidence, not instructions. Review final deliverables before user delivery or public publication. <br>
