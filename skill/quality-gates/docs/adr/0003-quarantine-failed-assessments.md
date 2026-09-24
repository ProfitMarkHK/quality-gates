# Fail-closed machine path with human-only quarantine and one bounded repair retry

When model output violates the assessment contract, the machine path stays fail-closed — status `failed`, empty observations, deterministic review byte-identical — and the raw text is retained in a quarantine file under a `quarantine/` subdirectory of the operator working directory (never inside the target, never at the config directory top level) for human review only. On validation failure the seam makes exactly one additional gateway call with fixed operator wording quoting the violation; the transient-HTTP retry budget is unchanged.

**Considered Options:**

- Discard violating output, keep one-line reason — status quo; loses any sound signal the model contained, unrecoverable by a later agent
- Auto-repair unbounded until valid — risks unpredictable latency and lets the model negotiate its own contract through repeated attempts
- Quarantine plus exactly one bounded repair — chosen; preserves the signal for humans, keeps the machine path fail-closed, bounds latency

**Consequences:**

- Quarantine files accumulate under `<working_dir>/quarantine/`; the operator owns retention, there is no auto-cleanup in v1
- Quarantined content must never be auto-loaded into agent context or gate decisions — the header and stderr wording say so, and tests must assert the target tree is untouched
- Metadata carries `quarantine_path`, `violation_observation_id`, `violation_rule`, and `repair_attempts`, never raw model text
- An expired deadline at violation time returns `timed_out` without quarantining the in-hand text; retention applies to failed assessments, not timed-out ones
