# Soften the advisory-text lexicon for descriptive and hedged prose (AIDEV-548)

The advisory-text validator rejected benign descriptive prose: a live
2026-09-24 quarantine flagged an observation solely for the word
"configured" in "configured via a hardcoded base URL". This describes
how something is set up, not a claim about tool state. Any useful
observation about gateway or config setup contains "configured", so the
rule banned the topic rather than the claim.

## Considered options

- Keep the lexicon as-is. Rejected because false positives on ordinary
  descriptive prose burn the single repair retry and fail closed.
- Drop the whole installed/configured/passing alternation. Rejected because
  "installed" and "passing" assert runtime state the model cannot verify.
- Allow descriptive "configured" and single-word hedged predicates
  ("appears/seems (to be) X"). Chosen. "Configured" describes static
  config presence verifiable from cited material; hedges are explicitly
  not claims. The single-word bound is load-bearing: "appears to be
  passing" passes, but "appears to be configured and passing" still fails
  on the unmasked "passing", so the hedge cannot launder compound claims.
- Downgrade lexicon hits to repair-eligible instead of fail-closed.
  rejected; bigger design change, out of scope.

**Consequences:**

- `_validate_advisory_text` masks hedged single-word predicates before the
  lexical checks and no longer denylists "configured". The redaction
  neutralizer shows "configured" plainly for the same reason.
- Residual risk accepted: hedged "passing" now passes. Mitigations already
  in place: source references still required, redacted previews surface
  these to the human, repair and fail-closed paths unchanged.
