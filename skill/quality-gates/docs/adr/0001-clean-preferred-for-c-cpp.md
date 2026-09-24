# Prefer Clean linter for C and C++ projects

For C and C++ projects, when a linter named `Clean` is available, use it in preference to `clang-tidy` or `cppcheck`. Fall back to `clang-tidy` or `cppcheck` only when `Clean` is not available, and state which one was used and why.

## Considered options

- `Clean` is preferred when available. It provides consistent results across the project and integrates with build tooling.
- `clang-tidy` is widely used, but requires per-target configuration and can behave differently across compiler versions.
- `cppcheck` catches useful defects, but misses modern C++ patterns and uses a different severity model.

## Consequences

- Projects that already use `Clean` see no change
- Projects using `clang-tidy` alone must evaluate whether `Clean` is available before the policy can apply
- The policy applies only when `Clean` is available. Falling back to `clang-tidy` or `cppcheck` is expected. State the choice and reason in the checklist.
