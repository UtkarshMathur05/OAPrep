"""Python harness: JSON arguments in, JSON answer out.

Appended to the person's solution before submission. Everything it defines is
prefixed `_mz_` so it cannot collide with names in their code — `main`, `solve`
and `parse` are all things somebody will reasonably define.
"""

from __future__ import annotations

# LeetCode's metaData type strings we can deserialise. A type absent from here
# is not a bug to work around: the problem stays in stdin mode and says so,
# which is better than passing a shape the solution cannot use.
SCALARS = {"integer", "long", "double", "string", "boolean", "character",
           "float", "int", "str", "bool"}
STRUCTURED = {"ListNode", "TreeNode"}


def _base(type_name: str) -> str:
    """Strip every layer of container down to the element type.

    `integer[][]` -> `integer`, `list<list<string>>` -> `string`. The nesting
    loops because LeetCode mixes the two notations and nests the generic one:
    peeling a single layer left `list<string>`, which read as an unknown type
    and quietly dropped ten problems into stdin mode.
    """
    name = (type_name or "").strip()
    while True:
        if name.endswith("[]"):
            name = name[:-2]
        elif name.startswith("list<") and name.endswith(">"):
            name = name[5:-1]
        else:
            return name


def _depth(type_name: str) -> int:
    """How many container layers wrap the element type."""
    name = (type_name or "").strip()
    n = 0
    while True:
        if name.endswith("[]"):
            name, n = name[:-2], n + 1
        elif name.startswith("list<") and name.endswith(">"):
            name, n = name[5:-1], n + 1
        else:
            return n


def supports(signature: dict) -> bool:
    types = [p.get("type", "") for p in signature.get("params") or []]
    types.append((signature.get("return") or {}).get("type", ""))
    for t in types:
        base = _base(t)
        if base.lower() in SCALARS or base in STRUCTURED or base.lower() == "void":
            continue
        return False
    return bool(signature.get("params") is not None)


# Goes BEFORE the person's code, and the ordering is load-bearing.
#
# LeetCode's own starters annotate `nums: List[int]` and `root: Optional[TreeNode]`
# without importing either — their judge injects them. Annotations are evaluated
# when the function is defined, so without this the solution raises NameError
# before it ever runs. `from __future__ import annotations` makes them strings
# and has to be the first statement in the file, which is why this is a preamble
# rather than something appended with the runner.
_PREAMBLE = '''from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple
import bisect, collections, functools, heapq, itertools, math, re, string
from collections import Counter, defaultdict, deque, OrderedDict


class ListNode:
    def __init__(self, val=0, next=None):
        self.val, self.next = val, next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right

'''


_PRELUDE = '''

# ---------------------------------------------------------------------------
# Added by Memoize. Reads one JSON argument per line, calls your function, and
# prints what it returns. You never need to touch this.
import json as _mz_json, sys as _mz_sys


def _mz_to_list(values):
    head = tail = None
    for v in values or []:
        node = ListNode(v)
        if head is None:
            head = tail = node
        else:
            tail.next = tail = node
    return head


def _mz_from_list(node):
    out = []
    while node is not None:
        out.append(node.val)
        node = node.next
    return out


def _mz_to_tree(values):
    """Level order with explicit nulls, the way the statements write it."""
    if not values:
        return None
    root = TreeNode(values[0])
    queue, i = [root], 1
    while queue and i < len(values):
        node = queue.pop(0)
        if i < len(values):
            if values[i] is not None:
                node.left = TreeNode(values[i])
                queue.append(node.left)
            i += 1
        if i < len(values):
            if values[i] is not None:
                node.right = TreeNode(values[i])
                queue.append(node.right)
            i += 1
    return root


def _mz_from_tree(root):
    if root is None:
        return []
    out, queue = [], [root]
    while queue:
        node = queue.pop(0)
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while out and out[-1] is None:   # trailing nulls are not part of the answer
        out.pop()
    return out


def _mz_encode(value):
    """Turn whatever the solution returned back into plain JSON values."""
    if isinstance(value, ListNode):
        return _mz_from_list(value)
    if isinstance(value, TreeNode):
        return _mz_from_tree(value)
    if isinstance(value, (list, tuple)):
        return [_mz_encode(v) for v in value]
    return value


def _mz_structure(value, kind, depth):
    """Build nodes at the nesting depth the signature declares.

    `ListNode[]` is a list of lists, not one long list. Collapsing the type to
    its element name lost that, so merge-k-sorted-lists received a single
    linked list built from every input row.
    """
    if depth:
        return [_mz_structure(v, kind, depth - 1) for v in value]
    return _mz_to_list(value) if kind == "ListNode" else _mz_to_tree(value)


def _mz_run():
    raw = _mz_sys.stdin.read().split("\\n")
    args = []
    for text, spec in zip(raw, _MZ_PARAM_TYPES):
        value = _mz_json.loads(text)
        kind, depth = spec
        if kind in ("ListNode", "TreeNode"):
            value = _mz_structure(value, kind, depth)
        args.append(value)

    solution = Solution()
    result = getattr(solution, _MZ_METHOD)(*args)

    # A void problem mutates its first argument in place; that mutation is the
    # answer, so print it rather than the None the function returned.
    if _MZ_RETURN == "void":
        result = args[0] if args else None

    # An empty list or tree is `[]`, not `null` -- that is how the expected
    # outputs are written, and returning None for "no nodes" is the normal
    # thing a correct solution does.
    if result is None and _MZ_RETURN in ("ListNode", "TreeNode"):
        result = []

    print(_mz_json.dumps(_mz_encode(result), separators=(",", ":")))


if __name__ == "__main__":
    _mz_run()
'''


def build(signature: dict, code: str) -> str:
    param_types = [
        [_base(p.get("type", "")), _depth(p.get("type", ""))]
        for p in signature.get("params") or []
    ]
    return_type = _base((signature.get("return") or {}).get("type", ""))
    header = (
        f"_MZ_METHOD = {signature['name']!r}\n"
        f"_MZ_PARAM_TYPES = {param_types!r}\n"
        f"_MZ_RETURN = {return_type!r}\n"
    )
    return f"{_PREAMBLE}\n{code.rstrip()}\n\n{header}{_PRELUDE}"
