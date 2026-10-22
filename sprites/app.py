"""The editor window: library sidebar, pixel canvas and tools."""
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, ttk

from . import export, model
from .library import LIBRARY, depth
from .theme import BG, COLORS, GRID_SIZES, K, SCALES, W, fonts, load_fonts
from .widgets import Btn, Seg, dialog, label, rule, spectrum

FALLBACK_SIZE = 384  # canvas px before the window has a size; divisible by every grid size


class App:
    """Owns the Tk root, the editing state and every widget.

    Layout, left to right: the library sidebar, a one-pixel rule, then the main
    column (spectrum strip, top bar, header, canvas stage, controls).
    """

    def __init__(self, library: Path = LIBRARY):
        self.library = library
        self.root = tk.Tk()
        self.root.title("Sprites")
        self.root.configure(bg=BG)
        self.root.geometry("1120x780")
        self.root.minsize(900, 640)
        load_fonts()

        # editing state
        self.n = 16  # grid size in pixels per side
        self.size = FALLBACK_SIZE  # canvas px, recomputed from the window in render(); always a multiple of n
        self.grid = model.blank(self.n)
        self.current: Path | None = None  # the open character file
        self.color = COLORS[0]
        self.palette = list(COLORS)
        self.master = None  # grid as drawn before any resize; None once edited
        self.cells = []  # canvas item ids, cells[y][x]
        self._job = None  # pending debounced render

        self.root.report_callback_exception = self.oops
        self._build_sidebar()
        self._build_main()
        self._bind_canvas()
        self.refresh()
        self.draw_palette()
        self.render()
        self.set_header()

    def run(self):
        """Enter the Tk main loop."""
        self.root.mainloop()

    # --- layout -----------------------------------------------------------
    def _build_sidebar(self):
        """Library tree on the left, with the project/collection/character buttons at its foot."""
        self.side = tk.Frame(self.root, bg=BG, width=280)
        self.side.pack(side="left", fill="y")
        self.side.pack_propagate(False)
        tk.Frame(self.root, bg=K, width=1).pack(side="left", fill="y")  # vertical divider

        label(self.side, "Index  +").pack(anchor="w", padx=20, pady=(22, 0))
        tk.Label(self.side, text="Library", font=fonts.title, bg=BG, fg=K).pack(anchor="w", padx=20, pady=(2, 14))
        rule(self.side).pack(fill="x", padx=20)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=BG, fieldbackground=BG, foreground=K, borderwidth=0, rowheight=30,
                        font=fonts.body)
        style.map("Treeview", background=[("selected", K)], foreground=[("selected", BG)])
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.layout("Treeview.Item", [("Treeitem.padding", {"sticky": "nswe", "children": [("Treeitem.text", {"side": "left"})]})])

        btns = tk.Frame(self.side, bg=BG)  # packed before the tree so the tree takes the leftover height
        btns.pack(side="bottom", fill="x", padx=20, pady=(8, 20))
        self.tree = ttk.Treeview(self.side, show="tree", selectmode="browse")
        self.tree.tag_configure("project", font=fonts.bold)
        self.tree.pack(fill="both", expand=True, padx=12, pady=(8, 0))
        self.tree.bind("<Double-1>", self.on_open)
        for text, cmd, filled in [("New project", self.new_project, True), ("New collection", self.new_collection, False),
                                  ("New character", self.new_character, False), ("Delete", self.delete, False)]:
            Btn(btns, text, cmd, filled=filled).pack(fill="x", pady=3)

    def _build_main(self):
        """Spectrum strip, top bar, header, then controls and the canvas stage."""
        main = tk.Frame(self.root, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        spectrum(main).pack(fill="x")
        body = tk.Frame(main, bg=BG)
        body.pack(fill="both", expand=True, padx=32)

        top = tk.Frame(body, bg=BG)
        top.pack(fill="x", pady=(16, 0))
        label(top, "Sprite editor  +  Pixel grid").pack(side="left")
        Btn(top, "Full screen", self.toggle_fullscreen).pack(side="right")
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))

        # header: character name and path on the left, grid size numeral on the right
        head = tk.Frame(body, bg=BG)
        head.pack(fill="x", pady=(14, 14))
        head.columnconfigure(0, weight=1)
        self.title = tk.Label(head, font=fonts.title, bg=BG, fg=K)
        self.title.grid(row=0, column=0, sticky="w")
        self.sub = label(head)
        self.sub.grid(row=1, column=0, sticky="w")
        self.dims = tk.Label(head, font=fonts.num, bg=BG, fg=K)
        self.dims.grid(row=0, column=1, rowspan=2, sticky="e")
        rule(body).pack(fill="x")

        self._build_controls(body)

        # stage: the canvas is centered in the leftover space and kept square
        self.stage = tk.Frame(body, bg=BG)
        self.stage.pack(fill="both", expand=True, pady=14)
        self.stage.bind("<Configure>", self.on_stage)
        card = tk.Frame(self.stage, bg=K)  # one-pixel black frame around the canvas
        card.place(relx=0.5, rely=0.5, anchor="center")
        self.canvas = tk.Canvas(card, width=self.size, height=self.size, bg=W, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(padx=1, pady=1)

    def _build_controls(self, body):
        """Tools, grid sizes, palette, clear and export. Packed before the stage so the stage gets what is left."""
        ctrl = tk.Frame(body, bg=BG)
        ctrl.pack(side="bottom", fill="x")
        row1 = tk.Frame(ctrl, bg=BG)
        row1.pack(fill="x")
        row2 = tk.Frame(ctrl, bg=BG)
        row2.pack(fill="x", pady=(10, 0))
        row3 = tk.Frame(ctrl, bg=BG)
        row3.pack(fill="x", pady=(10, 20))
        rule(ctrl).pack(fill="x", pady=(0, 14))

        self.tools = Seg(row1, ["Pencil", "Eraser"], "Pencil", lambda v: None)
        self.tools.pack(side="left")
        self.sizes = Seg(row1, GRID_SIZES, self.n, self.resize)
        self.sizes.pack(side="right")

        self.pal = tk.Canvas(row2, height=40, bg=BG, highlightthickness=0)
        self.pal.pack(fill="x")

        Btn(row3, "Clear", self.clear).pack(side="left")
        Btn(row3, "Export", self.export, filled=True).pack(side="right")
        self.scales = Seg(row3, SCALES, SCALES[1], lambda v: None)
        self.scales.pack(side="right", padx=(0, 4))

    def _bind_canvas(self):
        """Mouse drawing: left button paints, any other button erases, release autosaves."""
        for seq in ("<Button-1>", "<B1-Motion>"):
            self.canvas.bind(seq, lambda e: self.paint(e, self.color if self.tools.value == "Pencil" else None))
        for seq in ("<Button-2>", "<B2-Motion>", "<Button-3>", "<B3-Motion>"):  # right click, macOS or not
            self.canvas.bind(seq, lambda e: self.paint(e, None))
        for seq in ("<ButtonRelease-1>", "<ButtonRelease-2>", "<ButtonRelease-3>"):
            self.canvas.bind(seq, lambda e: self.save_char())  # autosave after every stroke
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    # --- window -----------------------------------------------------------
    def toggle_fullscreen(self, _=None):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def quit(self):
        """Save the open character, then close."""
        self.save_char()
        self.root.destroy()

    def oops(self, _t, v, _tb):
        """Tk callback-exception hook: show the error instead of failing silently."""
        self.info("Something went wrong", str(v))

    def info(self, title, message=""):
        """Show a one-button message dialog."""
        dialog(self.root, title, message, entry=False, ok="OK", cancel=False)

    def set_header(self, note=None):
        """Show the character name and its project / collection path, or `note` in place of the path."""
        self.title.config(text=self.current.stem if self.current else "Sprites")
        path = " / ".join(self.current.parent.relative_to(self.library).parts) if self.current else "No character open"
        self.sub.config(text=(note or path).upper())

    # --- canvas -----------------------------------------------------------
    def render(self):
        """Fit the canvas to the stage and redraw the dotted grid and every cell."""
        avail = min(self.stage.winfo_width(), self.stage.winfo_height()) - 4
        self.size = avail // self.n * self.n if avail >= self.n * 4 else FALLBACK_SIZE // self.n * self.n
        self.canvas.config(width=self.size, height=self.size)
        self.dims.config(text=f"{self.n}×{self.n}")
        self.canvas.delete("all")
        cs = self.size // self.n
        for i in range(1, self.n):  # dotted grid; painted cells cover it, transparent cells show it
            self.canvas.create_line(i * cs, 0, i * cs, self.size, fill=K, dash=(1, 3))
            self.canvas.create_line(0, i * cs, self.size, i * cs, fill=K, dash=(1, 3))
        self.cells = [[self.canvas.create_rectangle(x * cs, y * cs, (x + 1) * cs, (y + 1) * cs,
                                                    fill=self.grid[y][x] or "", outline="")
                       for x in range(self.n)] for y in range(self.n)]
        if not self.current:
            self.canvas.create_rectangle(0, 0, self.size, self.size, fill=W, outline="")
            self.canvas.create_text(self.size / 2, self.size / 2 - 12, text="No character open", font=fonts.bold, fill=K)
            self.canvas.create_text(self.size / 2, self.size / 2 + 14, text="Select a collection, then New character.",
                                    font=fonts.body, fill=K)

    def on_stage(self, _):
        """Window resized or toggled full screen: refit the canvas once the drag settles."""
        if self._job:
            self.root.after_cancel(self._job)
        self._job = self.root.after(40, self.render)

    def paint(self, event, c):
        """Set the pixel under the pointer to color `c` (None erases)."""
        if not self.current:
            return
        self.master = None  # an edit makes the pre-resize copy stale
        cs = self.size // self.n
        x, y = event.x // cs, event.y // cs
        if 0 <= x < self.n and 0 <= y < self.n:
            self.grid[y][x] = c
            self.canvas.itemconfig(self.cells[y][x], fill=c or "")

    def resize(self, new):
        """Change the grid size, keeping the picture.

        Shrinking is lossy, so the picture as drawn is kept in `master` and every
        resize rebuilds from it, until the next edit.
        """
        self.master = self.master or [r[:] for r in self.grid]
        self.grid = model.resample(self.master, new)
        self.n = new
        self.render()
        self.save_char()

    def clear(self):
        self.master = None
        self.grid = model.blank(self.n)
        self.render()
        self.save_char()

    def export(self):
        """Ask for a path and write the sprite as PNG, GIF or SVG."""
        if not self.current:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", initialfile=f"{self.current.stem}.png",
            filetypes=[("PNG", "*.png"), ("GIF", "*.gif"), ("SVG (vector)", "*.svg")])
        if path:
            export.write(path, self.grid, self.n, int(self.scales.value[:-1]))

    # --- palette ----------------------------------------------------------
    def draw_palette(self):
        """Draw the swatches, the selected one outlined, plus a final + swatch for custom colors."""
        self.pal.delete("all")
        for i, c in enumerate(self.palette):
            x = 2 + i * 36
            if c == self.color:
                self.pal.create_rectangle(x, 2, x + 34, 36, outline=K, width=2)
            self.pal.create_rectangle(x + 6, 8, x + 28, 30, fill=c, outline=K, tags=f"c{i}")
            self.pal.tag_bind(f"c{i}", "<Button-1>", lambda e, c=c: self.pick(c))
        x = 2 + len(self.palette) * 36
        self.pal.create_rectangle(x + 6, 8, x + 28, 30, fill=BG, outline=K, tags="add")
        self.pal.create_text(x + 17, 19, text="+", font=fonts.body, fill=K, tags="add")
        self.pal.tag_bind("add", "<Button-1>", self.add_color)

    def pick(self, c):
        """Select color `c` and switch back to the pencil."""
        self.color = c
        self.tools.set("Pencil")
        self.draw_palette()

    def add_color(self, _):
        """Choose a custom color. Only the two newest custom colors are kept."""
        c = colorchooser.askcolor()[1]
        if c:
            if c not in self.palette:
                self.palette[10:] = (self.palette[10:] + [c])[-2:]
            self.pick(c)

    # --- library: project > collection > character ------------------------
    def refresh(self, select=None):
        """Rebuild the tree from disk, optionally selecting the item at path `select`."""
        self.tree.delete(*self.tree.get_children())
        self.library.mkdir(exist_ok=True)
        for proj in sorted(p for p in self.library.iterdir() if p.is_dir()):
            self.tree.insert("", "end", str(proj), text=proj.name, open=True, tags="project")
            for col in sorted(c for c in proj.iterdir() if c.is_dir()):
                self.tree.insert(str(proj), "end", str(col), text=col.name, open=True)
                for ch in sorted(col.glob("*.json")):
                    self.tree.insert(str(col), "end", str(ch), text=ch.stem)
        if select and self.tree.exists(str(select)):
            self.tree.selection_set(str(select))
            self.tree.see(str(select))

    def selected(self) -> Path | None:
        """Return the selected tree item as a path, or None."""
        sel = self.tree.selection()
        return Path(sel[0]) if sel else None

    def save_char(self):
        """Write the open character to disk and flash "Saved" in the header."""
        if self.current:
            model.save(self.current, self.n, self.grid)
            self.set_header("Saved")
            self.root.after(1200, self.set_header)

    def open_char(self, path):
        """Autosave the character being left, then open `path`."""
        self.save_char()
        self.n, self.grid = model.load(path)
        self.current, self.master = path, None
        self.sizes.set(self.n)
        self.render()
        self.set_header()

    def new_project(self):
        if name := dialog(self.root, "New project"):
            (self.library / name).mkdir(parents=True, exist_ok=True)
            self.refresh(self.library / name)

    def new_collection(self):
        sel = self.selected()
        if not sel:
            return self.info("Select a project first", "A collection lives inside a project.")
        proj = self.library / sel.relative_to(self.library).parts[0]
        if name := dialog(self.root, "New collection", f"Inside project “{proj.name}”."):
            (proj / name).mkdir(exist_ok=True)
            self.refresh(proj / name)

    def new_character(self):
        sel = self.selected()
        if not sel:
            return self.info("Select a collection first", "A character lives inside a collection.")
        if depth(sel, self.library) == 1:  # project picked: use its only collection, or make one when it has none
            cols = [c for c in sel.iterdir() if c.is_dir()]
            if len(cols) > 1:
                return self.info("Select a collection first", "This project has several collections.")
            col = cols[0] if cols else sel / "Characters"
            col.mkdir(exist_ok=True)
        else:
            col = sel if depth(sel, self.library) == 2 else sel.parent
        if name := dialog(self.root, "New character", f"Inside collection “{col.name}”."):
            path = col / f"{name}.json"
            if path.exists():
                return self.info("Name already used", f"“{name}” already exists in this collection.")
            self.save_char()
            model.save(path, self.n, model.blank(self.n))
            self.open_char(path)
            self.refresh(path)

    def delete(self):
        """Delete the selected project, collection or character after confirmation."""
        sel = self.selected()
        if not sel:
            return
        name = sel.stem if sel.is_file() else sel.name
        if not dialog(self.root, f"Delete “{name}”?", "This also deletes everything inside it." if sel.is_dir() else "",
                      entry=False, ok="Delete"):
            return
        if self.current and (sel == self.current or sel in self.current.parents):
            self.current = None
            self.render()
            self.set_header()
        shutil.rmtree(sel) if sel.is_dir() else sel.unlink()
        self.refresh()

    def on_open(self, _):
        """Double-click on a character opens it."""
        sel = self.selected()
        if sel and sel.suffix == ".json":
            self.open_char(sel)
