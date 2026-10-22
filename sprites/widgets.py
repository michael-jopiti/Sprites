"""Reusable Tk widgets in the Swiss style: square buttons, segmented rows, rules, dialogs."""
import tkinter as tk

from .library import valid
from .theme import BG, K, SPECTRUM, W, fonts


class Btn(tk.Canvas):
    """Square button: outline when idle, filled when selected or hovered. Stretches with its container."""

    def __init__(self, parent, text, command, filled=False):
        self.text = text.upper()
        super().__init__(parent, width=fonts.small.measure(self.text) + 32, height=34, bg=BG, highlightthickness=0,
                         cursor="hand2")
        self.command, self.filled, self.hover = command, filled, False
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Configure>", lambda e: self.draw())
        self.draw()

    def _hover(self, v):
        self.hover = v
        self.draw()

    def set(self, filled):
        """Set the selected state."""
        self.filled = filled
        self.draw()

    def draw(self):
        self.delete("all")
        w = max(self.winfo_width(), int(self.cget("width")))
        dark = self.filled or self.hover
        self.create_rectangle(0, 0, w - 1, 33, fill=K if dark else BG, outline=K)
        self.create_text(w / 2, 17, text=self.text, fill=BG if dark else K, font=fonts.small)


class Seg(tk.Frame):
    """Row of buttons where exactly one is selected."""

    def __init__(self, parent, options, value, on_change):
        super().__init__(parent, bg=BG)
        self.value, self.on_change = value, on_change
        self.pills = {o: Btn(self, str(o), lambda o=o: self.set(o, True), filled=o == value) for o in options}
        for p in self.pills.values():
            p.pack(side="left", padx=(0, 4))

    def set(self, value, notify=False):
        """Select `value`; call `on_change` only when `notify` is set (i.e. on user clicks)."""
        self.value = value
        for o, p in self.pills.items():
            p.set(o == value)
        if notify:
            self.on_change(value)


def label(parent, text="", font=None, **kw):
    """Label on paper. The default small font is set in uppercase."""
    font = font or fonts.small
    return tk.Label(parent, text=text.upper() if font is fonts.small else text, font=font, bg=BG, fg=K, **kw)


def rule(parent, **kw):
    """One-pixel horizontal rule."""
    return tk.Frame(parent, bg=K, height=1, **kw)


def spectrum(parent):
    """Thin gradient strip, redrawn to the width it is given."""
    c = tk.Canvas(parent, height=6, bg=BG, highlightthickness=0)

    def draw(_=None):
        c.delete("all")
        w = max(c.winfo_width(), 1)
        for x in range(0, w, 2):
            t = x / w * (len(SPECTRUM) - 1)
            i = min(int(t), len(SPECTRUM) - 2)
            a, b = (tuple(int(SPECTRUM[j][k:k + 2], 16) for k in (1, 3, 5)) for j in (i, i + 1))
            c.create_rectangle(x, 0, x + 2, 6, outline="",
                               fill="#%02x%02x%02x" % tuple(round(p + (q - p) * (t - i)) for p, q in zip(a, b)))

    c.bind("<Configure>", draw)
    return c


def dialog(parent, title, message="", entry=True, ok="Create", cancel=True):
    """Show a modal dialog and block until it closes.

    With `entry`, returns the validated name, or None if cancelled. Without it,
    returns True on OK, or None if cancelled.
    """
    d = tk.Toplevel(parent, bg=BG)
    d.title("")
    d.transient(parent)
    d.resizable(False, False)
    label(d, "+").pack(anchor="w", padx=24, pady=(20, 0))
    tk.Label(d, text=title, font=fonts.bold, bg=BG, fg=K).pack(anchor="w", padx=24, pady=(6, 4))
    if message:
        tk.Label(d, text=message, font=fonts.body, bg=BG, fg=K, wraplength=320, justify="left").pack(anchor="w", padx=24)
    note = tk.Label(d, text="", font=fonts.body, bg=BG, fg=K)  # validation message
    ent = None
    if entry:
        ent = tk.Entry(d, font=fonts.body, bg=W, fg=K, insertbackground=K, relief="flat", width=30,
                       highlightthickness=1, highlightbackground=K, highlightcolor=K)
        ent.pack(padx=24, pady=(14, 4), ipady=6)
        ent.focus_set()
    note.pack(anchor="w", padx=24)
    result = []

    def finish(v):
        result.append(v)
        d.destroy()

    def accept(_=None):
        if not ent:
            return finish(True)
        name = ent.get().strip()
        if valid(name):
            finish(name)
        else:
            note.config(text="Use a name without / \\ : and not starting with a dot.")

    row = tk.Frame(d, bg=BG)
    row.pack(anchor="e", padx=24, pady=(12, 24))
    if cancel:
        Btn(row, "Cancel", lambda: finish(None)).pack(side="left", padx=(0, 8))
    Btn(row, ok, accept, filled=True).pack(side="left")
    d.bind("<Return>", accept)
    d.bind("<Escape>", lambda e: finish(None))
    d.update_idletasks()
    d.geometry(f"+{parent.winfo_x() + (parent.winfo_width() - d.winfo_width()) // 2}+{parent.winfo_y() + 140}")
    d.wait_visibility()
    d.grab_set()
    d.wait_window()
    return result[0] if result else None
