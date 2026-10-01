"""UNC Path Converter: translate mapped-drive / network-mount paths to UNC paths.

Run with no arguments for the desktop app, or pass paths to convert on the command line:
    python uncpath.py "Z:\\Projects\\plan.docx"
"""

import sys

import converter as conv

__version__ = "1.0.0"


def current_mappings() -> tuple[dict[str, str], dict[str, str]]:
    """Return (combined, manual). Manual entries override detected ones."""
    manual = conv.load_manual()
    return {**conv.detect_mappings(), **manual}, manual


def cli(paths: list[str]) -> int:
    mappings, _ = current_mappings()
    failed = 0
    for p in paths:
        try:
            print(conv.to_unc(p, mappings))
        except ValueError as e:
            print(f"{p}: {e}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


def gui() -> None:
    import tkinter as tk
    from tkinter import ttk

    class MappingDialog(tk.Toplevel):
        def __init__(self, parent, on_save):
            super().__init__(parent)
            self.title("Add mapping")
            self.transient(parent)
            self.resizable(False, False)
            self.on_save = on_save
            f = ttk.Frame(self, padding=12)
            f.pack(fill="both", expand=True)
            self.local = tk.StringVar()
            self.unc = tk.StringVar()
            ttk.Label(f, text="Drive letter or mount path:").grid(row=0, column=0, sticky="w")
            first = ttk.Entry(f, textvariable=self.local, width=34)
            first.grid(row=1, column=0, sticky="ew", pady=(0, 8))
            ttk.Label(f, text="Network path (e.g. \\\\server\\share):").grid(row=2, column=0, sticky="w")
            ttk.Entry(f, textvariable=self.unc, width=34).grid(row=3, column=0, sticky="ew")
            self.error = ttk.Label(f, foreground="#b00020", wraplength=280)
            self.error.grid(row=4, column=0, sticky="w", pady=(6, 0))
            btns = ttk.Frame(f)
            btns.grid(row=5, column=0, sticky="e", pady=(8, 0))
            ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")
            ttk.Button(btns, text="Save", command=self.save).pack(side="right", padx=(0, 6))
            self.bind("<Return>", lambda _e: self.save())
            self.bind("<Escape>", lambda _e: self.destroy())
            first.focus_set()
            self.grab_set()

        def save(self):
            try:
                local = conv.normalize_local(self.local.get())
                unc = conv.normalize_unc(self.unc.get())
            except ValueError as e:
                self.error.configure(text=str(e))
                return
            self.on_save(local, unc)
            self.destroy()

    class App(ttk.Frame):
        def __init__(self, root):
            super().__init__(root, padding=16)
            self.root = root
            self.grid(sticky="nsew")
            root.columnconfigure(0, weight=1)
            root.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.rowconfigure(1, weight=1)
            self.rowconfigure(4, weight=1)
            self.results: list[str] = []

            ttk.Label(self, text="Paths to convert (one per line):").grid(row=0, column=0, sticky="w")
            self.input = tk.Text(self, height=5, wrap="none", undo=True, font=("Courier", 11))
            self.input.grid(row=1, column=0, sticky="nsew", pady=(4, 8))
            self.input.bind("<KeyRelease>", lambda _e: self.convert())
            self.input.bind("<<Paste>>", lambda _e: self.root.after(1, self.convert))

            bar = ttk.Frame(self)
            bar.grid(row=2, column=0, sticky="ew")
            ttk.Label(bar, text="Output format:").pack(side="left")
            self.fmt = tk.StringVar(value=next(iter(conv.FORMATS)))
            combo = ttk.Combobox(bar, textvariable=self.fmt, values=list(conv.FORMATS),
                                 state="readonly", width=24)
            combo.pack(side="left", padx=8)
            combo.bind("<<ComboboxSelected>>", lambda _e: self.convert())
            ttk.Button(bar, text="Copy result", command=self.copy).pack(side="right")
            ttk.Button(bar, text="Paste", command=self.paste).pack(side="right", padx=(0, 6))
            ttk.Button(bar, text="Clear", command=self.clear).pack(side="right", padx=(0, 6))

            ttk.Label(self, text="UNC paths:").grid(row=3, column=0, sticky="w", pady=(10, 0))
            self.output = tk.Text(self, height=5, wrap="none", font=("Courier", 11),
                                  state="disabled", background="#f4f4f4")
            self.output.tag_configure("error", foreground="#b00020")
            self.output.grid(row=4, column=0, sticky="nsew", pady=(4, 4))

            self.status = tk.StringVar()
            ttk.Label(self, textvariable=self.status).grid(row=5, column=0, sticky="w")

            mf = ttk.LabelFrame(self, text="Drive mappings", padding=8)
            mf.grid(row=6, column=0, sticky="ew", pady=(10, 0))
            mf.columnconfigure(0, weight=1)
            self.tree = ttk.Treeview(mf, columns=("local", "unc", "source"), show="headings", height=5)
            for col, label, width in (("local", "Drive / mount", 140), ("unc", "Network path", 300),
                                      ("source", "Source", 80)):
                self.tree.heading(col, text=label)
                self.tree.column(col, width=width, stretch=col == "unc")
            self.tree.grid(row=0, column=0, sticky="ew")
            mbtns = ttk.Frame(mf)
            mbtns.grid(row=1, column=0, sticky="e", pady=(6, 0))
            ttk.Button(mbtns, text="Refresh", command=self.refresh).pack(side="right")
            ttk.Button(mbtns, text="Remove", command=self.remove).pack(side="right", padx=(0, 6))
            ttk.Button(mbtns, text="Add…", command=lambda: MappingDialog(root, self.add)
                       ).pack(side="right", padx=(0, 6))

            root.bind("<Control-Return>", lambda _e: (self.convert(), "break")[1])
            self.refresh()
            self.input.focus_set()

        # ----- mappings -----
        def refresh(self):
            self.mappings, self.manual = current_mappings()
            self.tree.delete(*self.tree.get_children())
            for local in sorted(self.mappings):
                source = "Manual" if local in self.manual else "Detected"
                self.tree.insert("", "end", iid=local, values=(local, self.mappings[local], source))
            self.convert()

        def add(self, local, unc):
            self.manual[local] = unc
            conv.save_manual(self.manual)
            self.refresh()

        def remove(self):
            sel = [i for i in self.tree.selection() if i in self.manual]
            if not sel:
                self.status.set("Select a Manual mapping to remove (detected ones come from the system).")
                return
            for local in sel:
                del self.manual[local]
            conv.save_manual(self.manual)
            self.refresh()

        # ----- conversion -----
        def convert(self):
            fmt = conv.FORMATS[self.fmt.get()]
            lines = self.input.get("1.0", "end-1c").splitlines()
            self.results = []
            ok = bad = 0
            self.output.configure(state="normal")
            self.output.delete("1.0", "end")
            for i, line in enumerate(lines):
                nl = "\n" if i < len(lines) - 1 else ""
                if not line.strip():
                    self.output.insert("end", nl)
                    continue
                try:
                    result = conv.format_unc(conv.to_unc(line, self.mappings), fmt)
                    self.results.append(result)
                    self.output.insert("end", result + nl)
                    ok += 1
                except ValueError as e:
                    self.output.insert("end", f"✗ {e}" + nl, "error")
                    bad += 1
            self.output.configure(state="disabled")
            self.status.set("" if not (ok or bad) else
                            f"{ok} converted" + (f", {bad} could not be converted" if bad else ""))

        def paste(self):
            try:
                text = self.root.clipboard_get()
            except tk.TclError:
                return
            self.input.delete("1.0", "end")
            self.input.insert("1.0", text)
            self.convert()

        def clear(self):
            self.input.delete("1.0", "end")
            self.convert()

        def copy(self):
            if self.results:
                self.root.clipboard_clear()
                self.root.clipboard_append("\n".join(self.results))
                n = len(self.results)
                self.status.set(f"Copied {n} path{'s' if n != 1 else ''}.")

    root = tk.Tk(className="UNCPathConverter")
    root.title(conv.APP_NAME)
    root.minsize(560, 560)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(cli(sys.argv[1:]))
    gui()
