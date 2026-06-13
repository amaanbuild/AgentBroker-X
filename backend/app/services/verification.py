"""Verification engine - automatically validate task outputs against criteria.

Supports three verification modes declared in a task's `acceptance_criteria`:

    {"type": "text",   "must_include": [...], "min_length": 100}
    {"type": "json",   "schema": {...}}                # lightweight JSON-schema
    {"type": "file",   "required_keys": ["url"], "extensions": [".pdf"]}

Each mode emits a list of named checks; the verdict passes only if every
required check passes. The score is the fraction of checks that passed.
"""
from __future__ import annotations

from typing import Any

from ..models import Task, VerificationVerdict


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "passed": bool(ok), "detail": detail}


def _verify_text(result: dict, criteria: dict) -> list[dict]:
    checks = []
    text = str(result.get("text") or result.get("output") or "")
    min_length = criteria.get("min_length", 0)
    checks.append(_check("non_empty", bool(text.strip()), "output present"))
    checks.append(
        _check("min_length", len(text) >= min_length, f"len={len(text)} need>={min_length}")
    )
    for token in criteria.get("must_include", []):
        checks.append(
            _check(f"includes:{token}", token.lower() in text.lower(), f"'{token}'")
        )
    for token in criteria.get("must_exclude", []):
        checks.append(
            _check(f"excludes:{token}", token.lower() not in text.lower(), f"'{token}'")
        )
    return checks


_TYPE_MAP = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _verify_json(result: dict, criteria: dict) -> list[dict]:
    checks = []
    schema = criteria.get("schema", {})
    props = schema.get("properties", {})
    required = schema.get("required", list(props.keys()))
    data = result.get("data", result)

    checks.append(_check("is_object", isinstance(data, dict), "result.data is an object"))
    if not isinstance(data, dict):
        return checks

    for key in required:
        checks.append(_check(f"required:{key}", key in data, f"field '{key}' present"))

    for key, spec in props.items():
        if key not in data:
            continue
        expected = _TYPE_MAP.get(spec.get("type", "any"))
        if expected:
            checks.append(
                _check(
                    f"type:{key}",
                    isinstance(data[key], expected),
                    f"{key} is {spec.get('type')}",
                )
            )
    return checks


def _verify_file(result: dict, criteria: dict) -> list[dict]:
    checks = []
    for key in criteria.get("required_keys", ["url"]):
        checks.append(_check(f"has:{key}", bool(result.get(key)), f"file ref '{key}'"))
    ref = str(result.get("url") or result.get("path") or "")
    exts = criteria.get("extensions")
    if exts:
        checks.append(
            _check("extension", any(ref.lower().endswith(e) for e in exts), ref)
        )
    return checks


def verify(task: Task) -> tuple[VerificationVerdict, float, list[dict], str]:
    """Run verification for a task. Returns (verdict, score, checks, notes)."""
    result = task.result or {}
    criteria = task.acceptance_criteria or {}
    vtype = criteria.get("type", "text")

    if vtype == "json":
        checks = _verify_json(result, criteria)
    elif vtype == "file":
        checks = _verify_file(result, criteria)
    else:
        checks = _verify_text(result, criteria)

    if not checks:
        return VerificationVerdict.inconclusive, 0.0, checks, "no checks defined"

    passed = sum(1 for c in checks if c["passed"])
    score = round(passed / len(checks), 3)
    verdict = (
        VerificationVerdict.passed
        if passed == len(checks)
        else VerificationVerdict.failed
    )
    notes = f"{passed}/{len(checks)} checks passed ({vtype} verification)"
    return verdict, score, checks, notes
