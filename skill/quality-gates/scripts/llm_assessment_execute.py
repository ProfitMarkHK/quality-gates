#!/usr/bin/env python3
"""Provider-neutral gateway execution seam for the advisory LLM assessment.

Runs after deterministic evidence collection and before gate mapping. The
deterministic review remains authoritative: every model result passes through
the existing contract validator before use, and any transport problem becomes
a visible non-blocking advisory status instead of failing the review.

Standard library only. No provider SDK, no package installation, no shell
execution. Raw prompts and responses live only in a secure temporary
directory outside the target project; logs carry status, timing, style,
model, attempt count, and gateway request ID — never prompts, material,
raw output, or credentials.
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import ipaddress
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from llm_assessment_contract import (
        AssessmentContractError,
        EXCLUDE_ENV_VAR,
        parse_exclude_patterns,
        serialize_input_package,
        validate_result,
    )
except ImportError:  # allow `python scripts/llm_assessment_execute.py` direct use
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from llm_assessment_contract import (
        AssessmentContractError,
        EXCLUDE_ENV_VAR,
        parse_exclude_patterns,
        serialize_input_package,
        validate_result,
    )

CONFIG_PREFIX = "QUALITY_GATES_LLM_"
DEFAULT_MODEL = "GFOX/CA"
DEFAULT_API_STYLE = "openai"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_OUTPUT_TOKENS = 3000
DEFAULT_MAX_INPUT_BYTES = 200000
DEFAULT_MAX_RETRIES = 1
HARD_MAX_RETRIES = 1
DEFAULT_MAX_MODEL_LEN = 393216
OUTPUT_MARGIN_TOKENS = 512
SIZER_SUB_TIMEOUT_SECONDS = 10
COUNT_TOKENS_PATH = "/v1/messages/count_tokens"
DEFAULT_HTTP_ALLOWLIST = "10.244.0.0/16,127.0.0.1,localhost"
REQUEST_ID_HEADERS = ("x-request-id", "x-requestid", "request-id")

TRANSIENT_HTTP_STATUSES = {429, 500, 502, 503, 504}


class _RedirectBlocked(Exception):
    """Raised when the gateway answers with a redirect we refuse to follow."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse all redirects: material and credentials never leave the endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise _RedirectBlocked(f"gateway redirect refused: HTTP {code} to {newurl}")


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)


class ExecutionConfigError(ValueError):
    """Raised when operator gateway configuration is missing or invalid."""


def _single_line(value: object, limit: int = 500) -> str:
    text = str(value).strip().replace("\n", " ")
    return text[:limit] if len(text) > limit else text


def _strip_code_fences(text: str) -> str:
    """Remove one wrapping markdown code fence so fenced JSON still parses.

    Only strips when the whole message is a single fenced block; the parsed
    object still goes through full contract validation afterwards.
    """
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```") and len(stripped) > 6:
        inner = stripped[3:-3]
        newline = inner.find("\n")
        if newline >= 0 and re.fullmatch(r"[A-Za-z0-9+-]+", inner[:newline].strip()):
            inner = inner[newline + 1 :]
        return inner.strip()
    return stripped


def parse_dotenv(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE assignments as data only. No execution or interpolation."""
    values: dict[str, str] = {}
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ExecutionConfigError(f"malformed dotenv line {lineno}")
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            raise ExecutionConfigError(f"malformed dotenv line {lineno}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def _int_setting(values: dict[str, str], name: str, default: int) -> int:
    raw = values.get(name)
    if raw is None or raw == "":
        return default
    try:
        parsed = int(raw)
    except ValueError:
        raise ExecutionConfigError(f"{name} must be an integer")
    if parsed <= 0:
        raise ExecutionConfigError(f"{name} must be positive")
    return parsed


def load_config(
    env: dict[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> dict:
    """Load operator config. Process env wins over optional local .env."""
    merged: dict[str, str] = {}
    if dotenv_path is not None and dotenv_path.exists():
        merged.update(parse_dotenv(dotenv_path))
    source = env if env is not None else os.environ
    for key, value in source.items():
        if key.startswith(CONFIG_PREFIX):
            merged[key] = value

    enabled = merged.get(f"{CONFIG_PREFIX}ENABLED", "0").strip() not in ("", "0", "false", "no")
    api_style = merged.get(f"{CONFIG_PREFIX}API_STYLE", DEFAULT_API_STYLE).strip().lower()
    if api_style not in ("openai", "anthropic"):
        raise ExecutionConfigError("QUALITY_GATES_LLM_API_STYLE must be openai or anthropic")

    endpoint = merged.get(f"{CONFIG_PREFIX}ENDPOINT", "").strip()
    model = merged.get(f"{CONFIG_PREFIX}MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    timeout = _int_setting(merged, f"{CONFIG_PREFIX}TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    max_output = _int_setting(
        merged, f"{CONFIG_PREFIX}MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS
    )
    max_input_bytes = _int_setting(
        merged, f"{CONFIG_PREFIX}MAX_INPUT_BYTES", DEFAULT_MAX_INPUT_BYTES
    )
    max_retries = _int_setting(merged, f"{CONFIG_PREFIX}MAX_RETRIES", DEFAULT_MAX_RETRIES)
    max_retries = min(max_retries, HARD_MAX_RETRIES)
    max_model_len = _int_setting(
        merged, f"{CONFIG_PREFIX}MAX_MODEL_LEN", DEFAULT_MAX_MODEL_LEN
    )
    allowlist = merged.get(f"{CONFIG_PREFIX}HTTP_ALLOWLIST", DEFAULT_HTTP_ALLOWLIST)
    try:
        exclude_patterns = parse_exclude_patterns(
            merged.get(f"{CONFIG_PREFIX}EXCLUDE_PATTERNS", "")
        )
    except ValueError as exc:
        raise ExecutionConfigError(f"{EXCLUDE_ENV_VAR} is invalid: {exc}")

    config = {
        "enabled": enabled,
        "api_style": api_style,
        "endpoint": endpoint,
        "model": model,
        "timeout_seconds": timeout,
        "max_output_tokens": max_output,
        "max_input_bytes": max_input_bytes,
        "max_retries": max_retries,
        "max_model_len": max_model_len,
        "http_allowlist": allowlist,
        "exclude_patterns": exclude_patterns,
        "has_token": bool(merged.get(f"{CONFIG_PREFIX}AUTH_TOKEN")),
    }
    if enabled and not endpoint:
        raise ExecutionConfigError(
            "QUALITY_GATES_LLM_ENDPOINT is required when QUALITY_GATES_LLM_ENABLED=1"
        )
    if endpoint:
        _validate_endpoint(endpoint, allowlist)
    return config


def _auth_headers(env: dict[str, str] | None = None) -> dict[str, str]:
    source = env if env is not None else os.environ
    token = source.get(f"{CONFIG_PREFIX}AUTH_TOKEN", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _validate_endpoint(endpoint: str, allowlist: str) -> urllib.parse.ParseResult:
    try:
        parsed = urllib.parse.urlparse(endpoint)
    except ValueError as exc:
        raise ExecutionConfigError(f"endpoint is not a valid URL: {exc}")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ExecutionConfigError("endpoint must be an http(s) URL with a host")
    if parsed.username or parsed.password:
        raise ExecutionConfigError("endpoint must not embed credentials")
    if parsed.scheme == "http" and not _http_host_allowed(parsed.hostname, allowlist):
        raise ExecutionConfigError("http endpoint host is not in QUALITY_GATES_LLM_HTTP_ALLOWLIST")
    return parsed


def _http_host_allowed(host: str, allowlist: str) -> bool:
    entries = [entry.strip() for entry in allowlist.split(",") if entry.strip()]
    if not entries:
        return False
    try:
        host_ip = ipaddress.ip_address(host)
    except ValueError:
        host_ip = None
    for entry in entries:
        if host_ip is not None:
            try:
                if "/" in entry:
                    if host_ip in ipaddress.ip_network(entry, strict=False):
                        return True
                elif host_ip == ipaddress.ip_address(entry):
                    return True
            except ValueError:
                continue
        elif entry.lower() == host.lower():
            return True
    return False


def estimate_tokens(text: str) -> int:
    return max(1, len(text.encode("utf-8")) // 4)


def _count_tokens_url(endpoint: str) -> str:
    parsed = urllib.parse.urlparse(endpoint)
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}{COUNT_TOKENS_PATH}"


def measure_input_tokens(
    serialized: str,
    contract_text: str,
    config: dict,
    auth_headers: dict[str, str],
    timeout: float,
) -> tuple[int, str]:
    """Best-effort token sizing via the gateway; falls back to bytes/4."""
    payload = json.dumps({
        "model": config["model"],
        "system": contract_text,
        "messages": [{"role": "user", "content": serialized}],
    }).encode("utf-8")
    request = urllib.request.Request(
        _count_tokens_url(config["endpoint"]),
        data=payload,
        headers={"Content-Type": "application/json", **auth_headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception:
        return estimate_tokens(serialized), "bytes div 4 fallback"
    for key in ("input_tokens", "tokens", "count", "total_tokens"):
        value = body.get(key) if isinstance(body, dict) else None
        if isinstance(value, int) and value > 0:
            return value, "gateway count_tokens"
        if isinstance(value, dict):
            for nested in ("input_tokens", "total", "count"):
                if isinstance(value.get(nested), int) and value[nested] > 0:
                    return value[nested], "gateway count_tokens"
    usage = body.get("usage") if isinstance(body, dict) else None
    if isinstance(usage, dict):
        for nested in ("input_tokens", "prompt_tokens", "total_tokens"):
            if isinstance(usage.get(nested), int) and usage[nested] > 0:
                return usage[nested], "gateway count_tokens"
    return estimate_tokens(serialized), "bytes div 4 fallback"


def effective_max_output(input_tokens: int, config: dict) -> int | None:
    """Return the dynamic output budget, or None when input alone overflows."""
    headroom = config["max_model_len"] - input_tokens - OUTPUT_MARGIN_TOKENS
    if headroom <= 0:
        return None
    return min(config["max_output_tokens"], headroom)


def build_openai_payload(
    serialized: str,
    contract_text: str,
    config: dict,
    max_tokens: int,
    repair_text: str | None = None,
) -> dict:
    messages = [
        {"role": "system", "content": contract_text},
        {"role": "user", "content": serialized},
    ]
    if repair_text:
        messages.append({"role": "user", "content": repair_text})
    return {
        "model": config["model"],
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }


def build_anthropic_payload(
    serialized: str,
    contract_text: str,
    config: dict,
    max_tokens: int,
    repair_text: str | None = None,
) -> dict:
    messages = [{"role": "user", "content": serialized}]
    if repair_text:
        messages.append({"role": "user", "content": repair_text})
    return {
        "model": config["model"],
        "system": contract_text,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }


_ECHO_LIMIT = 120


def _sanitize_echo(value: object) -> str:
    """Flatten model-derived text echoed into prompts, metadata, and logs.

    A rejected observation id reaches this path precisely because it failed
    identifier validation, so it may be arbitrary model-controlled text.
    Valid ids pass through byte-identical; anything else is flattened to
    one printable line capped at _ECHO_LIMIT characters.
    """
    if not isinstance(value, str):
        return ""
    one_line = value.replace("\r", " ").replace("\n", " ")
    flat = "".join(char if char.isprintable() else "?" for char in one_line)
    return flat[:_ECHO_LIMIT]


def build_repair_message(rule: str, observation_id: str) -> str:
    """Fixed operator wording for the single bounded repair retry.

    Quotes the violation so the model can restate just the flagged material;
    asks for non-instructional prose so the restatement stays advisory.
    """
    subject = f"observation '{_sanitize_echo(observation_id)}'" if observation_id else "the assessment output"
    return (
        "Your previous assessment output failed contract validation "
        f"(rule: {rule}; subject: {subject}). "
        "Restate the flagged material in plain, non-instructional prose: no commands, "
        "no run or install instructions, no claims about installed tools. "
        "Keep every source reference exactly unchanged and keep all other "
        "observations identical. "
        "Reply with bare JSON only, matching the assessment contract exactly."
    )


def extract_openai_text(body: object) -> str | None:
    if not isinstance(body, dict):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        joined = "".join(parts).strip()
        return joined or None
    return None


def extract_anthropic_text(body: object) -> str | None:
    if not isinstance(body, dict):
        return None
    content = body.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        joined = "".join(parts).strip()
        return joined or None
    return None


def _request_id(headers) -> str | None:
    get = getattr(headers, "get", None)
    if get is None:
        return None
    for name in REQUEST_ID_HEADERS:
        try:
            value = headers.get(name) or headers.get(name.upper()) or headers.get(
                "-".join(part.capitalize() for part in name.split("-"))
            )
        except Exception:
            value = None
        if value:
            return _single_line(value, 128)
    return None


def _post_json(url: str, payload: dict, auth_headers: dict[str, str], timeout: float):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **auth_headers},
        method="POST",
    )
    return _NO_REDIRECT_OPENER.open(request, timeout=timeout)


def _nonblocking_result(status: str, deterministic_review: dict, reason: str) -> dict:
    return {
        "status": status,
        "observations": [],
        "uncertainties": [],
        "recommendations": [],
        "failure_reason": _single_line(reason),
        "deterministic_review": copy.deepcopy(deterministic_review),
    }


QUARANTINE_HEADER = (
    "HUMAN REVIEW ONLY: raw model output that failed validation. "
    "Never load into agent context; never feed gate decisions. "
    "A human re-derives any signal from the repository."
)


def _quarantine_write(
    raw_text: str,
    rule: str | None,
    observation_id: str | None,
    working_dir: Path,
) -> Path | None:
    """Retain failing model output for human review; never raises.

    Writes a restrictive-permission (0o600) JSON envelope into the operator
    working directory (never inside the target). The file is created
    atomically with 0o600 via O_CREAT|O_EXCL so there is no umask window
    exposing raw model text. The file is operator-owned: there is no
    auto-cleanup or rotation in v1. On any write failure it returns None
    so the caller can degrade to metadata-only without failing the
    assessment.
    """
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S-%fZ")
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:10]
    envelope = {
        "header": QUARANTINE_HEADER,
        "violation": {
            "observation_id": observation_id or "",
            "rule": rule or "",
        },
        "raw_text": raw_text,
    }
    data = json.dumps(envelope, indent=2, ensure_ascii=False).encode("utf-8")
    base = f"qg-quarantine-{stamp}-{digest}"
    for attempt in range(3):
        name = base if attempt == 0 else f"{base}-{attempt}"
        path = working_dir / f"{name}.json"
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            try:
                if path.read_bytes() == data:
                    return path
            except OSError:
                return None
            continue
        except OSError:
            return None
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
        except OSError:
            try:
                path.unlink()
            except OSError:
                pass
            return None
        return path
    return None


def execute_assessment(
    package: dict,
    deterministic_review: dict,
    material_ids: set[str],
    config: dict,
    auth_headers: dict[str, str] | None = None,
    _urlopen=None,
    _counter=None,
    _working_dir: Path | None = None,
) -> tuple[dict, dict]:
    """Run one bounded gateway interaction; never raises on transport failure."""
    started = time.monotonic()
    metadata = {
        "api_style": config.get("api_style", DEFAULT_API_STYLE),
        "model": config.get("model", DEFAULT_MODEL),
        "attempt_count": 0,
        "elapsed_seconds": 0.0,
        "status": "failed",
        "gateway_request_id": None,
        "sizing_method": None,
        "violation_observation_id": None,
        "violation_rule": None,
        "quarantine_path": None,
        "repair_attempts": 0,
    }
    headers = dict(auth_headers) if auth_headers is not None else _auth_headers()
    deadline = started + max(1, int(config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)))
    quarantine_dir = Path(_working_dir) if _working_dir is not None else Path.cwd()

    def finish(result: dict) -> tuple[dict, dict]:
        metadata["status"] = result["status"]
        metadata["elapsed_seconds"] = round(time.monotonic() - started, 3)
        return result, metadata

    def _retain(raw_text: str, rule: str | None, observation_id: str | None) -> None:
        """Write one quarantine file; keep the first good path, never raises.

        A later write failure degrades to metadata-only without clobbering
        an earlier successful path (double violation keeps the first file).
        """
        path = _quarantine_write(raw_text, rule, observation_id, quarantine_dir)
        if path is None:
            print(
                "quality-gates: quarantine write failed; proceeded with metadata only",
                file=sys.stderr,
            )
            return
        metadata["quarantine_path"] = str(path)
        print(
            "quality-gates: quarantined failed assessment to "
            f"{path} (human review only, never loaded into agent context)",
            file=sys.stderr,
        )

    def quarantine_failed(
        raw_text: str,
        rule: str | None,
        observation_id: str | None,
        reason: str,
    ) -> tuple[dict, dict]:
        """Retain failing model output; degrade to metadata-only on write failure."""
        _retain(raw_text, rule, observation_id)
        return finish(_nonblocking_result("failed", deterministic_review, reason))

    def attempt_repair(rule: str, observation_id: str) -> tuple[dict, dict]:
        """Make exactly one repair call with fixed operator wording.

        Single shot: no transient-HTTP retry inside the repair, and the overall
        deadline still applies. A second violation keeps status failed with both
        attempts recorded; a clean retry completes normally.
        """
        remaining = int(deadline - time.monotonic())
        if remaining <= 0:
            return finish(_nonblocking_result("timed_out", deterministic_review, "assessment deadline expired"))
        repair_text = build_repair_message(rule, observation_id)
        if config["api_style"] == "anthropic":
            repair_payload = build_anthropic_payload(
                serialized, contract_text, config, max_tokens, repair_text=repair_text
            )
        else:
            repair_payload = build_openai_payload(
                serialized, contract_text, config, max_tokens, repair_text=repair_text
            )
        metadata["attempt_count"] = attempts + 1
        metadata["repair_attempts"] = 1
        try:
            response = opener(config["endpoint"], repair_payload, headers, remaining)
            with response as resp:
                repair_raw = resp.read().decode("utf-8")
                repair_request_id = _request_id(resp.headers)
                if repair_request_id is not None and metadata["gateway_request_id"] is None:
                    # Keep the violating response id for tracing; the repair
                    # id is less useful once the first attempt failed.
                    metadata["gateway_request_id"] = repair_request_id
        except urllib.error.HTTPError as exc:
            try:
                exc.read()
            except Exception:
                pass
            return finish(_nonblocking_result(
                "failed", deterministic_review, f"gateway request failed: HTTP {exc.code}",
            ))
        except Exception as exc:  # noqa: BLE001 — classified below, never raised
            name = type(exc).__name__.lower()
            message = str(exc).lower()
            if "timed out" in name or "timeout" in name or "timed out" in message or "timeout" in message:
                return finish(_nonblocking_result("timed_out", deterministic_review, "gateway request timed out"))
            last_error = _single_line(exc) or type(exc).__name__
            return finish(_nonblocking_result(
                "failed", deterministic_review, f"gateway transport error: {last_error}",
            ))
        try:
            repair_body = json.loads(repair_raw)
        except ValueError:
            # Transport-layer bytes, nothing model-authored: no quarantine,
            # matching the main path for malformed gateway JSON.
            return finish(_nonblocking_result(
                "failed", deterministic_review, "repair output was not valid JSON",
            ))
        repair_text_out = extract(repair_body)
        if not repair_text_out:
            return finish(_nonblocking_result(
                "failed", deterministic_review, "repair response held no usable text",
            ))
        try:
            repair_candidate = json.loads(_strip_code_fences(repair_text_out))
        except ValueError:
            _retain(repair_text_out, rule, observation_id)
            return finish(_nonblocking_result(
                "failed", deterministic_review, "repair output was not valid JSON",
            ))
        try:
            repair_result = validate_result(repair_candidate, deterministic_review, material_ids)
        except (AssessmentContractError, TypeError, ValueError) as exc:
            latest_rule = getattr(exc, "rule", "")
            latest_id = _sanitize_echo(getattr(exc, "observation_id", ""))
            metadata["violation_rule"] = latest_rule
            metadata["violation_observation_id"] = latest_id
            _retain(repair_text_out, latest_rule, latest_id)
            return finish(_nonblocking_result(
                "failed", deterministic_review,
                f"model result violated contract: {_single_line(exc)}",
            ))
        return finish(repair_result)

    materials = package.get("materials", [])
    excluded_count = sum(
        1 for item in materials
        if isinstance(item, dict) and item.get("kind") == "excluded"
    )
    metadata["excluded_materials"] = excluded_count
    metadata["total_materials"] = len(materials)
    metadata["exclude_patterns_count"] = len(config.get("exclude_patterns", []))

    if not config.get("enabled"):
        return finish(_nonblocking_result(
            "unavailable", deterministic_review, "assessment disabled: set QUALITY_GATES_LLM_ENABLED=1",
        ))

    contract_text = package.get("assessment_contract", "")
    serialized = serialize_input_package(package)
    if len(serialized.encode("utf-8")) > int(config.get("max_input_bytes", DEFAULT_MAX_INPUT_BYTES)):
        return finish(_nonblocking_result(
            "failed", deterministic_review,
            f"assessment input exceeds QUALITY_GATES_LLM_MAX_INPUT_BYTES={config['max_input_bytes']}",
        ))

    opener = _urlopen or _post_json
    counter = _counter or measure_input_tokens
    sizer_timeout = min(SIZER_SUB_TIMEOUT_SECONDS, max(1, int(deadline - time.monotonic())))
    try:
        input_tokens, sizing_method = counter(serialized, contract_text, config, headers, sizer_timeout)
    except Exception:
        input_tokens, sizing_method = estimate_tokens(serialized), "bytes div 4 fallback"
    metadata["sizing_method"] = sizing_method
    metadata["input_tokens"] = input_tokens

    max_tokens = effective_max_output(input_tokens, config)
    if max_tokens is None:
        return finish(_nonblocking_result(
            "failed", deterministic_review,
            f"assessment input needs {input_tokens} tokens, exceeding max_model_len={config['max_model_len']}",
        ))
    metadata["output_budget"] = max_tokens

    if config["api_style"] == "anthropic":
        payload = build_anthropic_payload(serialized, contract_text, config, max_tokens)
        extract = extract_anthropic_text
    else:
        payload = build_openai_payload(serialized, contract_text, config, max_tokens)
        extract = extract_openai_text

    tmpdir = tempfile.mkdtemp(prefix="qg-llm-")  # mkdtemp creates 0o700 atomically
    try:
        (Path(tmpdir) / "request.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass

    attempts = 0
    max_attempts = 1 + min(int(config.get("max_retries", 0)), HARD_MAX_RETRIES)
    last_error: str | None = None
    while attempts < max_attempts:
        attempts += 1
        metadata["attempt_count"] = attempts
        remaining = max(1, int(deadline - time.monotonic()))
        if remaining <= 0:
            return finish(_nonblocking_result("timed_out", deterministic_review, "assessment deadline expired"))
        try:
            response = opener(config["endpoint"], payload, headers, remaining)
            with response as resp:
                raw = resp.read().decode("utf-8")
                metadata["gateway_request_id"] = _request_id(resp.headers)
        except urllib.error.HTTPError as exc:
            try:
                exc.read()  # drain spooled error body to avoid ResourceWarning noise
            except Exception:
                pass
            last_error = f"gateway HTTP {exc.code}"
            if exc.code in (401, 403):
                try:
                    (Path(tmpdir) / "error.txt").write_text(f"HTTP {exc.code}", encoding="utf-8")
                except OSError:
                    pass
                return finish(_nonblocking_result(
                    "failed", deterministic_review, f"gateway authentication failed: HTTP {exc.code}",
                ))
            if exc.code in TRANSIENT_HTTP_STATUSES and attempts < max_attempts:
                time.sleep(0.2)
                continue
            if exc.code in TRANSIENT_HTTP_STATUSES:
                return finish(_nonblocking_result(
                    "failed", deterministic_review, f"gateway transient failure persisted: HTTP {exc.code}",
                ))
            return finish(_nonblocking_result(
                "failed", deterministic_review, f"gateway request failed: HTTP {exc.code}",
            ))
        except _RedirectBlocked as exc:
            return finish(_nonblocking_result(
                "failed", deterministic_review, _single_line(exc),
            ))
        except Exception as exc:  # noqa: BLE001 — classified below, never raised
            name = type(exc).__name__.lower()
            message = str(exc).lower()
            if "timed out" in name or "timeout" in name or "timed out" in message or "timeout" in message:
                return finish(_nonblocking_result("timed_out", deterministic_review, "gateway request timed out"))
            if any(token in message for token in (
                "connection refused", "no route to host", "name or service not known",
                "nodename nor servname", "network is unreachable", "failed to connect",
            )):
                return finish(_nonblocking_result("unavailable", deterministic_review, "gateway unreachable"))
            last_error = _single_line(exc) or type(exc).__name__
            return finish(_nonblocking_result(
                "failed", deterministic_review, f"gateway transport error: {last_error}",
            ))

        try:
            (Path(tmpdir) / "response.json").write_text(raw, encoding="utf-8")
        except OSError:
            pass
        try:
            body = json.loads(raw)
        except ValueError:
            return finish(_nonblocking_result("failed", deterministic_review, "gateway returned malformed JSON"))
        text = extract(body)
        if not text:
            return finish(_nonblocking_result("failed", deterministic_review, "gateway response held no usable text"))
        try:
            candidate = json.loads(_strip_code_fences(text))
        except ValueError:
            return quarantine_failed(
                text, None, None, "model output was not valid JSON"
            )
        try:
            result = validate_result(candidate, deterministic_review, material_ids)
        except (AssessmentContractError, TypeError, ValueError) as exc:
            # Record the machine-readable violation (rule + observation id) for
            # downstream use; the human-facing result payload stays unchanged.
            # An expired deadline short-circuits to timed_out before any
            # quarantine or repair work; otherwise exactly one repair follows.
            rule = getattr(exc, "rule", "")
            observation_id = _sanitize_echo(getattr(exc, "observation_id", ""))
            metadata["violation_rule"] = rule
            metadata["violation_observation_id"] = observation_id
            if int(deadline - time.monotonic()) <= 0:
                return finish(_nonblocking_result(
                    "timed_out", deterministic_review, "assessment deadline expired",
                ))
            _retain(
                text,
                rule,
                observation_id,
            )
            return attempt_repair(rule, observation_id)
        return finish(result)

    return finish(_nonblocking_result(
        "failed", deterministic_review, f"gateway request failed: {last_error or 'unknown error'}",
    ))


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            f"usage: {Path(sys.argv[0]).name} PROJECT_ROOT [DETERMINISTIC_JSON]",
            file=sys.stderr,
        )
        return 2
    root = Path(sys.argv[1])
    try:
        if len(sys.argv) == 3:
            deterministic_review = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        else:
            deterministic_review = json.load(sys.stdin)
    except (OSError, ValueError) as exc:
        print(f"error: unable to read deterministic review: {exc}", file=sys.stderr)
        return 2

    from llm_assessment_contract import build_input_package  # noqa: E402

    config_dir = Path.cwd()
    dotenv_path = config_dir / ".env"
    try:
        resolved_root = root.resolve()
        resolved_config = config_dir.resolve()
        if dotenv_path.exists() and (
            resolved_config == resolved_root
            or resolved_root in resolved_config.parents
        ):
            print(
                f"error: config directory {config_dir} resolves inside target {root}; "
                "run from outside the target so target content cannot supply config",
                file=sys.stderr,
            )
            return 2
        config = load_config(dotenv_path=dotenv_path if dotenv_path.exists() else None)
    except ExecutionConfigError as exc:
        result = _nonblocking_result("failed", deterministic_review, f"invalid gateway configuration: {exc}")
        print(json.dumps({"result": result, "metadata": {
            "api_style": DEFAULT_API_STYLE, "model": DEFAULT_MODEL,
            "attempt_count": 0, "elapsed_seconds": 0.0, "status": "failed",
            "gateway_request_id": None,
        }}, indent=2))
        return 0

    try:
        package = build_input_package(
            root, deterministic_review, config.get("exclude_patterns", [])
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"error: unable to build assessment input: {exc}", file=sys.stderr)
        return 2
    material_ids = {item["material_id"] for item in package["materials"]}

    result, metadata = execute_assessment(package, deterministic_review, material_ids, config)
    if (
        package["materials"]
        and metadata.get("excluded_materials") == len(package["materials"])
    ):
        print(
            f"warning: all {len(package['materials'])} materials excluded by "
            f"{EXCLUDE_ENV_VAR}",
            file=sys.stderr,
        )
    print(json.dumps({"result": result, "metadata": metadata}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
