from __future__ import annotations

import os
import threading
from pathlib import Path
from tkinter import BooleanVar, PhotoImage, StringVar, Text, Tk, filedialog, messagebox, simpledialog, ttk

from document_processor import APP_TITLE, process_file
from models import ProcessOptions, ProcessResult


APP_ROOT = Path(__file__).resolve().parents[1]
APP_ICON_PATH = APP_ROOT / "assets" / "statement-mark.ico"
APP_LOGO_PATH = APP_ROOT / "assets" / "statements-logo.png"
PLACEHOLDER_TEXT = (
    "Describe what you want done... Be specific. Example: Markup all prices by 1.35 except Product Supply and "
    "Installation which should be 1.38. Then add Net Total, HST at 13%, Total, Deposit and Balance."
)


class InstructionText(Text):
    def __init__(self, master, placeholder: str, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.placeholder_active = False
        self.configure(wrap="word", undo=True)
        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._show_placeholder_if_empty)
        self.show_placeholder()

    def show_placeholder(self) -> None:
        self.placeholder_active = True
        self.configure(foreground="#7a7f87")
        self.delete("1.0", "end")
        self.insert("1.0", self.placeholder)

    def get_user_text(self) -> str:
        if self.placeholder_active:
            return ""
        return self.get("1.0", "end").strip()

    def _clear_placeholder(self, _event=None) -> None:
        if not self.placeholder_active:
            return
        self.placeholder_active = False
        self.configure(foreground="#1f2933")
        self.delete("1.0", "end")

    def _show_placeholder_if_empty(self, _event=None) -> None:
        if not self.get("1.0", "end").strip():
            self.show_placeholder()


class DadMarkupApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("760x620")
        self.root.minsize(720, 580)
        if APP_ICON_PATH.exists():
            self.root.iconbitmap(str(APP_ICON_PATH))

        self.selected_file: Path | None = None
        self.last_output_dir: Path | None = None
        self.current_instructions = ""
        self.pending_instructions = ""
        self.round_var = BooleanVar(value=True)
        self.file_var = StringVar(value="No file selected")
        self.status_var = StringVar(value="Select a document, describe the changes, then process.")

        self.configure_styles()
        self.build_layout()

    def configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#f4f6f8")
        style.configure("App.TFrame", background="#f4f6f8")
        style.configure("Panel.TFrame", background="#ffffff", relief="flat")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), background="#ffffff", foreground="#17202a")
        style.configure("Body.TLabel", background="#ffffff", foreground="#344054")
        style.configure("Muted.TLabel", background="#ffffff", foreground="#667085")
        style.configure("Status.TLabel", background="#f4f6f8", foreground="#344054")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(18, 11))
        style.configure("Secondary.TButton", padding=(14, 9))
        style.configure("TCheckbutton", background="#ffffff", foreground="#344054")

    def build_layout(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=(24, 20))
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        panel = ttk.Frame(outer, style="Panel.TFrame", padding=(28, 24))
        panel.grid(row=0, column=0, sticky="ew")
        panel.columnconfigure(1, weight=1)

        self.logo_image = PhotoImage(file=str(APP_LOGO_PATH)) if APP_LOGO_PATH.exists() else None
        if self.logo_image is not None:
            ttk.Label(panel, image=self.logo_image, background="#ffffff").grid(row=0, column=0, rowspan=2, padx=(0, 18), sticky="n")

        ttk.Label(panel, text=APP_TITLE, style="Title.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(
            panel,
            text="Process PDF and Word statements from plain-English instructions without changing the original file.",
            style="Muted.TLabel",
        ).grid(row=1, column=1, sticky="w", pady=(5, 0))

        work = ttk.Frame(outer, style="Panel.TFrame", padding=(28, 24))
        work.grid(row=1, column=0, sticky="nsew", pady=(18, 0))
        work.columnconfigure(0, weight=1)
        work.rowconfigure(3, weight=1)

        file_row = ttk.Frame(work, style="Panel.TFrame")
        file_row.grid(row=0, column=0, sticky="ew")
        file_row.columnconfigure(1, weight=1)
        ttk.Button(file_row, text="Select PDF or Word File", style="Secondary.TButton", command=self.select_file).grid(row=0, column=0, sticky="w")
        ttk.Label(file_row, textvariable=self.file_var, style="Body.TLabel", wraplength=470).grid(row=0, column=1, sticky="w", padx=(14, 0))

        ttk.Label(work, text="Instructions", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=(22, 8))
        text_frame = ttk.Frame(work, style="Panel.TFrame")
        text_frame.grid(row=2, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.instructions_text = InstructionText(
            text_frame,
            PLACEHOLDER_TEXT,
            height=9,
            padx=12,
            pady=10,
            borderwidth=1,
            relief="solid",
            font=("Segoe UI", 10),
            insertbackground="#17202a",
        )
        self.instructions_text.grid(row=0, column=0, sticky="nsew")

        options_row = ttk.Frame(work, style="Panel.TFrame")
        options_row.grid(row=4, column=0, sticky="ew", pady=(18, 0))
        options_row.columnconfigure(3, weight=1)
        ttk.Checkbutton(
            options_row,
            text="Round to nearest whole dollar",
            variable=self.round_var,
        ).grid(row=0, column=0, sticky="w")
        self.process_button = ttk.Button(options_row, text="Process Document", style="Primary.TButton", command=self.process_document)
        self.process_button.grid(row=0, column=1, padx=(18, 0))
        self.adjust_button = ttk.Button(
            options_row,
            text="Make Adjustments",
            style="Secondary.TButton",
            command=self.make_adjustments,
        )
        self.adjust_button.grid(row=0, column=2, padx=(12, 0))
        self.adjust_button.grid_remove()
        self.open_folder_button = ttk.Button(
            options_row,
            text="Open Output Folder",
            style="Secondary.TButton",
            command=self.open_output_folder,
            state="disabled",
        )
        self.open_folder_button.grid(row=0, column=3, sticky="e")

        ttk.Label(outer, textvariable=self.status_var, style="Status.TLabel", wraplength=700).grid(row=2, column=0, sticky="ew", pady=(12, 0))

    def select_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select a PDF or Word document",
            filetypes=(
                ("PDF and Word documents", "*.pdf *.docx *.doc"),
                ("PDF files", "*.pdf"),
                ("Word files", "*.docx *.doc"),
                ("All files", "*.*"),
            ),
        )
        if not selected:
            return
        self.selected_file = Path(selected)
        self.file_var.set(self.selected_file.name)
        self.current_instructions = ""
        self.pending_instructions = ""
        self.adjust_button.grid_remove()
        self.open_folder_button.configure(state="disabled")
        self.status_var.set("Document selected. Add instructions and click Process Document.")

    def process_document(self) -> None:
        if self.selected_file is None:
            messagebox.showwarning(APP_TITLE, "Select a PDF or Word file first.")
            return
        instructions = self.instructions_text.get_user_text()
        if not instructions:
            messagebox.showwarning(APP_TITLE, "Describe what you want done before processing.")
            return

        self.start_processing(instructions, "Processing document...")

    def make_adjustments(self) -> None:
        if self.selected_file is None:
            messagebox.showwarning(APP_TITLE, "Select a PDF or Word file first.")
            return
        if not self.current_instructions:
            messagebox.showwarning(APP_TITLE, "Process the document once before making adjustments.")
            return

        correction = simpledialog.askstring(
            APP_TITLE,
            "Type the correction to apply.\n\nExamples:\nChange Product Supply markup to 1.38\nAdd $5000 to the deposit",
            parent=self.root,
        )
        if not correction or not correction.strip():
            return
        combined_instructions = f"{self.current_instructions}\nAdjustment: {correction.strip()}"
        self.start_processing(combined_instructions, "Applying adjustments...")

    def start_processing(self, instructions: str, status: str) -> None:
        if self.selected_file is None:
            messagebox.showwarning(APP_TITLE, "Select a PDF or Word file first.")
            return
        self.pending_instructions = instructions
        self.set_busy(True)
        self.status_var.set(status)
        options = ProcessOptions(round_to_whole_dollar=self.round_var.get())
        thread = threading.Thread(target=self.run_processing, args=(self.selected_file, instructions, options), daemon=True)
        thread.start()

    def run_processing(self, path: Path, instructions: str, options: ProcessOptions) -> None:
        try:
            result = process_file(path, instructions, options)
        except Exception as exc:
            self.root.after(0, self.show_error, str(exc))
            return
        self.root.after(0, self.show_success, result)

    def set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.process_button.configure(state=state)
        self.adjust_button.configure(state=state)

    def show_error(self, message: str) -> None:
        self.set_busy(False)
        self.pending_instructions = ""
        self.status_var.set("Could not process the document.")
        messagebox.showerror(APP_TITLE, message)

    def show_success(self, result: ProcessResult) -> None:
        self.set_busy(False)
        self.last_output_dir = result.output_path.parent
        self.current_instructions = self.pending_instructions
        self.pending_instructions = ""
        self.adjust_button.grid()
        self.open_folder_button.configure(state="normal")
        warning_text = f" Warnings: {len(result.warnings)}." if result.warnings else ""
        self.status_var.set(f"Done. Updated {result.price_count} price(s). Created: {result.output_path}.{warning_text}")
        message = (
            f"Updated {result.price_count} price(s).\n\n"
            f"Created:\n{result.output_path}\n\n"
            "The original file was not changed. Please review the output before sending or billing."
        )
        if result.warnings:
            message += "\n\nWarnings:\n" + "\n".join(f"- {warning}" for warning in result.warnings)
        messagebox.showinfo(APP_TITLE, message)

    def open_output_folder(self) -> None:
        if self.last_output_dir is None:
            return
        try:
            os.startfile(self.last_output_dir)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Could not open the output folder:\n{exc}")

    def run(self) -> None:
        self.root.mainloop()
