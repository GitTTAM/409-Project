"""Check that lessons match the real code and explain the real grammar results."""

from pathlib import Path
import unittest

from cfg_toolkit import Grammar, Production, loads_document, prepare_start
from cfg_toolkit.gui_support import added_rule_lines, explain_input_error
from cfg_toolkit.learning import (
    CodeReference,
    LESSONS,
    ROOT,
    read_code,
    run_start_check_demo,
    tuple_view,
    walkthrough_steps,
)
from support import bounded_language


class LearningTests(unittest.TestCase):
    def test_all_five_lessons_point_to_existing_code_and_tests(self):
        self.assertEqual(len(LESSONS), 5)
        for lesson in LESSONS:
            with self.subTest(lesson=lesson.title):
                for reference in (lesson.code, lesson.test):
                    text, first, last = read_code(reference)
                    self.assertIn(
                        reference.name.split(".")[-1], text.splitlines()[first - 1]
                    )
                    self.assertLessEqual(first, last)
                    self.assertTrue(lesson.exercise)

    def test_source_reader_rejects_escape_and_missing_function(self):
        for reference in (
            CodeReference("../outside.py", "thing"),
            CodeReference("cfg_toolkit/model.py", "missing"),
        ):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                read_code(reference)

    def test_tuple_view_shows_two_symbols_one_symbol_and_empty_rhs(self):
        grammar = loads_document(
            "V={S,A,B,AB}\nSigma={a,b}\nStart=S\nS -> A B | AB | epsilon\nA -> a\nB -> b\nAB -> a"
        )
        text = tuple_view(grammar)
        for expected in (
            "Production('S', ('A', 'B'))",
            "Production('S', ('AB',))",
            "Production('S', ())",
        ):
            self.assertIn(expected, text)

    def test_practice_token_grammar_has_the_explained_language(self):
        text = (ROOT / "examples/practice/token_names.cfg").read_text(encoding="utf-8")
        original = loads_document(text)
        changed = loads_document(text.replace("S -> A B | AB", "S -> A B"))
        self.assertEqual(bounded_language(original), {("a",), ("a", "b")})
        self.assertEqual(bounded_language(changed), {("a", "b")})

    def test_epsilon_exercise_really_changes_the_empty_word_to_e(self):
        original = loads_document("V={S}\nSigma={a,b}\nStart=S\nS -> aSb | epsilon")
        changed = loads_document("V={S}\nSigma={a,b,e}\nStart=S\nS -> aSb | e")
        self.assertIn((), bounded_language(original))
        self.assertNotIn((), bounded_language(changed))
        self.assertIn(("e",), bounded_language(changed))

    def test_empty_language_tuple_view_is_explicit(self):
        self.assertIn("No productions", tuple_view(Grammar(["S"], [], [], "S")))

    def test_walkthrough_does_not_claim_unrun_steps_finished(self):
        steps = walkthrough_steps(None, None)
        self.assertEqual(len(steps), 4)
        self.assertIn("not run", steps[2].text)
        self.assertIn("Click Run", steps[3].text)

    def test_walkthrough_uses_current_original_and_prepared_names(self):
        grammar = loads_document("Begin -> aBegin | epsilon")
        prepared = prepare_start(grammar)
        steps = walkthrough_steps(grammar, prepared)
        self.assertIn("Production('Begin',", steps[1].text)
        self.assertIn("Validation passed", steps[2].text)
        self.assertIn("Original start: Begin", steps[3].text)
        self.assertIn("Prepared start: Begin_0", steps[3].text)

    def test_real_assertion_fails_for_wrong_result_and_passes_for_actual_result(self):
        output = run_start_check_demo()
        self.assertIn("FAIL: True is not false", output)
        self.assertIn("PASS: the prepared start S_0", output)
        self.assertIn("assertFalse", output)


class FeedbackTests(unittest.TestCase):
    def test_ambiguity_keeps_actual_line_and_adds_spacing_example(self):
        text = "V={S,A,B,C,AB}\nSigma={a}\nStart=S\nS -> ABCa"
        try:
            loads_document(text)
        except ValueError as error:
            problem = explain_input_error(error)
        else:
            self.fail("This example must be ambiguous")
        self.assertEqual(problem.line, 4)
        self.assertIsNone(problem.column)
        self.assertIn("Line 4: S -> ABCa", problem.display(text))
        self.assertIn("A B C a", problem.hint)

    def test_json_error_has_real_column_and_caret(self):
        text = '{"variables": }'
        try:
            loads_document(text)
        except ValueError as error:
            problem = explain_input_error(error)
        else:
            self.fail("This JSON must be invalid")
        self.assertEqual(problem.line, 1)
        self.assertIsNotNone(problem.column)
        self.assertIn("^", problem.display(text))
        self.assertIn("S -> aSb | epsilon", problem.hint)

    def test_empty_alternative_gets_epsilon_example(self):
        problem = explain_input_error(
            ValueError("line 2: empty alternative; write epsilon explicitly")
        )
        self.assertIn("S -> a | epsilon", problem.hint)

    def test_unknown_location_is_not_invented(self):
        problem = explain_input_error(
            ValueError("variables and terminals must be disjoint")
        )
        self.assertIsNone(problem.line)
        self.assertNotIn("Line ", problem.display("S -> a"))
        self.assertIn("different names", problem.hint)

    def test_only_new_rule_is_highlighted_with_name_collision(self):
        grammar = Grammar(
            ["S", "S_0"],
            ["S_1", "a"],
            [Production("S", ("S",)), Production("S", ("a",))],
            "S",
        )
        self.assertEqual(added_rule_lines(prepare_start(grammar)), {"S_2 \u2192 S"})

    def test_no_added_rule_when_start_is_isolated(self):
        self.assertEqual(
            added_rule_lines(prepare_start(loads_document("S -> a | epsilon"))), set()
        )

    def test_escaped_unicode_start_is_highlighted_as_displayed(self):
        grammar = Grammar(
            ["\u0393"], ["a"], [Production("\u0393", ("a", "\u0393"))], "\u0393"
        )
        self.assertEqual(len(added_rule_lines(prepare_start(grammar))), 1)


if __name__ == "__main__":
    unittest.main()
