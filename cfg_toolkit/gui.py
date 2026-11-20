"""The team's grammar workshop, with input and integration led by Matt Lawrence.

This file handles widgets and file dialogs. Grammar parsing, validation, and
start preparation still come from the same modules used by the command line.
"""

from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .gui_support import explain_input_error
from .learning import (
    LESSONS,
    ROOT,
    read_code,
    run_start_check_demo,
    walkthrough_steps,
)
from .lecture import dumps_lecture, loads_lecture
from .model import GrammarError
from .start_symbol import prepare_start
from .pipeline import run_pipeline


EXAMPLES = (
    ("Recursive grammar", "examples/lecture/03_matching.cfg"),
    ("Nullable variables", "examples/lecture/05_nullable_units.cfg"),
    ("Whole names: A B vs AB", "examples/practice/token_names.cfg"),
    ("No new start needed", "examples/practice/isolated_start.cfg"),
    ("Ambiguous input (fix me)", "examples/practice/ambiguous.cfg"),
)
FILE_TYPES = (("Grammar", "*.cfg"),)
PENDING_NOTE = "Next: Devin's CNF steps. Full conversion is still pending."


class GrammarApp:
    """Keep current input and results together, and discard results after an edit."""

    def __init__(self, window, root=ROOT):
        self.window = window
        self.root = Path(root)
        self.grammar = None
        self.preparation = None
        self.pipeline_result = None
        self.validated_input = None
        self.loaded_path = None
        self.dirty = False
        self.walkthrough_index = 0
        self.lesson_index = 0
        self.status = tk.StringVar(value="Load an example or paste a grammar to begin.")
        self.example_name = tk.StringVar(value=EXAMPLES[0][0])
        self.step_title = tk.StringVar()
        self.question = tk.StringVar()
        self.window.title("409 CFG | Grammar workshop")
        self.window.geometry("1240x900")
        self.window.minsize(1000, 740)
        self._set_style()
        self._build_window()
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Control-Return>", lambda event: self.run_input())
        self._load_path(self.root / EXAMPLES[0][1])
        self._show_lesson()

    def _set_style(self):
        style = ttk.Style(self.window)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background="#f2f5fa")
        style.configure("TLabel", background="#f2f5fa", foreground="#24354b")
        style.configure("Title.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("TButton", padding=(12, 7))
        style.configure("Accent.TButton", background="#245cc7", foreground="white")
        style.map(
            "Accent.TButton",
            background=[("active", "#174aa9"), ("disabled", "#d7dfed")],
        )
        style.configure("TNotebook", background="#f2f5fa", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(18, 9))
        self.window.configure(background="#f2f5fa")

    @staticmethod
    def _text(parent, height=10, wrap="word", code=False):
        view = ScrolledText(
            parent,
            height=height,
            wrap=wrap,
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=10,
            font=("Consolas", 10) if code else ("Segoe UI", 11),
            background="white",
            foreground="#24354b",
            insertbackground="#245cc7",
        )
        view.configure(state="disabled")
        return view

    @staticmethod
    def _put(view, text):
        view.configure(state="normal")
        view.delete("1.0", "end")
        view.insert("1.0", text)
        view.configure(state="disabled")

    def _build_window(self):
        header = tk.Frame(self.window, background="#162b49", padx=22, pady=16)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Grammar workshop",
            font=("Segoe UI", 20, "bold"),
            background="#162b49",
            foreground="white",
        ).pack(anchor="w")
        tk.Label(
            header,
            text="409 CFG  /  Matt Lawrence, Steven Yang, Devin Finn",
            font=("Segoe UI", 10),
            background="#162b49",
            foreground="#c9d8ee",
        ).pack(anchor="w", pady=(4, 0))
        self.workspace = ttk.Frame(self.window, padding=12)
        self.workspace.pack(fill="both", expand=True, padx=16, pady=(12, 6))
        self._build_workspace()

        # Keep lessons in one reusable window, out of the main work area.
        self.help_window = tk.Toplevel(self.window)
        self.help_window.withdraw()
        self.help_window.title("Help | Grammar workshop")
        self.help_window.geometry("1120x760")
        self.help_window.minsize(1000, 640)
        self.help_window.protocol("WM_DELETE_WINDOW", self.help_window.withdraw)
        self.help_window.bind("<Escape>", lambda event: self.help_window.withdraw())
        self.help_notebook = ttk.Notebook(self.help_window)
        self.help_notebook.pack(fill="both", expand=True, padx=12, pady=12)
        self.walkthrough = ttk.Frame(self.help_notebook, padding=18)
        self.practice = ttk.Frame(self.help_notebook, padding=18)
        self.help_notebook.add(self.walkthrough, text="Walkthrough")
        self.help_notebook.add(self.practice, text="Practice")
        self._build_walkthrough()
        self._build_practice()
        ttk.Label(self.window, textvariable=self.status, padding=(20, 6)).pack(fill="x")

    def show_help(self, section="walkthrough"):
        """Open a lesson without replacing input or resetting the current results."""
        self._refresh_if_edited()
        page = self.practice if section == "practice" else self.walkthrough
        self.help_notebook.select(page)
        self.help_window.deiconify()
        self.help_window.lift()

    def _build_workspace(self):
        self.workspace.columnconfigure(0, weight=1)
        self.workspace.rowconfigure(2, weight=1)
        self.workspace.rowconfigure(5, weight=1)
        files = ttk.Frame(self.workspace)
        files.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(files, text="Save input...", command=self.save_input).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(files, text="Clear", command=self.clear_input).pack(side="left")
        help_button = ttk.Menubutton(files, text="Help")
        help_menu = tk.Menu(help_button, tearoff=False)
        help_menu.add_command(label="Walkthrough", command=self.show_help)
        help_menu.add_command(
            label="Practice", command=lambda: self.show_help("practice")
        )
        help_button.configure(menu=help_menu)
        help_button.pack(side="right")

        examples = ttk.Frame(self.workspace)
        examples.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(examples, text="Example").pack(side="left", padx=(0, 8))
        ttk.Combobox(
            examples,
            textvariable=self.example_name,
            values=[name for name, _ in EXAMPLES],
            state="readonly",
            width=29,
        ).pack(side="left")
        ttk.Button(examples, text="Load example", command=self.load_example).pack(
            side="left", padx=8
        )

        upper = ttk.Panedwindow(self.workspace, orient="horizontal")
        upper.grid(row=2, column=0, sticky="nsew")
        input_panel = ttk.Frame(upper)
        input_panel.columnconfigure(0, weight=1)
        input_panel.rowconfigure(1, weight=1)
        ttk.Label(
            input_panel, text="Paste or edit a grammar", style="Title.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 7))
        self.editor = ScrolledText(
            input_panel,
            height=9,
            wrap="none",
            undo=True,
            relief="flat",
            padx=12,
            pady=10,
            font=("Consolas", 11),
            foreground="#24354b",
        )
        self.editor.grid(row=1, column=0, sticky="nsew")
        horizontal = ttk.Scrollbar(
            input_panel, orient="horizontal", command=self.editor.xview
        )
        horizontal.grid(row=2, column=0, sticky="ew")
        self.editor.configure(xscrollcommand=horizontal.set)
        self.editor.tag_configure(
            "error_line", background="#fee2e2", foreground="#8b2020"
        )
        self.editor.bind("<<Modified>>", self._input_changed)
        self.editor.edit_modified(False)
        upper.add(input_panel, weight=3)
        feedback_panel = ttk.Frame(upper, padding=(12, 0, 0, 0))
        ttk.Label(feedback_panel, text="What happened", style="Title.TLabel").pack(
            anchor="w", pady=(0, 7)
        )
        self.feedback = self._text(feedback_panel, height=9)
        self.feedback.pack(fill="both", expand=True)
        upper.add(feedback_panel, weight=2)

        actions = ttk.Frame(self.workspace)
        actions.grid(row=3, column=0, sticky="ew", pady=10)
        self.run_button = ttk.Button(
            actions,
            text="Run",
            style="Accent.TButton",
            command=self.run_input,
        )
        self.run_button.pack(side="left", padx=(0, 8))
        self.save_button = ttk.Button(
            actions,
            text="Save result...",
            command=self.save_result,
            state="disabled",
        )
        self.save_button.pack(side="left")
        ttk.Label(
            self.workspace,
            text="Green = new or changed rule   |   Blue = changed declaration",
            foreground="#34634b",
        ).grid(row=4, column=0, sticky="w", pady=(0, 6))
        comparison = ttk.Panedwindow(self.workspace, orient="horizontal")
        comparison.grid(row=5, column=0, sticky="nsew")
        self.original_view = self._comparison_panel(comparison, "Original grammar")
        self.result_view = self._comparison_panel(comparison, "After Steven's steps")
        ttk.Label(self.workspace, text=PENDING_NOTE, wraplength=1080).grid(
            row=6, column=0, sticky="w", pady=(9, 0)
        )

    def _comparison_panel(self, parent, title):
        panel = ttk.Frame(parent, padding=(0, 0, 10, 0))
        ttk.Label(panel, text=title, style="Title.TLabel").pack(anchor="w", pady=(0, 7))
        text = self._text(panel, height=9, code=True)
        text.pack(fill="both", expand=True)
        text.tag_configure("added", background="#d5f3df", foreground="#155b35")
        text.tag_configure("declaration", background="#e4edff")
        parent.add(panel, weight=1)
        return text

    def _build_walkthrough(self):
        ttk.Label(
            self.walkthrough,
            text="Follow the grammar currently in your workspace",
            style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            self.walkthrough,
            text="Next runs validation or start preparation when that step needs it.",
        ).pack(anchor="w", pady=(6, 18))
        ttk.Label(
            self.walkthrough,
            textvariable=self.step_title,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 10))
        self.walkthrough_text = self._text(self.walkthrough, height=18, code=True)
        self.walkthrough_text.pack(fill="both", expand=True)
        navigation = ttk.Frame(self.walkthrough)
        navigation.pack(fill="x", pady=12)
        self.back_button = ttk.Button(
            navigation, text="Back", command=lambda: self._move_walkthrough(-1)
        )
        self.back_button.pack(side="left")
        self.next_button = ttk.Button(
            navigation,
            text="Next",
            style="Accent.TButton",
            command=lambda: self._move_walkthrough(1),
        )
        self.next_button.pack(side="left", padx=8)
        self.walkthrough_source_button = ttk.Button(
            navigation, text="Show Python function", command=self._show_walkthrough_code
        )
        self.walkthrough_source_button.pack(side="left", padx=8)
        ttk.Label(self.walkthrough, text=PENDING_NOTE).pack(anchor="w")

    def _build_practice(self):
        ttk.Label(
            self.practice,
            text="Explain it aloud, then try one small change",
            style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            self.practice,
            text="Pick a question, reveal its explanation, and compare it with the real code.",
        ).pack(anchor="w", pady=(6, 16))
        body = ttk.Frame(self.practice)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self.lesson_list = tk.Listbox(
            body,
            width=29,
            height=7,
            font=("Segoe UI", 11),
            relief="flat",
            activestyle="none",
            exportselection=False,
            selectbackground="#245cc7",
            selectforeground="white",
        )
        self.lesson_list.grid(row=0, column=0, sticky="ns", padx=(0, 18))
        for lesson in LESSONS:
            self.lesson_list.insert("end", lesson.title)
        self.lesson_list.selection_set(0)
        self.lesson_list.bind("<<ListboxSelect>>", self._lesson_selected)
        detail = ttk.Frame(body)
        detail.grid(row=0, column=1, sticky="nsew")
        self.question_label = ttk.Label(
            detail,
            textvariable=self.question,
            font=("Segoe UI", 14, "bold"),
            wraplength=730,
        )
        self.question_label.pack(anchor="w", pady=(0, 12))
        detail.bind(
            "<Configure>",
            lambda event: self.question_label.configure(
                wraplength=max(200, event.width - 8)
            ),
        )
        self.answer_text = self._text(detail, height=8)
        self.answer_text.pack(fill="both", expand=True)
        buttons = ttk.Frame(detail)
        buttons.pack(fill="x", pady=10)
        ttk.Button(
            buttons, text="Reveal explanation", command=self._reveal_answer
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Show implementation",
            command=lambda: self.show_code(LESSONS[self.lesson_index].code),
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons,
            text="Show real test",
            command=lambda: self.show_code(LESSONS[self.lesson_index].test),
        ).pack(side="left")
        ttk.Label(detail, text="Try it yourself", style="Title.TLabel").pack(
            anchor="w", pady=(8, 6)
        )
        self.exercise_text = self._text(detail, height=6)
        self.exercise_text.pack(fill="both", expand=True)
        self.demo_button = ttk.Button(
            detail,
            text="Run test demonstration",
            command=self._show_test_demo,
            state="disabled",
        )
        self.demo_button.pack(anchor="w", pady=(12, 0))

    def _invalidate_results(self, message):
        self.grammar = None
        self.preparation = None
        self.pipeline_result = None
        self.validated_input = None
        self.save_button.configure(state="disabled")
        self.editor.tag_remove("error_line", "1.0", "end")
        self._render_results()
        self._put(self.feedback, message)
        self.status.set(message)
        self._render_walkthrough()

    def _input_changed(self, event=None):
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        self.dirty = True
        self._invalidate_results("Input changed. Click Run to refresh the results.")

    def _refresh_if_edited(self):
        """Handle an edit even if Tk has not delivered its Modified event yet."""
        if self.editor.edit_modified():
            self._input_changed()
        elif self.grammar is not None:
            current = self.editor.get("1.0", "end-1c")
            if current != self.validated_input:
                self._invalidate_results("Input changed. Click Run again.")

    def _replace_input(self, text, path=None):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.editor.edit_modified(False)
        self.editor.edit_reset()
        self.loaded_path = Path(path).resolve() if path else None
        self.dirty = False
        self.walkthrough_index = 0
        self._invalidate_results("Ready. Click Run to check and prepare the grammar.")

    def _confirm_replace(self):
        self._refresh_if_edited()
        return not self.dirty or messagebox.askyesno(
            "Replace edited input?",
            "Your editor has unsaved changes. Replace them?",
            parent=self.window,
        )

    def _load_path(self, path):
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            messagebox.showerror(
                "Could not load example", str(error), parent=self.window
            )
            return False
        self._replace_input(text, path)
        return True

    def load_example(self):
        if self._confirm_replace():
            self._load_path(self.root / dict(EXAMPLES)[self.example_name.get()])

    def clear_input(self):
        if self._confirm_replace():
            self._replace_input("")

    def validate_input(self):
        self._refresh_if_edited()
        text = self.editor.get("1.0", "end-1c")
        self.editor.edit_modified(False)
        try:
            grammar = loads_lecture(text)
        except GrammarError as error:
            self._invalidate_results(
                "Input needs a fix. See the message beside the editor."
            )
            problem = explain_input_error(error)
            self._put(self.feedback, problem.display(text))
            if problem.line is not None and problem.line <= int(
                self.editor.index("end-1c").split(".")[0]
            ):
                self.editor.tag_add(
                    "error_line",
                    "{}.0".format(problem.line),
                    "{}.end+1c".format(problem.line),
                )
                self.editor.see("{}.0".format(problem.line))
            self.help_window.withdraw()
            self.window.lift()
            self.editor.focus_set()
            return False
        self.grammar = grammar
        self.preparation = None
        self.pipeline_result = None
        self.validated_input = text
        self.save_button.configure(state="disabled")
        self.editor.tag_remove("error_line", "1.0", "end")
        self._render_results()
        self._put(self.feedback, "Valid grammar.\n\nClick Run to continue.")
        self.status.set("Validation passed.")
        self._render_walkthrough()
        return True

    def run_input(self):
        """Run every available step and show the grammar ready for Devin."""
        self._refresh_if_edited()
        if self.grammar is None and not self.validate_input():
            return False
        self.preparation = prepare_start(self.grammar)
        self.pipeline_result = run_pipeline(self.grammar)
        self._render_results()
        self.save_button.configure(state="normal")
        if self.preparation.added:
            message = "{} appears on a right side.\n\nAdded {} -> {}.".format(
                self.grammar.start, self.preparation.new_start, self.grammar.start
            )
        else:
            message = (
                "{} never appears on a right side.\n\nNo new start needed.".format(
                    self.grammar.start
                )
            )
        self._put(
            self.feedback,
            message + "\n\nSteven's steps finished: epsilon and unit rules removed."
            "\n\nNext: Devin's CNF steps.",
        )
        self.status.set(
            "Run finished. "
            + (
                "Result is ready for Devin."
                if self.preparation.added
                else "No new start was needed."
            )
        )
        self._render_walkthrough()
        return True

    def _render_results(self):
        if self.grammar is None:
            self._put(
                self.original_view,
                "Click Run to check the current input.",
            )
        else:
            self._put(self.original_view, dumps_lecture(self.grammar))
        if self.pipeline_result is None:
            self._put(
                self.result_view,
                "Click Run to see the result after epsilon and unit removal.",
            )
            return
        original = dumps_lecture(self.grammar)
        current = dumps_lecture(self.pipeline_result.snapshots[-1].grammar)
        self._put(self.result_view, current)
        original_lines = set(original.splitlines())
        for number, line in enumerate(current.splitlines(), 1):
            tag = None
            if line not in original_lines:
                tag = (
                    "declaration"
                    if line.startswith(("V =", "Sigma =", "Start ="))
                    else "added"
                )
            if tag:
                self.result_view.tag_add(
                    tag, "{}.0".format(number), "{}.end+1c".format(number)
                )

    def _choose_save_path(self, title, filename):
        filename = filedialog.asksaveasfilename(
            parent=self.window,
            title=title,
            initialfile=filename,
            defaultextension=".cfg",
            filetypes=FILE_TYPES,
        )
        if not filename:
            return None
        path = Path(filename).resolve()
        if path.suffix.lower() != ".cfg":
            messagebox.showerror(
                "Save grammar", "Use a .cfg filename.", parent=self.window
            )
            return None
        return path

    def save_input(self):
        self._refresh_if_edited()
        text = self.editor.get("1.0", "end-1c")
        path = self._choose_save_path("Save input", "my_grammar.cfg")
        if path is None:
            return
        try:
            path.write_text(text, encoding="utf-8")
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Could not save input", str(error), parent=self.window)
            return
        self.loaded_path = path
        self.dirty = False
        self.editor.edit_modified(False)
        self.status.set("Saved input: {}".format(path.name))

    def save_result(self):
        self._refresh_if_edited()
        if self.pipeline_result is None:
            return
        path = self._choose_save_path("Save current result", "for_devin.cfg")
        if path is None:
            return
        try:
            if self.loaded_path is not None and path == self.loaded_path:
                raise GrammarError(
                    "Result must not overwrite the input file. Choose another name."
                )
            current = self.pipeline_result.snapshots[-1].grammar
            path.write_text(dumps_lecture(current), encoding="utf-8")
        except (GrammarError, OSError, UnicodeError) as error:
            messagebox.showerror(
                "Could not save result", str(error), parent=self.window
            )
            return
        self.status.set("Saved result: {}".format(path.name))

    def _render_walkthrough(self):
        step = walkthrough_steps(self.grammar, self.preparation)[self.walkthrough_index]
        self.step_title.set(step.title + "  /  4")
        self._put(self.walkthrough_text, step.text)
        self.walkthrough_source_button.configure(text="Show " + step.code.name + "()")
        self.back_button.configure(
            state="normal" if self.walkthrough_index else "disabled"
        )
        self.next_button.configure(
            state="normal" if self.walkthrough_index < 3 else "disabled"
        )

    def _move_walkthrough(self, direction):
        self._refresh_if_edited()
        target = max(0, min(3, self.walkthrough_index + direction))
        if target >= 1 and self.grammar is None and not self.validate_input():
            return
        if target == 3 and self.preparation is None and not self.run_input():
            return
        self.walkthrough_index = target
        self._render_walkthrough()

    def _show_walkthrough_code(self):
        step = walkthrough_steps(self.grammar, self.preparation)[self.walkthrough_index]
        self.show_code(step.code)

    def _lesson_selected(self, event=None):
        selection = self.lesson_list.curselection()
        if selection:
            self.lesson_index = selection[0]
            self._show_lesson()

    def _show_lesson(self):
        lesson = LESSONS[self.lesson_index]
        self.question.set(lesson.question)
        self._put(
            self.answer_text,
            "Try answering in your own words first. Then reveal the explanation and compare it with the actual code.",
        )
        self._put(self.exercise_text, lesson.exercise)
        self.demo_button.configure(
            state="normal" if self.lesson_index == 4 else "disabled"
        )

    def _reveal_answer(self):
        self._put(self.answer_text, LESSONS[self.lesson_index].answer)

    def _show_test_demo(self):
        popup = tk.Toplevel(self.window)
        popup.title("How a test catches the wrong start")
        popup.geometry("850x470")
        text = self._text(popup, code=True)
        text.pack(fill="both", expand=True, padx=12, pady=12)
        self._put(text, run_start_check_demo())

    def show_code(self, reference):
        try:
            source, first, last = read_code(reference, self.root)
        except (OSError, UnicodeError, ValueError, SyntaxError) as error:
            messagebox.showerror(
                "Could not open source", str(error), parent=self.window
            )
            return None
        popup = tk.Toplevel(self.window)
        popup.title(reference.path + " | " + reference.name)
        popup.geometry("1000x680")
        ttk.Label(
            popup, text=reference.path + "  /  " + reference.name, padding=12
        ).pack(anchor="w")
        text = self._text(popup, code=True, wrap="none")
        text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self._put(
            text,
            "\n".join(
                "{:4}  {}".format(number, line)
                for number, line in enumerate(source.splitlines(), 1)
            ),
        )
        text.tag_configure("function", background="#e4edff")
        text.tag_add("function", "{}.0".format(first), "{}.end+1c".format(last))
        text.see("{}.0".format(max(1, first - 2)))
        popup.bind("<Escape>", lambda event: popup.destroy())
        return popup

    def close(self):
        if self._confirm_replace():
            self.window.destroy()


def main() -> int:
    try:
        window = tk.Tk()
    except tk.TclError as error:
        print(
            "Could not open the desktop window: {}. Run on a desktop with Tkinter installed.".format(
                error
            ),
            file=sys.stderr,
        )
        return 2
    GrammarApp(window)
    window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
