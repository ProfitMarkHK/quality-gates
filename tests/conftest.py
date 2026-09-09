"""Pytest-only hermetic guard for operator LLM configuration.

Unit tests assume a clean operator environment; a real exported
QUALITY_GATES_LLM_* configuration (needed for the opt-in live smoke test)
would otherwise leak into env-sensitive tests such as the config-directory
refusal test. When the live smoke test is NOT opted in, strip operator LLM
vars for every test. The live module keeps its real env (it skips without
it), so run it separately with the operator environment present.
"""

import os

import pytest

PREFIX = "QUALITY_GATES_LLM_"
LIVE_FLAG = "QUALITY_GATES_LIVE_SMOKE"
LIVE_MODULE = "test_llm_assessment_live"


@pytest.fixture(autouse=True)
def _hermetic_operator_env(request, monkeypatch):
    if request.node.module.__name__ == LIVE_MODULE:
        return
    if os.environ.get(LIVE_FLAG) == "1":
        for key in [k for k in os.environ if k.startswith(PREFIX)]:
            monkeypatch.delenv(key, raising=False)
