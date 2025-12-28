#!/usr/bin/env python
# docgen frontend

import sys

import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

from docgen import DocGen


class CaptureOutput:
    def __init__(self, widget) -> None:
        self.widget = widget

    def write(self, text) -> None:
        self.widget.configure(state="normal")
        self.widget.insert("end", text)
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self) -> None:
        pass


class App(tk.Frame):
    def __init__(self, master) -> None:
        super().__init__(master)
        self.pack()

        self.infile: str = ""
        self.outfile: str = ""

        self.create_open_infile_widget()
        self.create_open_outfile_widget()
        self.create_flags_fieldset()
        self.create_generate_button()
        self.create_terminal_output()

    def create_open_infile_widget(self) -> None:
        self.infile_frame = tk.LabelFrame(self, text="Input file")
        self.infile_frame.pack(fill="both")

        self.infile_entry = tk.Entry(self.infile_frame, width=50)
        self.infile_entry.pack(side="left")

        self.infile_button = tk.Button(
            self.infile_frame, text="Open", command=self.open_infile
        )
        self.infile_button.pack(side="right")

    def open_infile(self) -> None:
        FILE_TYPES = (("Markdown files", "*.md"), ("All files", "*.*"))
        self.infile: str = filedialog.askopenfilename(filetypes=FILE_TYPES)

        if self.infile:
            self.infile_entry.delete(0, tk.END)
            self.infile_entry.insert(0, self.infile)

    def create_open_outfile_widget(self) -> None:
        self.outfile_frame = tk.LabelFrame(self, text="Output file")
        self.outfile_frame.pack(fill="both")

        self.outfile_entry = tk.Entry(self.outfile_frame, width=50)
        self.outfile_entry.pack(side="left")

        self.outfile_button = tk.Button(
            self.outfile_frame,
            text="Open",
            command=self.open_outfile,
        )
        self.outfile_button.pack(side="right")

    def open_outfile(self) -> None:
        FILE_TYPES = (("HTML files", "*.html"), ("All files", "*.*"))
        self.outfile: str = filedialog.asksaveasfilename(filetypes=FILE_TYPES)

        if self.outfile:
            self.outfile_entry.delete(0, tk.END)
            self.outfile_entry.insert(0, self.outfile)

    def create_flags_fieldset(self) -> None:
        self.flags_fieldset = tk.LabelFrame(self, text="Flags")
        self.flags_fieldset.pack(fill="both")

        self.flags_verbose = tk.BooleanVar()
        self.flags_verbose_check = tk.Checkbutton(
            self.flags_fieldset,
            text="Verbose",
            variable=self.flags_verbose,
            onvalue=True,
            offvalue=False,
        )
        self.flags_verbose_check.pack(side="left")

    def create_generate_button(self) -> None:
        self.generate_button = tk.Button(
            self,
            text="Generate",
            command=self.generate,
        )
        self.generate_button.pack()

    def generate(self) -> None:
        self.infile = self.infile_entry.get()
        if not self.infile:
            messagebox.showwarning(
                title="Oops",
                message="No input file selected!\nPlease select an input file first before generating",
            )
            return

        self.outfile = self.outfile_entry.get()
        if not self.outfile:
            messagebox.showwarning(
                title="Oops",
                message="No output file selected!\nPlease select an output file first before generating",
            )
            return

        if self.terminal_output.compare("end-1c", "!=", "1.0"):
            self.terminal_output.configure(state="normal")
            self.terminal_output.delete("1.0", tk.END)
            self.terminal_output.configure(state="disabled")

        verbose: bool = self.flags_verbose.get()
        generator = DocGen(self.infile, self.outfile, verbose)
        generator.generate()

    def create_terminal_output(self) -> None:
        self.terminal_frame = tk.LabelFrame(self, text="Terminal Output")
        self.terminal_frame.pack(fill="both")

        self.terminal_output = tk.Text(self.terminal_frame, state="disabled")
        self.terminal_output.pack(fill="both")

        self.stdout = sys.stdout
        sys.stdout = CaptureOutput(self.terminal_output)


def main() -> None:
    root = create_root()

    app = App(root)
    app.mainloop()


def create_root() -> tk.Tk:
    root: tk.Tk = tk.Tk()
    root.title("DocGen")

    return root


if __name__ == "__main__":
    main()
