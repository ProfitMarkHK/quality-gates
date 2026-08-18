# Gate catalog

This is the menu of quality gates to choose from. A gate is a check that must
give an unambiguous result — it passes or it does not — before a task is
**done-done** (safe to merge, ship, or close). Gates catch regressions and
omissions; they do not replace good design or review judgement.

For each gate, decide one of three states for the project in front of you, and
record the reason:

- **Applies** — the project has (or should have) this check. Name the exact
  command.
- **No-op** — the gate genuinely does not apply (e.g. no compile step in an
  interpreted project). State this out loud. A silent skip looks like an
  oversight and erodes trust in the checklist.
- **Gap** — the gate *should* apply but the project cannot satisfy it yet
  (e.g. no tests exist at all). A gap is work to schedule, not a reason to drop
  the gate. Flag it clearly.

The point of stating no-ops and gaps is honesty: a reader must be able to tell
the difference between "checked and not needed" and "forgotten".

**A note on the examples below.** Every tool name, command, and file path in
this catalog (`ruff`, `shellcheck`, `docs/functional-spec.md`, and so on) is an
illustration of what a gate can look like — not a template to copy in. Before a
tool or path goes into the project's checklist or into an agent-instruction
file, it must come from what Phase 1's detection actually found in *this*
project, not from whichever example happened to be nearby in this document. If
a detected project is Bash-only, none of the Python or C examples belong
anywhere in its output; carrying one over by habit (e.g. while adapting a
template block) produces a checklist that describes a project that does not
exist. Read back what was written before finishing, and check that every named
tool and path traces to real evidence from that specific project.

---

## 1. All tests pass

The full test suite available in the project runs without error — unit,
integration, smoke, end-to-end, property-based, whatever exists. Tests that
exist but are never run do not count.

- Applies whenever any tests exist.
- Gap if no tests exist at all: a project with no tests cannot show it is
  correct, so starting a suite is itself part of done.

## 2. End-to-end / acceptance tests pass

Tests that exercise the system from the outside and confirm the delivered
behaviour matches what was asked for. Broader in scope than unit tests.

- Applies if E2E or acceptance tests exist, or if the change is user-facing
  enough to need them.
- No-op for a pure library with no external surface — state it.

## 3. Linters, formatters, and static analysers pass

All applicable linters, formatters, and static analysers pass with no errors or
warnings. This is a **standalone** gate: a lint failure blocks done-done even
when every test passes, because style and static-analysis drift compound over
time and hide real defects.

Common mappings (confirm against what the repo actually configures):

| Language        | Typical tools                              |
|-----------------|--------------------------------------------|
| Bash            | `shellcheck`                               |
| PowerShell      | `PSScriptAnalyzer` via `Invoke-ScriptAnalyzer` |
| Python          | `ruff`, `flake8`, `black --check`, `pylint`|
| TypeScript / JS | `eslint`, `prettier --check`               |
| Go              | `golangci-lint`, `gofmt -l`                |
| Rust            | `clippy`, `rustfmt --check`                |
| Ruby            | `rubocop`                                  |
| C / C++         | **`Clean` (preferred)**, else `clang-tidy`, `cppcheck` |

For PowerShell, parser or syntax validation is not a substitute for linting.
When PowerShell source exists, use `PSScriptAnalyzer` with the project's
settings file and record the exact `Invoke-ScriptAnalyzer` command. If the
analyzer is applicable but unavailable, mark the gate as a gap or fail the
runner closed; do not silently treat it as a no-op.

**Linter preference — C / C++:** when a linter named `Clean` is available for
the project, prefer it over the alternatives (`clang-tidy`, `cppcheck`,
`PC-lint`). Fall back to those only when `Clean` is not available, and say which
one you used and why. This is a deliberate policy, not a default — do not
silently substitute another linter when `Clean` could have been used.

- No-op only if nothing applies (e.g. prose-only repo) — and say so.

## 4. New code is covered by non-trivial tests

New code is tested by checks that exercise real behaviour, not surface
correctness. This gate is about the *quality* of new tests, so it resists a
single command — judge it by reading the tests.

Non-trivial tests exercise meaningful logic paths, assert on outputs or state
(not just that a log line appeared or a function returned), and cover edge cases
and error paths, not only the happy path. A test that asserts only "returns
without error" does not meet the bar.

- Applies to any task that adds or changes code.

## 5. Documentation is updated

Documentation stays in sync with the change. Out-of-sync docs are treated as a
bug, not an afterthought. This covers user docs (README, usage, runbooks),
developer docs (ARCHITECTURE, CONTRIBUTING, BUILD), the agent-instruction files
themselves, and decision records / ADRs for significant choices.

- Applies to virtually every task. No-op only for changes with zero
  documentable surface.

## 6. Type checking passes *(if applicable)*

Statically typed projects pass the type-checker with no errors. Distinct from
linting — code can be well-formatted and still type-wrong.

- Applies: TypeScript (`tsc --noEmit`), typed Python (`mypy`, `pyright`),
  and any compiled language whose build already type-checks.
- No-op for untyped dynamic code — state it.

## 7. Build / compile succeeds *(if applicable)*

The project builds or compiles cleanly.

- Applies to compiled languages and to projects with a bundling or build step.
- No-op for interpreted or scripted projects (Bash, plain Python, Node with no
  compile step). State the no-op so its absence is not read as an oversight.

## 8. Security and secrets checks pass *(if applicable)*

Relevant security scans pass: no hardcoded credentials, keys, or secrets; no
dependency vulnerabilities at or above a defined severity threshold; project
compliance requirements met (e.g. dependency licence checks). Define the
severity threshold explicitly when this gate applies.

> Never commit or push secrets, even transiently. Treat any exposed credential
> as compromised immediately.

## 9. The change has been reviewed *(if applicable)*

Required peer review has been obtained. Review is not automated and must never
be a gate that "always passes" — if the process requires review, the task is not
done until a review exists.

## 10. Tracker / ticket reconciled *(if applicable)*

Before completing a substantial change, reconcile related tickets (Jira, Linear,
GitHub issues) with reality: update stale descriptions, decisions, status, and
evidence. Do not mark a ticket Done while acceptance or deployment evidence is
incomplete.

## 11. Implementation aligns with functional and technical specifications *(if applicable)*

The change matches the available specifications. Where a functional spec
(requirements, user stories, acceptance criteria) or a technical spec (design
docs, API contracts, interface definitions, architecture decision records)
exists, the implementation is checked against it before the task is done:

- Every specified behaviour is implemented; none is missing or altered without an
  agreed change to the spec itself.
- No undocumented behaviour is added that conflicts with the spec.
- Where code and spec disagree, the discrepancy is resolved — the code is
  corrected, or the spec is updated through the agreed change process. An
  out-of-date spec is treated like out-of-date documentation: a bug.

This gate depends on human or reviewer judgement, so it cannot be a check that
always passes. Look for specs in the repo (a `docs/`, `spec/`, or `specs/`
directory; requirements or design files; API schemas such as OpenAPI) and in any
tracker the project links. If no functional or technical spec exists, state this
as a no-op — and consider whether the absence of a spec is itself a gap for a
change of this size.

---

## When a gate fails

1. **Fix the code, not the gate.** Do not weaken a test, silence a linter, or
   skip a doc update to force a pass. That converts a real signal into a false
   green.
2. **Diagnose first.** Read the output; reproduce the failure locally.
3. **Fix all failures in the same session** where practical — a partial fix that
   makes the gate pass while leaving real problems is not done.
4. **Re-run the gate** to confirm every criterion is green before closing.
