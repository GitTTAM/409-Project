"""Exercise real Tk widgets, while replacing dialogs so tests need no clicking.

These tests skip when Tkinter or a desktop display is unavailable. Pure grammar,
lesson, and feedback tests still run in that environment.
"""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    import tkinter as tk
except ImportError:
    tk = None

from cfg_toolkit import read_document


@unittest.skipIf(tk is None, "Tkinter is not installed")
class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            window = tk.Tk()
        except tk.TclError as error:
            raise unittest.SkipTest("No desktop display: {}".format(error))
        window.withdraw()
        window.destroy()

    def setUp(self):
        from cfg_toolkit.gui import GrammarApp

        self.window = tk.Tk()
        self.window.withdraw()
        self.addCleanup(self.window.destroy)
        self.app = GrammarApp(self.window)
        self.window.update()
        self.save_dialog = self.enterContext(
            patch("cfg_toolkit.gui.filedialog.asksaveasfilename", return_value="")
        )
        self.error_dialog = self.enterContext(
            patch("cfg_toolkit.gui.messagebox.showerror")
        )
        self.replace_dialog = self.enterContext(
            patch("cfg_toolkit.gui.messagebox.askyesno", return_value=False)
        )

    def contents(self, widget):
        return widget.get("1.0", "end-1c")

    def edit_input(self, text, deliver_event=True):
        self.app.editor.delete("1.0", "end")
        self.app.editor.insert("1.0", text)
        if deliver_event:
            self.window.update()

    def test_startup_does_not_claim_validation_or_allow_saving_a_result(self):
        self.assertIsNone(self.app.grammar)
        self.assertIsNone(self.app.preparation)
        self.assertIn("disabled", self.app.save_button.state())
        self.assertIn("S -> aSb", self.contents(self.app.editor))

    def test_prepare_shows_original_new_start_and_added_rule(self):
        self.app.run_button.invoke()
        self.assertEqual(self.app.grammar.start, "S")
        self.assertEqual(self.app.preparation.grammar.start, "S_0")
        self.assertIn("S_0 \u2192 S", self.contents(self.app.prepared_view))
        self.assertTrue(self.app.prepared_view.tag_ranges("added"))
        self.assertIn("Added S_0 -> S.", self.contents(self.app.feedback))
        self.assertNotIn("disabled", self.app.save_button.state())

    def test_help_reopens_without_losing_editor_or_results(self):
        self.assertEqual(self.app.help_window.state(), "withdrawn")
        self.app.run_button.invoke()
        original_text = self.contents(self.app.editor)
        result = self.app.preparation
        help_window = self.app.help_window
        self.app.show_help()
        self.window.update()
        self.assertEqual(help_window.state(), "normal")
        self.assertEqual(self.app.help_notebook.select(), str(self.app.walkthrough))
        help_window.withdraw()
        self.app.show_help("practice")
        self.assertIs(self.app.help_window, help_window)
        self.assertEqual(self.app.help_notebook.select(), str(self.app.practice))
        self.assertEqual(self.contents(self.app.editor), original_text)
        self.assertIs(self.app.preparation, result)

    def test_validate_alone_leaves_start_preparation_pending(self):
        self.assertTrue(self.app.validate_input())
        self.assertIsNone(self.app.preparation)
        self.assertIn("Click Run", self.contents(self.app.prepared_view))

    def test_walkthrough_shows_tuples_while_workspace_shows_grammar(self):
        self.app.run_input()
        self.app.walkthrough_index = 1
        self.app._render_walkthrough()
        self.assertIn("Production('S', ())", self.contents(self.app.walkthrough_text))
        self.assertIn("S_0 \u2192 S", self.contents(self.app.prepared_view))
        self.assertTrue(self.app.prepared_view.tag_ranges("added"))

    def test_edit_clears_results_and_disables_saving(self):
        self.app.run_input()
        self.edit_input("S -> a\n")
        self.assertIsNone(self.app.grammar)
        self.assertIsNone(self.app.preparation)
        self.assertIn("disabled", self.app.save_button.state())
        self.assertNotIn("S_0", self.contents(self.app.prepared_view))
        self.assertTrue(self.app.dirty)

    def test_queued_edit_cannot_save_a_stale_result(self):
        self.app.run_input()
        self.edit_input("S -> a\n", deliver_event=False)
        self.app.save_prepared()
        self.save_dialog.assert_not_called()
        self.assertIsNone(self.app.preparation)

    def test_queued_edit_is_reparsed_before_preparing(self):
        self.app.run_input()
        self.edit_input("S -> a\n", deliver_event=False)
        self.assertTrue(self.app.run_input())
        self.assertFalse(self.app.preparation.added)
        self.assertEqual(self.app.preparation.grammar.start, "S")

    def test_json_paste_is_rejected_with_a_grammar_example(self):
        self.app.run_input()
        self.edit_input('{\n  "variables": ["S"]\n}')
        self.assertFalse(self.app.validate_input())
        self.assertIsNone(self.app.preparation)
        self.assertIn("S -> aSb | epsilon", self.contents(self.app.feedback))

    def test_error_highlights_actual_line_and_explains_correction(self):
        self.app._replace_input("V={S,A,B,C,AB}\nSigma={a}\nStart=S\nS -> ABCa")
        self.assertFalse(self.app.validate_input())
        self.assertEqual(str(self.app.editor.tag_ranges("error_line")[0]), "4.0")
        self.assertIn("Line 4: S -> ABCa", self.contents(self.app.feedback))
        self.assertIn("A B C a", self.contents(self.app.feedback))
        self.assertIn("disabled", self.app.save_button.state())

    def test_invalid_input_clears_a_previous_valid_result(self):
        self.app.run_input()
        self.edit_input("S -> a |")
        self.assertFalse(self.app.run_input())
        self.assertIsNone(self.app.preparation)
        self.assertNotIn("S_0", self.contents(self.app.prepared_view))

    def test_no_change_case_has_no_added_rule_highlight(self):
        self.app._replace_input("S -> a | epsilon")
        self.app.run_input()
        self.assertFalse(self.app.preparation.added)
        self.assertFalse(self.app.prepared_view.tag_ranges("added"))
        self.assertIn("No new start", self.app.status.get())

    def test_repeat_prepare_does_not_add_another_wrapper(self):
        self.app.run_input()
        first = self.app.preparation
        self.app.run_input()
        self.assertEqual(self.app.preparation, first)

    def test_clear_removes_input_and_previous_results(self):
        self.app.run_input()
        self.edit_input("S -> b")
        self.replace_dialog.return_value = True
        self.app.clear_input()
        self.assertEqual(self.contents(self.app.editor), "")
        self.assertIsNone(self.app.grammar)
        self.assertIsNone(self.app.preparation)
        self.assertIsNone(self.app.loaded_path)
        self.assertIn("disabled", self.app.save_button.state())

    def test_unsaved_changes_can_cancel_replacing_input(self):
        self.edit_input("S -> b")
        self.app.clear_input()
        self.assertEqual(self.contents(self.app.editor), "S -> b")
        self.replace_dialog.assert_called_once()

    def test_save_input_preserves_text_and_updates_file_tracking(self):
        self.edit_input("// My example\nS -> a\n")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "my_grammar.cfg"
            self.save_dialog.return_value = str(path)
            self.app.save_input()
            self.assertEqual(
                path.read_text(encoding="utf-8"), self.contents(self.app.editor)
            )
            self.assertEqual(self.app.loaded_path, path.resolve())
            self.assertFalse(self.app.dirty)

    def test_save_prepared_roundtrips_as_grammar_text(self):
        self.app.run_input()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prepared.cfg"
            self.save_dialog.return_value = str(path)
            self.app.save_prepared()
            self.assertEqual(read_document(path), self.app.preparation.grammar)

    def test_saves_reject_non_cfg_names_without_writing(self):
        self.app.run_input()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "output.json"
            self.save_dialog.return_value = str(path)
            self.app.save_input()
            self.app.save_prepared()
            self.assertFalse(path.exists())
            self.assertEqual(self.error_dialog.call_count, 2)

    def test_prepared_output_cannot_overwrite_the_open_input_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "original.cfg"
            path.write_text("S -> aSb | epsilon", encoding="utf-8")
            original = path.read_bytes()
            self.app._load_path(path)
            self.app.run_input()
            self.save_dialog.return_value = str(path)
            self.app.save_prepared()
            self.assertEqual(path.read_bytes(), original)
            self.error_dialog.assert_called_once()

    def test_walkthrough_runs_current_grammar_through_actual_steps(self):
        self.app.show_help()
        self.app._move_walkthrough(1)
        self.assertIn("Production('S',", self.contents(self.app.walkthrough_text))
        self.app._move_walkthrough(1)
        self.assertIn("Validation passed", self.contents(self.app.walkthrough_text))
        self.app._move_walkthrough(1)
        self.assertIn("Prepared start: S_0", self.contents(self.app.walkthrough_text))
        self.assertEqual(self.app.walkthrough_index, 3)
        self.assertIn("disabled", self.app.next_button.state())

    def test_walkthrough_stops_on_bad_input(self):
        self.app._replace_input("S ->")
        self.app.show_help()
        self.app._move_walkthrough(1)
        self.assertEqual(self.app.walkthrough_index, 0)
        self.assertIsNone(self.app.grammar)
        self.assertEqual(self.app.help_window.state(), "withdrawn")

    def test_practice_answer_and_actual_test_can_be_opened(self):
        from cfg_toolkit.learning import LESSONS

        self.app.lesson_index = 0
        self.app._show_lesson()
        self.app._reveal_answer()
        self.assertIn("one symbol", self.contents(self.app.answer_text))
        popup = self.app.show_code(LESSONS[0].test)
        self.assertIsNotNone(popup)
        popup.withdraw()
        popup.destroy()

    def test_each_example_loads_and_only_intentional_bad_input_fails(self):
        from cfg_toolkit.gui import EXAMPLES

        for name, relative in EXAMPLES:
            with self.subTest(example=name):
                self.assertTrue(self.app._load_path(self.app.root / relative))
                self.assertEqual(self.app.validate_input(), "fix me" not in name)


if __name__ == "__main__":
    unittest.main()
