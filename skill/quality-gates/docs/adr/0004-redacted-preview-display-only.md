# Display-only redacted previews alongside fail-closed quarantine

Advisory-text violations discard the whole assessment (`failed`, empty
observations) while the raw text sits in a human-only quarantine file outside
any live session. That is safe but opaque: the operator cannot tell a benign
`install instructions` rejection from a real exfiltration attempt without
opening the quarantine file outside the session.

## Considered options

- Promote neutralized observations into the result as `partial`. Rejected.
  vowel-masking is reversible obfuscation, the denylist misses real payloads
  (`rm -rf`, `curl | sh` passed validation), and promotion would move attack
  surface from a human-only file into agent context by design.
- Keep `failed` with no observations and add nothing. This is the status quo. Rejection volume stays
  unexplained inside the session.
- Fail-closed machine path plus a display-only neutralized preview in result
  metadata. Chosen. The machine result is unchanged, and the preview lets a
  human understand the flagged content without ingesting trigger keywords,
  shell metacharacters, raw URLs, or command payloads.

**Consequences:**

- The denylist is intentionally broader than before: raw `://` URLs, `&&`,
  `||`, `;`, spaced pipes, `${`, backslashes, and dangerous verbs with
  targets (`rm -rf …`, `curl https://…`) now fail validation. Bare tool
  mentions (`uses docker for builds`) still pass.
- Preview neutralization is ASCII-only and NFKC-stable (NFKD-folded):
  backticks become quotes, `$(`/`${` are spaced apart, shell chaining becomes
  `[and]`/`[or]`/`[pipe]`/`[semi]`, `://` becomes `[://]`, unsafe verbs become
  category tags (`[setup-action]`, `[instruction]`, `candidate-tool [check]`),
  and command-with-target spans become `[instruction withheld: <verb>]`.
  Preview output re-passes the validator (property-tested).
- Previews are capped (5 observations, 5 uncertainties, 500 chars per span)
  and live only in `metadata.redacted_preview`, never in `observations`,
  logs, or gate mapping. The single bounded repair retry is unchanged and
  still runs on violations; the preview attaches to the final failed result.
- Known limitation: `kubectl apply -f` style bare-subcommand invocations
  (verb followed by a plain word, no flag/path/URL) are not flagged. The
  preview layer still neutralizes any metacharacters or URLs they contain.
