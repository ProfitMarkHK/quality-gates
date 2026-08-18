# PSScriptAnalyzer is not optional when PowerShell source exists

When the project contains `.ps1`, `.psm1`, or `.psd1` files, the linter gate uses `PSScriptAnalyzer` via `Invoke-ScriptAnalyzer`. Parser validation or syntax checking does not satisfy the linter gate — they are not substitutes. If `PSScriptAnalyzer` is not available, the linter gate is marked as a gap and the project is flagged with a strong recommendation to install it; it is not treated as a no-op.

**Considered Options:**

- `PSScriptAnalyzer` — strongly recommended; catches script logic issues, unused variables, and style violations that parser validation misses entirely
- Parser or syntax validation only — insufficient; confirms the script is syntactically valid but says nothing about script quality, cmdlet usage, or security anti-patterns
- No linting — not acceptable; style and quality drift compound silently without a linter

**Consequences:**

- The gate is marked as a gap with a clear recommendation to install `PSScriptAnalyzer`; the gate does not hard-fail when the tool is absent
- The exact `Invoke-ScriptAnalyzer` invocation and the settings file used must be recorded in the checklist
- The policy cannot be relaxed to "parser validation suffices" — that would silently downgrade the gate to a no-op for quality