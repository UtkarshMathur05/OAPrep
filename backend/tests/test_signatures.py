"""The rules that decide whether a problem may become functional.

LeetCode publishes the signature and the example inputs but NOT the expected
answers, so those are read from the "Output:" lines of the statement and paired
positionally. That pairing is the one guessy step in the pipeline, and these
tests pin the checks that stop a bad pairing reaching the corpus. A problem left
in stdin mode is recoverable; a problem converted with mismatched answers tells
people their correct solution is wrong.
"""

import sys

sys.path.insert(0, ".")

from ai.corpus.load_signatures import convert, expected_outputs, judge_mode

TWO_SUM = {
    "slug": "two-sum",
    "signature": {"name": "twoSum",
                  "params": [{"name": "nums", "type": "integer[]"},
                             {"name": "target", "type": "integer"}],
                  "return": {"type": "integer[]"}},
    "example_inputs": ["[2,7,11,15]\n9", "[3,2,4]\n6"],
    # The starter must declare the same arguments metaData claims: the loader
    # cross-checks them, because metaData sometimes lists judge setup as a
    # parameter (hasCycle's `pos`, firstBadVersion's `bad`).
    "code_snippets": {
        "python3": "class Solution:\n    def twoSum(self, nums, target): ...",
    },
}
DESCRIPTION = ("Example 1:\nInput: nums = [2,7,11,15], target = 9\nOutput: [0,1]\n"
               "Example 2:\nInput: nums = [3,2,4], target = 6\nOutput: [1,2]\n")


def test_a_well_formed_problem_converts():
    cases, mode, reason = convert(TWO_SUM, DESCRIPTION)
    assert reason == ""
    assert [c["input"] for c in cases] == TWO_SUM["example_inputs"]
    assert [c["expected_output"] for c in cases] == ["[0,1]", "[1,2]"]
    assert mode == "exact"


def test_mismatched_counts_are_refused():
    """The failure mode this whole check exists for: answers sliding by one."""
    cases, _, reason = convert(TWO_SUM, DESCRIPTION + "Output: [9,9]\n")
    assert cases == []
    assert "3 outputs" in reason


def test_an_answer_of_the_wrong_type_is_refused():
    """Catches "Output:" lines scraped from the wrong place in a statement."""
    bad = DESCRIPTION.replace("Output: [1,2]", "Output: true")
    cases, _, reason = convert(TWO_SUM, bad)
    assert cases == []
    assert "not a integer[]" in reason


def test_an_input_with_the_wrong_number_of_arguments_is_refused():
    row = {**TWO_SUM, "example_inputs": ["[2,7,11,15]", "[3,2,4]\n6"]}
    cases, _, reason = convert(row, DESCRIPTION)
    assert cases == []
    assert "1 values for 2 params" in reason


def test_a_class_design_problem_stays_on_stdin():
    """LRU Cache has no function to call; forcing it would break it."""
    cases, _, reason = convert({**TWO_SUM, "signature": {"params": []}}, DESCRIPTION)
    assert cases == []
    assert "no function signature" in reason


def test_a_problem_without_starters_stays_on_stdin():
    cases, _, reason = convert({**TWO_SUM, "code_snippets": {}}, DESCRIPTION)
    assert cases == []
    assert "no starter code" in reason


def test_any_order_is_read_from_the_statement():
    sig = TWO_SUM["signature"]
    assert judge_mode("You can return the answer in any order.", sig) == "unordered"
    assert judge_mode("Return the intervals.", sig) == "exact"


def test_any_order_never_loosens_a_scalar_answer():
    """"in any order" next to an integer return means something else entirely,
    and a loose judge on a scalar would pass wrong answers."""
    scalar = {"name": "f", "params": [], "return": {"type": "integer"}}
    assert judge_mode("You can return the answer in any order.", scalar) == "exact"


def test_output_lines_are_read_in_order():
    assert expected_outputs(DESCRIPTION) == ["[0,1]", "[1,2]"]
    assert expected_outputs("no examples here") == []


def test_metadata_that_lies_about_the_parameters_is_refused():
    """hasCycle's metaData lists a `pos` argument that exists in no language's
    signature. Trusting it means calling the method with an extra argument and
    failing every case with a TypeError the person cannot act on."""
    lying = {**TWO_SUM, "code_snippets": {
        "python3": "class Solution:\n    def twoSum(self, nums): ..."}}
    cases, _, reason = convert(lying, DESCRIPTION)
    assert cases == []
    assert "the real signature takes 1" in reason
