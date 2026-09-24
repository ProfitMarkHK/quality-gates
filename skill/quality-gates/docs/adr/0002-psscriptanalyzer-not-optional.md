# PSScriptAnalyzer is not optional when PowerShell source exists

When a project contains `.ps1`, `.psm1`, or `.psd1` files, run the linter gate with `PSScriptAnalyzer` through `Invoke-ScriptAnalyzer`. Parser validation and syntax checking do not replace linting. If `PSScriptAnalyzer` is unavailable, mark the gate as a gap and recommend installing it. Do not mark it as a no-op.

## Considered options

- `PSScriptAnalyzer` is strongly recommended. It catches script logic issues, unused variables, and style violations that parser validation misses.
- Parser or syntax validation alone is insufficient. It confirms syntax but says nothing about script quality, cmdlet usage, or security anti-patterns.
- Omitting linting is not acceptable. Style and quality problems accumulate without a linter.

## Consequences

- The gate is marked as a gap with a clear recommendation to install `PSScriptAnalyzer`; the gate does not hard-fail when the tool is absent
- The exact `Invoke-ScriptAnalyzer` invocation and the settings file used must be recorded in the checklist
- Do not relax the policy to "parser validation suffices". That would turn the quality gate into a no-op.
