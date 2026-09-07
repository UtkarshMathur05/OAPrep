"""Functional execution: solving a problem by writing the function.

These tests never call Judge0. They cover the two things that can silently
corrupt a verdict — building the wrong program, and comparing two right answers
as though they differ.
"""

import json
import subprocess
import sys

import pytest

from app.harness import UnsupportedSignature, build, compare, supports

TWO_SUM = {"name": "twoSum",
           "params": [{"name": "nums", "type": "integer[]"},
                      {"name": "target", "type": "integer"}],
           "return": {"type": "integer[]"}}


def run(signature: dict, code: str, stdin: str) -> str:
    """Execute a built program locally, the way Judge0 would."""
    proc = subprocess.run([sys.executable, "-c", build("python", signature, code)],
                          input=stdin, capture_output=True, text=True, timeout=15)
    return proc.stdout.strip() or f"ERROR: {proc.stderr.strip().splitlines()[-1:]}"


# ------------------------------------------------------------------- building

def test_a_leetcode_starter_runs_unmodified():
    """The starter we hand people is LeetCode's own, annotations and all.

    `List[int]` is never imported in those snippets and annotations evaluate at
    def time, so without the harness preamble the solution raises NameError
    before it ever runs — a failure that looks like the person's bug.
    """
    code = ("class Solution:\n"
            "    def twoSum(self, nums: List[int], target: int) -> List[int]:\n"
            "        seen = {}\n"
            "        for i, x in enumerate(nums):\n"
            "            if target - x in seen: return [seen[target - x], i]\n"
            "            seen[x] = i")
    assert run(TWO_SUM, code, "[2,7,11,15]\n9") == "[0,1]"


def test_tree_and_list_arguments_are_built_not_passed_as_arrays():
    """`[3,9,20,null,null,15,7]` has to arrive as a TreeNode, not a list."""
    depth = {"name": "maxDepth", "params": [{"name": "root", "type": "TreeNode"}],
             "return": {"type": "integer"}}
    code = ("class Solution:\n"
            "    def maxDepth(self, root: Optional[TreeNode]) -> int:\n"
            "        return 0 if not root else 1 + max(self.maxDepth(root.left),"
            " self.maxDepth(root.right))")
    assert run(depth, code, "[3,9,20,null,null,15,7]") == "3"

    reverse = {"name": "reverseList", "params": [{"name": "head", "type": "ListNode"}],
               "return": {"type": "ListNode"}}
    code = ("class Solution:\n"
            "    def reverseList(self, head):\n"
            "        prev = None\n"
            "        while head: head.next, prev, head = prev, head, head.next\n"
            "        return prev")
    assert run(reverse, code, "[1,2,3,4,5]") == "[5,4,3,2,1]"


def test_a_void_problem_reports_the_mutated_argument():
    """In-place problems return None; the answer is what they changed."""
    sort_colors = {"name": "sortColors", "params": [{"name": "nums", "type": "integer[]"}],
                   "return": {"type": "void"}}
    code = ("class Solution:\n"
            "    def sortColors(self, nums: List[int]) -> None:\n"
            "        nums.sort()")
    assert run(sort_colors, code, "[2,0,2,1,1,0]") == "[0,0,1,1,2,2]"


def test_harness_names_cannot_collide_with_a_solution():
    """Somebody will define `main`, `solve` or `parse`. That must not break."""
    code = ("class Solution:\n"
            "    def twoSum(self, nums, target):\n"
            "        return [0, 1]\n"
            "\n"
            "def main(): raise SystemExit('user main should never be called')\n"
            "def parse(x): return None\n"
            "json = None\n")
    assert run(TWO_SUM, code, "[3,3]\n6") == "[0,1]"


def test_a_type_without_a_harness_stays_in_stdin_mode():
    """Refusing is the point: a shape we cannot build must not be half-built."""
    weird = {"name": "f", "params": [{"name": "x", "type": "TreeNodeGraph[]"}],
             "return": {"type": "integer"}}
    assert supports("python", weird) is False
    assert supports("python", {"params": []}) is False, "no name is not a function"
    assert supports("go", TWO_SUM) is False, "no Go harness yet"


def test_building_for_a_language_without_a_harness_raises():
    """Never returns something that looks like code but is not."""
    with pytest.raises(UnsupportedSignature):
        build("go", TWO_SUM, "func twoSum() {}")


# ------------------------------------------------------------------ comparing

def test_spacing_is_not_a_wrong_answer():
    """Languages serialise JSON differently; that is not the person's mistake."""
    assert compare("[0,1]", "[0, 1]")
    assert compare("[[1,6],[8,10]]", "[[1, 6], [8, 10]]")


def test_any_order_is_honoured_only_where_the_statement_says_so():
    assert compare("[0,1]", "[1,0]", "unordered")
    assert not compare("[0,1]", "[1,0]", "exact"), "reordering is not free by default"


def test_unordered_does_not_forgive_a_wrong_answer():
    """The risk of a loose judge is passing something incorrect."""
    assert not compare("[0,1]", "[0,2]", "unordered")
    assert not compare("[0,1]", "[0,1,2]", "unordered")
    assert not compare("[[1,2]]", "[[2,1]]", "unordered"), "rows keep their own order"


def test_one_is_not_true():
    """Python's True == 1. Returning 1 for a boolean problem is still wrong."""
    assert not compare("true", "1")
    assert compare("true", "true")


def test_doubles_compare_with_a_tolerance():
    """Languages disagree in the last place; LeetCode itself judges to 1e-5."""
    assert compare("2.00000", "2.0")
    assert compare("0.66667", "0.6666666666")
    assert not compare("2.0", "2.1")


def test_unparseable_output_falls_back_to_text_and_still_fails():
    """A crashed harness must show as wrong, never as accidentally equal."""
    assert not compare("[0,1]", "Traceback (most recent call last):")
    assert compare("abc", "abc"), "non-JSON but identical is still a match"


# ------------------------------------------------------- the other languages
#
# These check what is *generated*, not what Judge0 does with it — a compile is
# a network round trip. Correct execution for every shape was verified against
# the live judge for all four languages; what breaks silently afterwards is the
# builder emitting the wrong call, so that is what is pinned here.

def test_every_language_agrees_on_what_it_supports():
    """`runnable_languages` is computed from these, so a lie here shows up as a
    language in the picker that cannot run."""
    for language in ("python", "java", "cpp", "c"):
        assert supports(language, TWO_SUM), language
        assert not supports(language, {"params": []}), f"{language}: no name"
        assert not supports(language, None), f"{language}: no signature"


def test_java_entry_point_is_main_and_solution_is_not_public():
    """Judge0 compiles the file as Main.java: two public classes will not build,
    and people paste `public class Solution` from an IDE often enough to matter."""
    out = build("java", TWO_SUM, "public class Solution { }")
    assert "public class Main" in out
    assert "public class Solution" not in out
    assert "class Solution" in out


def test_c_expands_arrays_into_leetcode_s_extra_parameters():
    """C has no containers, so `int[] nums` is `(int* nums, int numsSize)` and an
    array return comes back through `int* returnSize`. This convention was
    checked against 510 real C starters; if the builder drifts from it, every C
    submission fails to compile."""
    out = build("c", TWO_SUM, "int* twoSum(int* a, int b, int c, int* d) { return 0; }")
    assert "twoSum(a0, a0Size, a1, &_rsize)" in out


def test_c_two_dimensional_return_carries_column_sizes():
    merge = {"name": "merge", "params": [{"name": "intervals", "type": "integer[][]"}],
             "return": {"type": "integer[][]"}}
    out = build("c", merge, "int** merge() { return 0; }")
    assert "merge(a0, a0Size, a0ColSize, &_rsize, &_rcols)" in out


def test_c_handles_nested_strings_but_refuses_a_third_dimension():
    """`list<list<string>>` is `char***` and does work — verified on the judge.
    A third dimension has no LeetCode convention to follow, so it is refused
    rather than guessed at."""
    nested = {"name": "f", "params": [{"name": "x", "type": "string[]"}],
              "return": {"type": "list<list<string>>"}}
    assert supports("c", nested)

    deeper = {"name": "f", "params": [{"name": "x", "type": "integer"}],
              "return": {"type": "list<list<list<integer>>>"}}
    assert supports("python", deeper), "Python has no arity limit"
    assert not supports("c", deeper)


def test_cpp_declares_arguments_at_their_concrete_types():
    """C++ has no reflection, so the call site is generated from metaData."""
    out = build("cpp", TWO_SUM, "class Solution {};")
    assert "vector<int> a0{};" in out
    assert "int a1{};" in out
    assert "_sol.twoSum(a0, a1)" in out


def test_a_void_problem_prints_the_first_argument_in_every_language():
    """The mutation is the answer, and getting this wrong prints nothing at all."""
    sort_colors = {"name": "sortColors", "params": [{"name": "nums", "type": "integer[]"}],
                   "return": {"type": "void"}}
    assert "ser(a0)" in build("cpp", sort_colors, "class Solution {};")
    assert "a0" in build("c", sort_colors, "void sortColors(int* a, int b) {}")
    assert "values[0]" in build("java", sort_colors, "class Solution {}")


# ------------------------------------------------- bugs found on the live judge
# Each of these shipped, built cleanly, and failed only when a real solution ran
# against real test cases. They are pinned here because none of them is visible
# from reading the generated program.

def test_java_hoists_a_solution_s_own_imports():
    """Java wants every import before the first type declaration, and the
    preamble declares ListNode/TreeNode above the person's code. Left in place,
    `import java.util.*;` — which anything using a HashMap needs — became a
    compile error pointing at a line they did not write."""
    out = build("java", TWO_SUM, "import java.util.*;\nclass Solution { }")
    assert out.index("import java.util.*;") < out.index("class ListNode")
    body = out[out.index("class ListNode"):]
    assert "import " not in body


def test_java_drops_a_package_declaration():
    """Judge0 compiles a bare Main.java; a package line breaks the build."""
    out = build("java", TWO_SUM, "package com.example;\nclass Solution { }")
    assert "package " not in out


def test_java_serialises_a_tree_with_a_missing_child():
    """The level-order BFS pushes nulls on purpose — a null is how a gap is
    written. ArrayDeque rejects null elements, so every tree with a missing
    child threw instead of printing."""
    out = build("java", TWO_SUM, "class Solution { }")
    assert "new ArrayDeque" not in out.split("static List<Integer> fromTree")[1]


def test_a_list_of_lists_builds_one_node_chain_each():
    """`ListNode[]` is a list of linked lists. Collapsing the type to its
    element name built one chain from every row concatenated together."""
    lists = {"name": "mergeKLists",
             "params": [{"name": "lists", "type": "ListNode[]"}],
             "return": {"type": "ListNode"}}
    out = build("python", lists, "class Solution:\n    def mergeKLists(self, lists): return None")
    assert "['ListNode', 1]" in out, "the nesting depth must survive into the runner"

    got = run(lists, "class Solution:\n"
                     "    def mergeKLists(self, lists):\n"
                     "        return lists[1]\n", "[[1,2],[3,4]]")
    assert got == "[3,4]"


def test_an_empty_result_is_a_list_not_a_null():
    """A correct solution returns None for "no nodes"; the expected outputs
    write that as []. Printing `null` failed every empty case."""
    lists = {"name": "mergeKLists",
             "params": [{"name": "lists", "type": "ListNode[]"}],
             "return": {"type": "ListNode"}}
    got = run(lists, "class Solution:\n"
                     "    def mergeKLists(self, lists): return None\n", "[]")
    assert got == "[]"

    out = build("java", lists, "class Solution { }")
    assert "new ArrayList<>()" in out.split("target.getReturnType() == void.class")[1]


def test_c_takes_an_array_of_nodes():
    """`ListNode[]` expands like any other array — `struct ListNode**` plus a
    size — which is what LeetCode's own C starter for mergeKLists declares."""
    lists = {"name": "mergeKLists",
             "params": [{"name": "lists", "type": "ListNode[]"}],
             "return": {"type": "ListNode"}}
    assert supports("c", lists)
    out = build("c", lists, "struct ListNode* mergeKLists(struct ListNode** l, int n) { return 0; }")
    assert "mergeKLists(a0, a0Size)" in out

    deeper = {"name": "f", "params": [{"name": "x", "type": "ListNode[][]"}],
              "return": {"type": "integer"}}
    assert not supports("c", deeper), "no starter convention exists for this"
