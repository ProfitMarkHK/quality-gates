# What good tests look like

Gate 1 says the suite passes. This reference decides whether passing means
anything. Read it when judging Gate 4 (test quality), when Gate 4b
(state-transition coverage) applies, and whenever the task adds or changes
tests.

## The bar every unit test must clear

**The assertion must be independent of the implementation.** The standing
question: if a realistic bug were introduced, would this test fail? A test
that would still pass is restating the implementation, not testing it.

A good unit test:

- supplies known inputs and asserts exact expected outputs, errors, or side
  effects
- asserts on outputs or on state, not only on "returned without error" or the
  presence of a log line
- covers invalid inputs, missing data, timeouts, and failure paths, not only
  the happy path
- is deterministic: no wall-clock time, no live network, no unseeded
  randomness. Time and randomness arrive through a seam (an injected clock or
  generator) so a failure path can be frozen and replayed
- runs in the suite that executes on every change

A test that counts calls without asserting what was passed to them proves
less than it appears to. If the behaviour is "back off with growing delays"
or "do not fetch again", assert the recorded delays or the recorded call
count, not merely that the code called something.

Full-task tests (end-to-end, acceptance, smoke) are judged differently:
they check the final state of the system with ordinary code, assert
invariants rather than exact step sequences, and may legitimately touch the
live network or record an explicit skip when the environment has no data.
The independence question applies to them unchanged; the other criteria on
this list are unit-test criteria.

## Three failure smells

Each smell looks like coverage but can pass while the behaviour under test is
wrong. All three were found in one real suite that had already passed a
conventional review.

**Circular assertion.** The test computes its expected value with the same
code it is testing, so a wrong formula and a wrong expectation move together
and the test still passes. It proves plumbing at best. Fix: take the expected
value from an independent source, or hardcode a literal computed once by hand
and recorded with its derivation.

**Vacuous pass.** A guard means the test's real assertion never runs. The
usual shape is asserting only when the response is non-empty, or accepting an
empty result as success. The suite passes while proving nothing. Fix: assert
the response is non-empty, or turn "no data" into an explicit skip with a
status visible in the output.

**Masking fixture.** The test's fixture never enters the branch under test, so
wrong behaviour passes as correct. A real example: a pricing formula returned
zero for a degenerate input in every case, but the fixture only used inputs
where zero happened to be the right answer, so the test passed and the bug
shipped. Fix: choose a fixture that discriminates between the correct answer
and the most plausible wrong answer, and say in the test which wrong answer it
would catch.

## Before submitting a test

1. Does it check a deterministic unit of logic, or a full task outcome? Both
   are valid; the assertion style differs.
2. Is the expected value derived independently of the code under test?
3. Name the realistic bug it would catch. If no bug comes to mind, the test is
   decorative.
4. Can a second reviewer verify the expected outcome without reading the
   implementation?
5. If the code retains state across calls, which transition does this test
   enter? (Gate 4b.)

## The state-transition audit (Gate 4b)

Most code that retains state hides implicit state machines: a cache with hit,
miss, and eviction; a cursor that advances and terminates; a retry counter; a
guard that fires; a dedupe set; a freshness stamp; a convergence loop with a
budget. The states are rarely declared anywhere. They are implied by the
code.

The audit:

1. **Enumerate.** List every piece of state the changed code retains across
   calls, and the transitions the code implements around it.
2. **Check entry.** For each transition, either a test enters it, or say why
   it is unreachable. The interesting ones are the failure and edge
   transitions the code explicitly implements: a rejected request evicted so
   the next call retries; the runaway-loop guard firing; a failed fetch
   leaving no cache entry; a newer record not downgraded by a stale one;
   duplicates collapsing; an iteration budget honoured.
3. **Test through observable effects.** State is usually not exposed, so
   assert transitions by what can be observed: call counts, recorded
   arguments, output contents, and order.

The gap pattern this audit exists for: happy-path transitions get tested
naturally, while failure and edge transitions the author took care to
implement go unentered. In the real suite that motivated this gate, the audit
found six implemented but untested transitions in a codebase whose suite had
just passed a test-quality review.

The examples above (cache, cursor, guard, dedupe) are illustrations, not a
checklist. Enumerate the machines the code in front of you actually retains,
and name the transitions in the project's own terms.
