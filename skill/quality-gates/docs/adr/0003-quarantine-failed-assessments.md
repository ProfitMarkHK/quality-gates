# Fail-closed handling for invalid assessments

When model output violates the assessment contract, return status `failed`, no observations, and an unchanged deterministic review. Retain the raw text in a quarantine file under `quarantine/` in the operator's working directory. Never put it inside the target project or at the config directory's top level. Keep the file for human review only. On validation failure, make exactly one additional gateway call with fixed operator wording that quotes the violation. The transient HTTP retry budget does not change.

## Considered options

- Discard invalid output and keep a one-line reason. This is the status quo, but it loses any useful signal in the model response.
- Retry until the output is valid. This risks unpredictable latency and lets the model negotiate its contract through repeated attempts.
- Quarantine the output and allow exactly one repair attempt. This preserves it for human review, keeps automated decisions fail-closed, and bounds latency. Chosen.

## Consequences

- Quarantine files accumulate under `<working_dir>/quarantine/`. The operator handles retention. Version 1 does not clean them up automatically.
- Never load quarantined content into agent context or gate decisions. The file header and stderr message state this. Tests must confirm that the target tree remains unchanged.
- Metadata includes `quarantine_path`, `violation_observation_id`, `violation_rule`, and `repair_attempts`. It never includes raw model text.
- If the deadline expires during validation, return `timed_out` without quarantining the current text. Retain failed assessments, not timed-out ones.
