"""Run a solution as a function instead of a program.

Judge0 still only speaks stdin/stdout — that has not changed and cannot. What
changes is who writes the parsing. A harness is appended to the person's code:
it reads one JSON argument per line, deserialises each by its declared type,
calls their function, and prints the return value as JSON. They write
`def twoSum(self, nums, target)` and never see a stream.

The cost of this design is one harness per language. The alternative considered
was a stdin-parsing preamble generated per problem per language, which is
3,399 x 11 artifacts each able to be independently wrong, against 11 written
once and tested. A parser that is subtly wrong tells a correct solution it is
wrong, which is the failure this codebase treats as worse than having no tests
at all.

Types come from LeetCode's own `metaData`, so they are not guessed.
"""

from __future__ import annotations

import json
import math
from typing import Optional

from app.harness import c as _c, cpp as _cpp, java as _java, python as _python

# language id (app.languages) -> module implementing build(signature, code)
_BUILDERS = {
    "python": _python,
    "java": _java,
    "cpp": _cpp,
    "c": _c,
}


class UnsupportedSignature(Exception):
    """The harness cannot express this problem in this language.

    Raised rather than returned so it can never be mistaken for generated code.
    Callers degrade to stdin mode and say so.
    """


def supports(language: str, signature: Optional[dict]) -> bool:
    """Whether a functional run is possible. False means: fall back to stdin."""
    if not signature or not signature.get("name"):
        return False
    builder = _BUILDERS.get(language)
    if builder is None:
        return False
    return builder.supports(signature)


def build(language: str, signature: dict, code: str) -> str:
    """Return the full program to submit: the person's code plus the harness."""
    builder = _BUILDERS.get(language)
    if builder is None:
        raise UnsupportedSignature(f"no harness for {language!r}")
    return builder.build(signature, code)


# ------------------------------------------------------------------ comparing

_FLOAT_TOLERANCE = 1e-5


def compare(expected: str, actual: str, judge_mode: str = "exact") -> bool:
    """Compare a returned answer with the expected one, structurally.

    Text comparison is wrong here: `[0,1]` and `[0, 1]` are the same answer and
    differ only in how a language's serialiser spaces them. So both sides are
    parsed as JSON and compared as values, and only if that fails do we fall
    back to comparing the raw text (which covers a harness that printed
    something unparseable, and keeps the failure visible rather than swallowed).
    """
    exp_text, act_text = (expected or "").strip(), (actual or "").strip()
    try:
        exp, act = json.loads(exp_text), json.loads(act_text)
    except (json.JSONDecodeError, TypeError):
        return exp_text == act_text

    if judge_mode == "unordered":
        # "You can return the answer in any order." Only the top level is
        # reordered: for integer[][] the rows may come in any order but each row
        # is still itself.
        if isinstance(exp, list) and isinstance(act, list):
            return len(exp) == len(act) and _sorted(exp) == _sorted(act)
    elif judge_mode == "set":
        if isinstance(exp, list) and isinstance(act, list):
            return _sorted(exp) == _sorted(act)

    return _equal(exp, act)


def _sorted(values: list) -> list:
    """Order a list of arbitrary JSON values deterministically."""
    return sorted(values, key=lambda v: json.dumps(v, sort_keys=True))


def _equal(a, b) -> bool:
    """Structural equality, with a tolerance on floats.

    A problem returning a double cannot be compared exactly: languages disagree
    in the last place, and LeetCode itself judges these to 1e-5.
    """
    if isinstance(a, float) or isinstance(b, float):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return math.isclose(a, b, rel_tol=_FLOAT_TOLERANCE, abs_tol=_FLOAT_TOLERANCE)
        return False
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b))
    # bool before int: in Python True == 1, and returning 1 for a boolean
    # problem is a wrong answer, not a formatting difference.
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b
