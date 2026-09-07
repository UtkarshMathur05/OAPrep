"""Corpus step 6 — turn fetched signatures into functional problems.

Reads out/signatures.jsonl and, for each problem it can fully verify, sets
`exec_mode='functional'`, stores the signature and starters, and replaces the
stdin test cases with JSON ones.

The expected answers are the weak link and are treated as such. LeetCode does
not expose them, so they are read from the "Output:" lines of the statement we
already stored, paired positionally with `exampleTestcaseList`. That pairing is
only trustworthy if everything lines up, so a problem is converted only when:

  * the signature parses and every type has a Python harness
  * there are as many "Output:" lines as example inputs
  * every input supplies exactly one JSON value per parameter
  * every expected answer parses as JSON and matches the declared return type

Anything else stays in stdin mode and is reported. A problem left behind is
recoverable; a problem converted with a mispaired answer tells people their
correct solution is wrong, which is the failure this corpus refuses to risk.

    python -m ai.corpus.load_signatures            # report
    python -m ai.corpus.load_signatures --apply    # convert
    python -m ai.corpus.load_signatures --dump     # write 10_signatures.sql

Commit the dump, for the same reason ai/corpus/load_corpus.py commits its own:
out/signatures.jsonl is gitignored and rebuilding it costs 1,125 requests to a
site that is entitled to rate-limit us. Without the dump a fresh clone browses
988 problems it cannot run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "backend")

SRC = Path(__file__).parent / "out" / "signatures.jsonl"
DUMP = Path("database/init/10_signatures.sql")
MAX_CASES = 5

# LeetCode's langSlug -> our app.languages id.
LANG_MAP = {"python3": "python", "cpp": "cpp", "java": "java",
            "javascript": "javascript", "c": "c", "golang": "go",
            "csharp": "csharp", "kotlin": "kotlin", "ruby": "ruby",
            "rust": "rust", "typescript": "typescript"}

_OUTPUT_LINE = re.compile(r"^Output:\s*(.+?)\s*$", re.MULTILINE)
_ANY_ORDER = re.compile(r"in any order", re.IGNORECASE)


def expected_outputs(description: str) -> list[str]:
    """The "Output:" lines of the worked examples, in order."""
    return _OUTPUT_LINE.findall(description or "")


def judge_mode(description: str, signature: dict) -> str:
    """`unordered` when the statement says the answer's order is free.

    Only for a list return — "return the answer in any order" about a scalar
    would mean something else entirely, and guessing there would let a wrong
    answer pass.
    """
    ret = ((signature.get("return") or {}).get("type") or "")
    if ret.endswith("[]") or ret.startswith("list<"):
        if _ANY_ORDER.search(description or ""):
            return "unordered"
    return "exact"


def _type_ok(value, type_name: str) -> bool:
    """Does a parsed answer look like the declared return type?

    Catches the failure that matters: "Output:" lines picked up in the wrong
    order, or a statement whose examples do not correspond to the test list.
    """
    base = (type_name or "").strip()
    if base.endswith("[]") or base.startswith("list<") or base in {"ListNode", "TreeNode"}:
        # Only the outermost layer matters: every container serialises to a
        # JSON array, however deeply it nests.
        return isinstance(value, list)
    if base == "boolean":
        return isinstance(value, bool)
    if base in {"integer", "long"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if base == "double":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if base in {"string", "character"}:
        return isinstance(value, str)
    if base == "void":
        return True
    return False


_PY_DEF = "def {name}("


def declared_param_count(row: dict) -> int | None:
    """How many arguments the real function takes, per the Python starter.

    `metaData` is not always the function: `hasCycle` lists a `pos` parameter
    and `firstBadVersion` lists `bad`, both of which are judge setup rather than
    arguments, and no language's signature has them. Trusting metaData there
    means passing an extra argument and failing every case with a TypeError the
    person cannot act on. The starters do not lie, so they arbitrate.
    """
    snippet = (row.get("code_snippets") or {}).get("python3")
    name = (row.get("signature") or {}).get("name")
    if not snippet or not name:
        return None
    match = re.search(r"def\s+" + re.escape(name) + r"\s*\(([^)]*)\)", snippet)
    if not match:
        return None
    args = [a for a in match.group(1).split(",") if a.strip() and a.strip() != "self"]
    return len(args)


def convert(row: dict, description: str) -> tuple[list[dict], str, str]:
    """Return (cases, judge_mode, reason). An empty case list means: skip."""
    from app.harness import supports

    signature = row.get("signature")
    if not signature or not signature.get("name"):
        return [], "exact", "no function signature (class-design problem)"
    if not supports("python", signature):
        types = [p.get("type") for p in signature.get("params") or []]
        types.append((signature.get("return") or {}).get("type"))
        return [], "exact", f"harness has no type for {types}"
    if not row.get("code_snippets"):
        return [], "exact", "no starter code"

    # Having *a* starter is not enough: it has to be one we can run. LeetCode's
    # JavaScript-track problems (`createHelloWorld`) ship starters only for
    # languages with no harness, so converting them produced a problem the
    # editor offered zero languages for — browsable, unsolvable, and silent
    # about why.
    runnable = [our for their, our in LANG_MAP.items()
                if their in row["code_snippets"] and supports(our, signature)]
    if not runnable:
        langs = sorted(row["code_snippets"])
        return [], "exact", f"no runnable language (starters only for {langs})"

    n_declared = declared_param_count(row)
    if n_declared is not None and n_declared != len(signature.get("params") or []):
        return [], "exact", (f"metaData claims {len(signature['params'])} params, "
                             f"the real signature takes {n_declared}")

    inputs = row.get("example_inputs") or []
    outputs = expected_outputs(description)
    if not inputs or not outputs:
        return [], "exact", "no worked examples to pair"
    if len(inputs) != len(outputs):
        return [], "exact", f"{len(inputs)} inputs vs {len(outputs)} outputs"

    n_params = len(signature.get("params") or [])
    ret_type = (signature.get("return") or {}).get("type", "")
    # A void problem's answer is its mutated first argument, so judge that type.
    if ret_type == "void" and signature.get("params"):
        ret_type = signature["params"][0].get("type", "")

    cases = []
    for stdin, answer in zip(inputs, outputs):
        lines = stdin.split("\n")
        if len(lines) != n_params:
            return [], "exact", f"input has {len(lines)} values for {n_params} params"
        try:
            for line in lines:
                json.loads(line)
            value = json.loads(answer)
        except json.JSONDecodeError:
            return [], "exact", f"answer is not JSON: {answer[:40]!r}"
        if not _type_ok(value, ret_type):
            return [], "exact", f"answer {answer[:30]!r} is not a {ret_type}"
        cases.append({"input": stdin,
                      "expected_output": json.dumps(value, separators=(",", ":"))})

    return cases[:MAX_CASES], judge_mode(description, signature), ""


def _lit(value) -> str:
    """A SQL literal. json.dumps first, so nothing arrives as a Python repr."""
    if value is None:
        return "NULL"
    if not isinstance(value, str):
        value = json.dumps(value, separators=(",", ":"))
    return "'" + value.replace("'", "''") + "'"


def dump(db) -> int:
    """Write the functional conversion as replayable SQL, keyed by slug.

    Only the columns this step owns, and only the test cases belonging to a
    functional problem. Keyed by slug rather than id because ids are generated
    per database and would not match a fresh clone's.
    """
    problems = db.query(
        "SELECT slug, signature, code_snippets, judge_mode FROM problems "
        "WHERE exec_mode = 'functional' ORDER BY slug")
    cases = db.query(
        "SELECT p.slug, t.input, t.expected_output FROM test_cases t "
        "JOIN problems p ON p.id = t.problem_id WHERE p.exec_mode = 'functional' "
        "ORDER BY p.slug, t.created_at, t.id")

    lines = [
        "-- Generated by ai/corpus/load_signatures.py --dump. Do not edit by hand.",
        f"-- {len(problems)} functional problems, {len(cases)} test cases.",
        "",
    ]
    for row in problems:
        lines.append(
            "UPDATE problems SET exec_mode = 'functional', io_format = NULL, "
            f"signature = {_lit(row['signature'])}::jsonb, "
            f"code_snippets = {_lit(row['code_snippets'])}::jsonb, "
            f"judge_mode = {_lit(row['judge_mode'])} "
            f"WHERE slug = {_lit(row['slug'])};")

    lines += ["", "-- Replace, never merge: a stdin case and a JSON case cannot coexist.",
              "DELETE FROM test_cases WHERE problem_id IN "
              "(SELECT id FROM problems WHERE exec_mode = 'functional');", ""]
    for row in cases:
        lines.append(
            "INSERT INTO test_cases (problem_id, input, expected_output) "
            f"SELECT id, {_lit(row['input'])}, {_lit(row['expected_output'])} "
            f"FROM problems WHERE slug = {_lit(row['slug'])};")

    DUMP.parent.mkdir(parents=True, exist_ok=True)
    DUMP.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {DUMP} ({len(problems)} problems, {len(cases)} cases)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write to the database")
    ap.add_argument("--slug", help="only this problem")
    ap.add_argument("--dump", action="store_true",
                    help=f"write {DUMP} from the database and exit")
    args = ap.parse_args()

    from app.services import database_service as db

    if args.dump:
        return dump(db)

    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.slug:
        rows = [r for r in rows if r["slug"] == args.slug]

    converted = skipped = reverted = 0
    for row in rows:
        problem = db.query_one(
            "SELECT id::text AS id, description, exec_mode FROM problems WHERE slug = %s",
            (row["slug"],))
        if problem is None:
            continue

        cases, mode, reason = convert(row, problem["description"])
        if not cases:
            skipped += 1
            # A problem already converted that no longer passes these checks was
            # converted under a rule we have since found wrong. Put it back:
            # leaving it functional means every run fails for a reason the
            # person cannot see.
            if problem["exec_mode"] == "functional":
                reverted += 1
                print(f"  REVERT {row['slug']:<36} {reason}")
                if args.apply:
                    db.execute(
                        "UPDATE problems SET exec_mode = 'stdin', signature = NULL, "
                        "code_snippets = NULL, judge_mode = 'exact' WHERE id = %s",
                        (problem["id"],))
                    db.execute("DELETE FROM test_cases WHERE problem_id = %s",
                               (problem["id"],))
            else:
                print(f"  skip {row['slug']:<38} {reason}")
            continue

        converted += 1
        print(f"  ok   {row['slug']:<38} {len(cases)} cases, judge={mode}")
        if not args.apply:
            continue

        snippets = {LANG_MAP[k]: v for k, v in row["code_snippets"].items()
                    if k in LANG_MAP}
        db.execute(
            """
            UPDATE problems
               SET signature = %s, code_snippets = %s,
                   judge_mode = %s, exec_mode = 'functional',
                   io_format = NULL
             WHERE id = %s
            """,
            (json.dumps(row["signature"]), json.dumps(snippets), mode, problem["id"]),
        )
        # Replace, never merge: a stdin case and a JSON case cannot coexist.
        db.execute("DELETE FROM test_cases WHERE problem_id = %s", (problem["id"],))
        for case in cases:
            db.execute(
                "INSERT INTO test_cases (problem_id, input, expected_output) "
                "VALUES (%s, %s, %s)",
                (problem["id"], case["input"], case["expected_output"]),
            )

    verb = "converted" if args.apply else "convertible"
    print(f"\n{converted} {verb}, {skipped} left in stdin mode, "
          f"{reverted} reverted to stdin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
