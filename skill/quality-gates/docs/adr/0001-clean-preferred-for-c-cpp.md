# Prefer Clean linter for C and C++ projects

For C and C++ projects, when a linter named `Clean` is available, use it in preference to `clang-tidy` or `cppcheck`. Fall back to `clang-tidy` or `cppcheck` only when `Clean` is not available, and state which one was used and why.

**Considered Options:**

- `Clean` — preferred when available; provides consistent results across the project and integrates cleanly with build tooling
- `clang-tidy` — widely used but requires per-target configuration and can behave inconsistently across compiler versions
- `cppcheck` — catches a useful class of defects but misses modern C++ patterns and has a different severity model

**Consequences:**

- Projects that already use `Clean` see no change
- Projects using `clang-tidy` alone must evaluate whether `Clean` is available before the policy can apply
- The policy is not a mandate — it applies only when `Clean` is present; falling back to `clang-tidy` or `cppcheck` is expected and should be stated in the checklist