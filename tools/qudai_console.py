"""QudAI console: one window to run the brain, pause it, check the mod's health, watch a run, and review deaths.

    python tools/qudai_console.py        (or double-click QudAI_Console.bat in the repo root)

It only reads files, except: it starts/stops the brain process it launched itself, sends that brain a newline to pause or resume
(the brain's own Enter-to-toggle), and writes lesson approvals through chronicler (same as tools/wisdom.py).
The testable logic lives in tools/console_logic.py. [unverified in a real run: the GUI itself has only been smoke-tested]"""
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import console_logic as cl  # noqa: E402

REPO = cl.REPO
EX = cl.EXCHANGE_DIR
GAME = cl.game_dir(EX)
TRACE = os.path.join(REPO, "memory", "decision_trace.jsonl")
RUNS = os.path.join(REPO, "memory", "runs")
CHRONICLES = os.path.join(REPO, "chronicles")
DROPS = os.path.join(REPO, "memory", "item_drops.jsonl")
MAX_CONSOLE_LINES = 3000
AUTO_MODEL = "(auto: whatever LM Studio has loaded)"


class Console(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QudAI Console")
        self.geometry("1200x780")
        self.proc = None
        self.out_q = queue.Queue()
        self.ui_q = queue.Queue()      # callables posted by worker threads; Tk is only touched from the main thread
        self.console_lines = []
        self.mtimes = {}
        self._health_gen = 0
        self._build()
        self.refresh_health()
        self.after(200, self._pump)
        self.after(2000, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._close)

    # ------------------------------------------------------------------ layout
    def _build(self):
        root = ttk.PanedWindow(self, orient="vertical")
        root.pack(fill="both", expand=True)
        nb = ttk.Notebook(root)
        root.add(nb, weight=3)
        root.add(self._build_bottom(root), weight=2)
        self.tab_control, self.tab_health, self.tab_live, self.tab_review, self.tab_memory, self.tab_lab, self.tab_items, self.tab_quests, self.tab_logs = (ttk.Frame(nb) for _ in range(9))
        for tab, name in ((self.tab_control, "Control"), (self.tab_health, "Mod health"), (self.tab_live, "Live"), (self.tab_review, "Review"), (self.tab_memory, "Memory"),
                          (self.tab_lab, "Lab"), (self.tab_items, "Items"), (self.tab_quests, "Quests"), (self.tab_logs, "Logs")):
            nb.add(tab, text=name)
        self._build_control()
        self._build_health()
        self._build_live()
        self._build_review()
        self._build_memory()
        self._build_lab()
        self._build_items()
        self._build_logs()
        ttk.Label(self.tab_quests, text="Quest log (read-only, from the last state)").pack(anchor="w", padx=4)
        self.quest_text = self._text(self.tab_quests)

    def _build_control(self):
        f = self.tab_control
        top = ttk.Frame(f)
        top.pack(fill="x", padx=12, pady=12)
        ttk.Label(top, text="Model").grid(row=0, column=0, sticky="w")
        self.model_var = tk.StringVar(value=AUTO_MODEL)
        self.model_box = ttk.Combobox(top, textvariable=self.model_var, width=50, values=[AUTO_MODEL])
        self.model_box.grid(row=0, column=1, padx=6)
        ttk.Button(top, text="Refresh models", command=self.refresh_models).grid(row=0, column=2)
        ttk.Label(top, text="Applies the next time you press Start (sets QUDAI_LM_MODEL).").grid(row=1, column=1, sticky="w", padx=6)
        btns = ttk.Frame(f)
        btns.pack(fill="x", padx=12, pady=4)
        self.btn_start = ttk.Button(btns, text="Start brain", command=self.start_brain)
        self.btn_stop = ttk.Button(btns, text="Stop brain", command=self.stop_brain, state="disabled")
        self.btn_toggle = ttk.Button(btns, text="Engage AI", command=self.toggle_ai, state="disabled")
        for b in (self.btn_start, self.btn_toggle, self.btn_stop):
            b.pack(side="left", padx=4)
        cap = ttk.LabelFrame(f, text="Capture logs for Claude (one click: every log, the brain's console and the code version go into scratch/captures/latest)")
        cap.pack(fill="x", padx=12, pady=6)
        ttk.Label(cap, text="What just happened?").pack(side="left", padx=6)
        self.capture_note = tk.StringVar(value="")
        ttk.Entry(cap, textvariable=self.capture_note, width=60).pack(side="left", padx=4, pady=6)
        ttk.Button(cap, text="Capture logs", command=self.capture_clicked).pack(side="left", padx=6)
        self.capture_var = tk.StringVar(value="")
        ttk.Label(f, textvariable=self.capture_var, wraplength=1100, justify="left").pack(anchor="w", padx=16)
        snap = ttk.LabelFrame(f, text="Saved-game snapshots (save in the game first; restore needs the game closed; kept in scratch/saves)")
        snap.pack(fill="x", padx=12, pady=6)
        srow = ttk.Frame(snap)
        srow.pack(fill="x")
        ttk.Label(srow, text="Note").pack(side="left", padx=6)
        self.snapshot_note = tk.StringVar(value="")
        ttk.Entry(srow, textvariable=self.snapshot_note, width=40).pack(side="left", padx=4, pady=4)
        ttk.Button(srow, text="Save snapshot", command=self.snapshot_clicked).pack(side="left", padx=6)
        ttk.Button(srow, text="Restore selected", command=self.restore_clicked).pack(side="left", padx=6)
        self.snapshot_list = tk.Listbox(snap, height=4, exportselection=False)
        self.snapshot_list.pack(fill="x", padx=6, pady=2)
        self.snapshot_var = tk.StringVar(value="")
        ttk.Label(snap, textvariable=self.snapshot_var, wraplength=1100, justify="left").pack(anchor="w", padx=6)
        self._snapshots = []
        self.refresh_snapshots()
        game = ttk.LabelFrame(f, text="Game (Caves of Qud, through Steam)")
        game.pack(fill="x", padx=12, pady=6)
        self.btn_game_start = ttk.Button(game, text="Start game", command=self.start_game_clicked)
        self.btn_game_stop = ttk.Button(game, text="Stop game", command=self.stop_game_clicked)
        self.btn_all_start = ttk.Button(game, text="Start game + brain", command=self.start_all)
        self.btn_all_stop = ttk.Button(game, text="Stop brain + game", command=self.stop_all)
        for b in (self.btn_game_start, self.btn_game_stop, self.btn_all_start, self.btn_all_stop):
            b.pack(side="left", padx=4, pady=6)
        self.game_var = tk.StringVar(value="Game status: checking...")
        ttk.Label(game, textvariable=self.game_var).pack(side="left", padx=12)
        self.status_var = tk.StringVar(value="Brain not running.")
        ttk.Label(f, textvariable=self.status_var, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=6)
        ttk.Label(f, text="The brain starts PAUSED. 'Engage AI' lets it play; press again to pause. This is the same as pressing Enter in the brain's own window.\n"
                          "Stop only ends a brain started from this window.", wraplength=900, justify="left").pack(anchor="w", padx=16)
        folders = ttk.LabelFrame(f, text="Open folder")
        folders.pack(fill="x", padx=12, pady=16)
        for label, path in (("Exchange (state.json)", EX), ("Repo", REPO), ("Game data (logs)", GAME), ("Chronicles", CHRONICLES), ("Memory", os.path.join(REPO, "memory"))):
            ttk.Button(folders, text=label, command=lambda p=path: self.open_folder(p)).pack(side="left", padx=4, pady=6)
        self.after(300, self.refresh_models)

    def _build_health(self):
        f = self.tab_health
        bar = ttk.Frame(f)
        bar.pack(fill="x", padx=12, pady=8)
        ttk.Button(bar, text="Re-check", command=self.refresh_health).pack(side="left")
        self.health_note = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.health_note).pack(side="left", padx=12)
        self.health = ttk.Treeview(f, columns=("check", "status", "detail"), show="headings", height=14)
        for c, w in (("check", 170), ("status", 80), ("detail", 900)):
            self.health.heading(c, text=c.title())
            self.health.column(c, width=w, anchor="w")
        self.health.tag_configure("ok", foreground="#1a7f37")
        self.health.tag_configure("warn", foreground="#9a6700")
        self.health.tag_configure("bad", foreground="#cf222e")
        self.health.tag_configure("unknown", foreground="#6e7781")
        self.health.pack(fill="both", expand=True, padx=12, pady=4)
        ttk.Label(f, text="The game compiles the mod at launch. If 'Mod compile' is red, the error text is in build_log.txt; paste it to Claude.", wraplength=1000).pack(anchor="w", padx=12, pady=6)

    def _build_bottom(self, parent):
        """Always visible under every tab: what he is doing right now, who is near, and the brain's own console."""
        f = ttk.Frame(parent)
        self.threat_var = tk.StringVar(value="No state yet.")
        self.threat_label = tk.Label(f, textvariable=self.threat_var, anchor="w", justify="left", font=("Segoe UI", 10, "bold"), padx=8, pady=4)
        self.threat_label.pack(fill="x")
        self.filter_var = tk.StringVar()
        nb = ttk.Notebook(f)
        nb.pack(fill="both", expand=True)
        feed_tab, console_tab = ttk.Frame(nb), ttk.Frame(nb)
        nb.add(feed_tab, text="Live actions")
        nb.add(console_tab, text="Brain console")
        self.feed = self._text(feed_tab)
        for tag, colour in (("hp", "#cf222e"), ("loop", "#bc4c00"), ("flee", "#8250df"), ("ability", "#0969da"), ("loot", "#1a7f37")):
            self.feed.tag_configure(tag, foreground=colour)
        ttk.Label(feed_tab, text="red = lost HP   orange = loop breaker (erratic movement)   purple = fleeing   blue = ability   green = loot").pack(anchor="w", padx=6)
        bar = ttk.Frame(console_tab)
        bar.pack(fill="x")
        ttk.Label(bar, text="filter:").pack(side="left", padx=4)
        e = ttk.Entry(bar, textvariable=self.filter_var, width=24)
        e.pack(side="left")
        e.bind("<KeyRelease>", lambda _e: self._redraw_console())
        ttk.Button(bar, text="Clear", command=self._clear_console).pack(side="left", padx=6)
        self.console = self._text(console_tab)
        for tag, colour in (("[INVENTORY]", "#0969da"), ("[AVOID]", "#8250df"), ("[LOOT]", "#1a7f37"), ("[STAND AND FIGHT]", "#bc4c00"), ("[Loop Breaker]", "#9a6700"),
                            ("[AI ENGAGED]", "#1a7f37"), ("[AI PAUSED]", "#9a6700"), ("Traceback", "#cf222e"), ("Error", "#cf222e")):
            self.console.tag_configure(tag, foreground=colour)
        return f

    def _build_live(self):
        f = self.tab_live
        paned = ttk.PanedWindow(f, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left, right = ttk.Frame(paned), ttk.Frame(paned)
        paned.add(left, weight=2)
        paned.add(right, weight=3)
        ttk.Label(left, text="Last state").pack(anchor="w", padx=4)
        self.state_text = self._text(left)
        ttk.Label(right, text="Decision trace (latest turns)").pack(anchor="w", padx=4)
        self.trace_text = self._text(right)

    def _build_review(self):
        f = self.tab_review
        paned = ttk.PanedWindow(f, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=2)
        paned.add(right, weight=3)
        ttk.Label(left, text="Runs (newest first)").pack(anchor="w", padx=4)
        self.runs = ttk.Treeview(left, columns=("who", "lvl", "turns", "death"), show="headings", height=8)
        for c, w in (("who", 150), ("lvl", 40), ("turns", 60), ("death", 260)):
            self.runs.heading(c, text=c)
            self.runs.column(c, width=w, anchor="w")
        self.runs.pack(fill="x", padx=4)
        self.runs.bind("<<TreeviewSelect>>", lambda _e: self.show_run())
        ttk.Button(left, text="Reload", command=self.reload_review).pack(anchor="w", padx=4, pady=4)
        ttk.Label(left, text="Ancestral lessons (only APPROVED ones reach the model)").pack(anchor="w", padx=4)
        self.lessons = ttk.Treeview(left, columns=("gen", "status", "lesson"), show="headings", height=12, selectmode="extended")
        for c, w in (("gen", 40), ("status", 80), ("lesson", 320)):
            self.lessons.heading(c, text=c)
            self.lessons.column(c, width=w, anchor="w")
        self.lessons.tag_configure("APPROVED", foreground="#1a7f37")
        self.lessons.pack(fill="both", expand=True, padx=4)
        self.lessons.bind("<<TreeviewSelect>>", lambda _e: self.show_lesson())
        row = ttk.Frame(left)
        row.pack(fill="x", padx=4, pady=4)
        ttk.Button(row, text="Approve selected", command=lambda: self.set_approval(True)).pack(side="left")
        ttk.Button(row, text="Reject selected", command=lambda: self.set_approval(False)).pack(side="left", padx=6)
        self.lesson_detail = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.lesson_detail, wraplength=520, justify="left").pack(anchor="w", padx=4, pady=4)
        ttk.Label(right, text="Chronicle and post-mortem of the selected run").pack(anchor="w", padx=4)
        self.chron = self._text(right)
        self.reload_review()

    def _build_memory(self):
        f = self.tab_memory
        paned = ttk.PanedWindow(f, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left, right = ttk.Frame(paned), ttk.Frame(paned)
        paned.add(left, weight=2)
        paned.add(right, weight=3)
        bar = ttk.Frame(left)
        bar.pack(fill="x")
        ttk.Label(bar, text="Everything stored (click one; Ctrl or Shift for several)").pack(side="left", padx=4)
        ttk.Button(bar, text="Reload", command=self.reload_memory).pack(side="right", padx=4)
        tree_wrap = ttk.Frame(left)
        tree_wrap.pack(fill="both", expand=True)
        self.mem_tree = ttk.Treeview(tree_wrap, show="tree", selectmode="extended")
        ys = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.mem_tree.yview)
        self.mem_tree.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.mem_tree.pack(side="left", fill="both", expand=True)
        self.mem_tree.tag_configure("approved", foreground="#1a7f37")
        self.mem_tree.tag_configure("data", foreground="#6e7781")
        self.mem_tree.bind("<<TreeviewSelect>>", lambda _e: self.show_memory())
        self.mem_head = tk.StringVar(value="Select a memory on the left.")
        ttk.Label(right, textvariable=self.mem_head, font=("Segoe UI", 10, "bold"), wraplength=700, justify="left").pack(anchor="w", padx=4, pady=2)
        self.mem_text = self._text(right)
        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=6)
        self.mem_approve = ttk.Button(btns, text="Approve", command=self.memory_approve, state="disabled")
        self.mem_archive = ttk.Button(btns, text="Archive", command=self.memory_archive, state="disabled")
        self.mem_delete = ttk.Button(btns, text="Delete", command=self.memory_delete, state="disabled")
        for b in (self.mem_approve, self.mem_archive, self.mem_delete):
            b.pack(side="left", padx=4)
        self.mem_status = tk.StringVar(value="Archive keeps the memory in an archive folder; Delete removes it for good. Live data files are view-only.")
        ttk.Label(right, textvariable=self.mem_status, wraplength=700, justify="left").pack(anchor="w", padx=4)
        self._mem_items = {}
        self.reload_memory()

    def _build_lab(self):
        f = self.tab_lab
        paned = ttk.PanedWindow(f, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left, right = ttk.Frame(paned), ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=3)
        ttk.Label(left, text="Lab scenarios (wishes)").pack(anchor="w", padx=4)
        self.lab_list = tk.Listbox(left, exportselection=False, height=12)
        self.lab_list.pack(fill="both", expand=True, padx=4)
        self._lab = cl.load_wish_scenarios()
        for s in self._lab:
            self.lab_list.insert("end", s.get("title", s["id"]))
        self.lab_list.bind("<<ListboxSelect>>", lambda _e: (setattr(self, "_lab_idx", 0), self.show_lab()))
        self._lab_idx = 0
        self.lab_text = self._text(right)
        row = ttk.Frame(right)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Target level").pack(side="left", padx=4)
        self.lab_level = tk.IntVar(value=5)
        spin = ttk.Spinbox(row, from_=2, to=20, textvariable=self.lab_level, width=4, command=self.show_lab)
        spin.pack(side="left")
        spin.bind("<KeyRelease>", lambda _e: self.show_lab())
        ttk.Button(row, text="Copy next wish line", command=self.lab_copy).pack(side="left", padx=10)
        ttk.Button(row, text="I used this (log it)", command=self.lab_log).pack(side="left")
        self.lab_status = tk.StringVar(value="Pick a scenario. The wish prompt is Ctrl+W in the game; pause the AI first.")
        ttk.Label(right, textvariable=self.lab_status, wraplength=800, justify="left").pack(anchor="w", padx=4)

    def _lab_selected(self):
        sel = self.lab_list.curselection()
        return self._lab[sel[0]] if sel else None

    def _lab_xp(self):
        return (cl.read_json(os.path.join(EX, "last_state.json"), {}) or {}).get("xp", 0)

    def show_lab(self):
        s = self._lab_selected()
        if not s:
            return
        try:
            level = int(self.lab_level.get())
        except (tk.TclError, ValueError):
            level = None
        self._set(self.lab_text, cl.scenario_text(s, level, self._lab_xp()))

    def lab_copy(self):
        s = self._lab_selected()
        if not s:
            return
        try:
            level = int(self.lab_level.get())
        except (tk.TclError, ValueError):
            level = None
        lines = cl.wish_lines(s, level, self._lab_xp())
        if not lines:
            self.lab_status.set("Nothing to copy for this scenario (choose a level, or you are already there).")
            return
        i = self._lab_idx % len(lines)
        self.clipboard_clear()
        self.clipboard_append(lines[i])
        self._lab_idx = i + 1
        self.lab_status.set(f"Copied line {i + 1} of {len(lines)}: {lines[i]}    In the game: Ctrl+W, paste, Enter. Click again for the next line.")

    def lab_log(self):
        s = self._lab_selected()
        if s:
            cl.log_lab_use(s["id"])
            self.lab_status.set(f"Logged '{s['id']}' in memory/lab_runs.jsonl (so this run can be told apart from a real one).")

    def _build_items(self):
        f = self.tab_items
        paned = ttk.PanedWindow(f, orient="vertical")
        paned.pack(fill="both", expand=True)
        a = ttk.Frame(paned)
        b = ttk.Frame(paned)
        paned.add(a, weight=1)
        paned.add(b, weight=1)
        ttk.Label(a, text="Inventory (from the last state; * = equipped)").pack(anchor="w", padx=4)
        self.inv_text = self._text(a)
        ttk.Label(b, text="Dropped items (zone, cell, why): go back for them with this").pack(anchor="w", padx=4)
        self.drop_text = self._text(b)

    # ------------------------------------------------------------------ Logs tab (BACKLOG B19)
    def _build_logs(self):
        f = self.tab_logs
        row = ttk.Frame(f)
        row.pack(fill="x", padx=4, pady=2)
        ttk.Label(row, text="Source").pack(side="left")
        self.log_source = tk.StringVar(value=cl.MOD_LINES)
        ttk.Combobox(row, textvariable=self.log_source, values=cl.LOG_SOURCES, width=34, state="readonly").pack(side="left", padx=4)
        ttk.Label(row, text="Filter").pack(side="left")
        self.log_filter = tk.StringVar(value="")
        ttk.Combobox(row, textvariable=self.log_filter, values=cl.LOG_QUICK_FILTERS, width=16).pack(side="left", padx=4)
        ttk.Label(row, text="Last").pack(side="left")
        self.log_count = tk.IntVar(value=200)
        ttk.Spinbox(row, from_=10, to=2000, increment=50, textvariable=self.log_count, width=6).pack(side="left", padx=4)
        self.log_auto = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="Auto-refresh", variable=self.log_auto).pack(side="left", padx=6)
        ttk.Button(row, text="Refresh", command=self.show_logs).pack(side="left", padx=2)
        ttk.Button(row, text="Copy view", command=self.logs_copy_view).pack(side="left", padx=2)
        ttk.Button(row, text="Copy bundle for Claude", command=self.logs_copy_bundle).pack(side="left", padx=2)
        ttk.Button(row, text="Save bundle", command=self.logs_save_bundle).pack(side="left", padx=2)
        ttk.Button(row, text="Capture logs", command=self.capture_clicked).pack(side="left", padx=8)
        self.logs_status = tk.StringVar(value="Pick a source and a filter. The bundle holds mod health, the last state, the mod lines, the trace and the exit choices.")
        ttk.Label(f, textvariable=self.logs_status, wraplength=1100, justify="left").pack(anchor="w", padx=4)
        self.logs_text = self._text(f)
        self.log_source.trace_add("write", lambda *_: self.show_logs())
        self.log_filter.trace_add("write", lambda *_: self.show_logs())

    def _logs_args(self):
        try:
            n = int(self.log_count.get())
        except (tk.TclError, ValueError):
            n = 200
        return self.log_source.get(), self.log_filter.get(), n

    def show_logs(self):
        source, needle, n = self._logs_args()
        lines = cl.log_lines(source, needle, n, EX)
        self._set(self.logs_text, "\n".join(lines))
        self.logs_text.see("end")
        self.logs_status.set(f"{len(lines)} line(s) from {source}" + (f", filter '{needle}'" if needle else "") + f", {time.strftime('%H:%M:%S')}")

    def logs_copy_view(self):
        self.clipboard_clear()
        self.clipboard_append(self.logs_text.get("1.0", "end").rstrip())
        self.logs_status.set("Copied what is shown. Paste it into the chat.")

    def logs_copy_bundle(self):
        text = cl.log_bundle(EX)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.logs_status.set(f"Copied the bundle ({len(text):,} characters). Paste it into the chat.")

    def refresh_snapshots(self):
        self._snapshots = cl.list_snapshots()
        self.snapshot_list.delete(0, "end")
        for s in self._snapshots:
            self.snapshot_list.insert("end", f"{s['stamp']}   {s['note'] or '(no note)'}   |   {s['summary']}")

    def snapshot_clicked(self):
        try:
            folder, text = cl.snapshot_save(self.snapshot_note.get().strip())
        except Exception as e:                      # noqa: BLE001  a snapshot must never kill the window
            self.snapshot_var.set(f"Snapshot failed: {e}")
            return
        self.snapshot_var.set(text)
        self.refresh_snapshots()

    def restore_clicked(self):
        sel = self.snapshot_list.curselection()
        if not sel:
            self.snapshot_var.set("Pick a snapshot in the list first.")
            return
        snap = self._snapshots[sel[0]]
        if cl.game_running():
            self.snapshot_var.set("Close the game first (Stop game): it would write over the restored files.")
            return
        if not messagebox.askyesno("Restore snapshot", f"Replace the current save with this snapshot?\n\n{snap['summary']}\n\nWhat it replaces is copied to scratch/saves/_replaced first."):
            return
        ok, text = cl.restore_snapshot(snap["folder"])
        self.snapshot_var.set(text)

    def capture_clicked(self):
        try:
            folder, text, copied = cl.capture_logs(self.capture_note.get().strip(), list(self.console_lines), EX)
        except Exception as e:                      # noqa: BLE001  a capture must never kill the window
            self.capture_var.set(f"Capture failed: {e}")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        msg = f"Captured {len(copied)} file(s) to {folder} (also scratch/captures/latest). The bundle is on the clipboard; tell Claude 'captured'."
        self.capture_var.set(msg)
        self.logs_status.set(msg)

    def logs_save_bundle(self):
        ok, where = cl.save_bundle(cl.log_bundle(EX))
        self.logs_status.set(f"Saved the bundle to {where}" if ok else f"Could not save the bundle: {where}")

    @staticmethod
    def _text(parent):
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True)
        t = tk.Text(wrap, wrap="none", font=("Consolas", 9), undo=False)
        ys = ttk.Scrollbar(wrap, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        return t

    # ----------------------------------------------------------------- brain process
    def start_brain(self):
        if self.proc and self.proc.poll() is None:
            return
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        model = self.model_var.get().strip()
        if model and model != AUTO_MODEL:
            env["QUDAI_LM_MODEL"] = model
        else:
            env.pop("QUDAI_LM_MODEL", None)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.proc = subprocess.Popen([sys.executable, "-u", "brain.py"], cwd=REPO, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, creationflags=flags)
        except OSError as e:
            messagebox.showerror("QudAI", f"Could not start the brain: {e}")
            return
        threading.Thread(target=self._reader, args=(self.proc,), daemon=True).start()
        self._log(f"--- brain started (model: {model if model != AUTO_MODEL else 'auto'}) ---")
        self._sync_buttons()

    def _reader(self, proc):
        for raw in iter(proc.stdout.readline, b""):
            self.out_q.put(raw.decode("utf-8", errors="replace").rstrip("\r\n"))
        self.out_q.put(f"--- brain exited (code {proc.poll()}) ---")

    def stop_brain(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self._log("--- stop requested ---")
        self._sync_buttons()

    def toggle_ai(self):
        if not (self.proc and self.proc.poll() is None):
            return
        try:
            self.proc.stdin.write(cl.pause_resume_bytes())
            self.proc.stdin.flush()
        except OSError as e:
            messagebox.showerror("QudAI", f"Could not reach the brain: {e}")

    def _running(self):
        return bool(self.proc and self.proc.poll() is None)

    # ----------------------------------------------------------------- game control (HANDOFF issue 100)
    def _game_poll(self):
        """Refreshes the game status text off the UI thread (tasklist takes a moment)."""
        def work():
            up = cl.game_running()
            self.after(0, lambda: self._game_status(up))
        threading.Thread(target=work, daemon=True).start()

    def _game_status(self, up):
        self._game_up = up
        self.game_var.set("Game status: RUNNING" if up else "Game status: not running")
        self.btn_game_start.configure(state="disabled" if up else "normal")
        self.btn_game_stop.configure(state="normal" if up else "disabled")

    def start_game_clicked(self):
        ok, text = cl.start_game()
        self._log(f"--- {text} ---")
        if not ok:
            messagebox.showerror("QudAI", text)
        self.after(4000, self._game_poll)

    def stop_game_clicked(self):
        ok, text = cl.stop_game(force=False)
        self._log(f"--- game close requested: {text} ---")
        self.after(6000, self._offer_force_close)

    def _offer_force_close(self):
        """A polite close can leave the game up (for example behind a confirmation). Offer the hard stop only if it is still running."""
        if cl.game_running() and messagebox.askyesno("QudAI", "The game is still running. Force it to close now? (Anything since the last save is lost.)"):
            ok, text = cl.stop_game(force=True)
            self._log(f"--- game force-closed: {text} ---")
        self._game_poll()

    def start_all(self):
        if not cl.game_running():
            self.start_game_clicked()
        self.start_brain()

    def stop_all(self):
        self.stop_brain()
        if cl.game_running():
            self.stop_game_clicked()

    def _sync_buttons(self):
        running = self._running()
        self.btn_start.configure(state="disabled" if running else "normal")
        self.btn_stop.configure(state="normal" if running else "disabled")
        self.btn_toggle.configure(state="normal" if running else "disabled", text="Pause AI" if cl.flag_on(EX) else "Engage AI")
        if not running:
            self.status_var.set("Brain not running.")
        else:
            self.status_var.set("Brain running: AI ENGAGED (playing)." if cl.flag_on(EX) else "Brain running: AI PAUSED (you have manual control).")

    def _close(self):
        if self._running() and not messagebox.askyesno("QudAI", "The brain is still running. Stop it and close?"):
            return
        self.stop_brain()
        self.destroy()

    # ----------------------------------------------------------------- console text
    def _log(self, line):
        self.console_lines.append(line)
        if len(self.console_lines) > MAX_CONSOLE_LINES:
            del self.console_lines[: len(self.console_lines) - MAX_CONSOLE_LINES]
        needle = self.filter_var.get().strip().lower()
        if needle and needle not in line.lower():
            return
        self._append(line)

    def _append(self, line):
        at_end = self.console.yview()[1] >= 0.99
        self.console.insert("end", line + "\n", cl.colour_tag(line))
        if at_end:
            self.console.see("end")

    def _redraw_console(self):
        self.console.delete("1.0", "end")
        for line in cl.filter_lines(self.console_lines, self.filter_var.get()):
            self.console.insert("end", line + "\n", cl.colour_tag(line))
        self.console.see("end")

    def _clear_console(self):
        self.console_lines.clear()
        self.console.delete("1.0", "end")

    def _pump(self):
        for _ in range(400):
            try:
                self._log(self.out_q.get_nowait())
            except queue.Empty:
                break
        while True:
            try:
                self.ui_q.get_nowait()()
            except queue.Empty:
                break
            except Exception:
                pass
        self.after(200, self._pump)

    # ----------------------------------------------------------------- periodic refresh
    def _changed(self, key, path):
        try:
            m = os.path.getmtime(path)
        except OSError:
            m = None
        if self.mtimes.get(key) == m:
            return False
        self.mtimes[key] = m
        return True

    @staticmethod
    def _set(widget, text):
        top = widget.yview()[0]
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.yview_moveto(top)

    def _tick(self):
        self._game_ticks = getattr(self, "_game_ticks", 0) + 1
        if self._game_ticks % 2 == 1:
            self._game_poll()
        try:
            self._sync_buttons()
            state_path = os.path.join(EX, "last_state.json")
            if self._changed("state", state_path):
                state = cl.read_json(state_path, {})
                self._draw_threats(state)
                self._set(self.state_text, cl.describe_state(state))
                inv = [f"{'*' if i.get('equipped') else ' '} {i.get('name')} x{i.get('count', 1)}   {i.get('weight', 0)} lb" for i in (state or {}).get("inventory") or []]
                self._set(self.inv_text, "\n".join(inv) or "No inventory in the last state.")
                self._set(self.quest_text, cl.describe_quests(state))
            if self._changed("trace", TRACE):
                self._set(self.trace_text, cl.trace_text(TRACE))
                self.trace_text.see("end")
                self._draw_feed()
            if self.log_auto.get():
                self.show_logs()
            if self._changed("drops", DROPS):
                self._set(self.drop_text, cl.drop_log_text(DROPS))
        except Exception as e:  # a refresh must never kill the window
            self.status_var.set(f"refresh error: {e}")
        self.after(2000, self._tick)

    def _draw_feed(self):
        at_end = self.feed.yview()[1] >= 0.98
        self.feed.delete("1.0", "end")
        for text, tag in cl.feed_rows(TRACE, 60):
            self.feed.insert("end", text + "\n", tag)
        if at_end:
            self.feed.see("end")

    def _draw_threats(self, state):
        text, worst = cl.threat_summary(state)
        hp = f"HP {state.get('hp', '?')}/{state.get('max_hp', '?')}   " if state else ""
        self.threat_var.set(hp + text)
        bg, fg = {"danger": ("#ffebe9", "#82071e"), "watch": ("#fff8c5", "#4d2d00"), "calm": ("#dafbe1", "#116329")}[worst]
        self.threat_label.configure(bg=bg, fg=fg)

    # ----------------------------------------------------------------- health
    def refresh_health(self):
        self.health.delete(*self.health.get_children())
        for name, status, detail in cl.mod_health(EX):
            self.health.insert("", "end", values=(name, status.upper(), detail), tags=(status,))
        self.health_note.set("checking LM Studio...")
        self._health_gen += 1
        threading.Thread(target=self._lm_check, args=(self._health_gen,), daemon=True).start()

    def _lm_check(self, gen):
        models, err = self._fetch_models()
        self.ui_q.put(lambda: self._lm_done(gen, models, err))

    def _lm_done(self, gen, models, err):
        if gen != self._health_gen:
            return                      # a newer re-check replaced this one
        status, detail = ("ok", f"reachable, {len(models)} model(s) listed") if models else ("bad", f"not reachable or no models: {err}")
        self.health.insert("", "end", values=("LM Studio", status.upper(), detail), tags=(status,))
        self.health_note.set("")

    @staticmethod
    def _fetch_models():
        try:
            import requests
            r = requests.get("http://localhost:1234/v1/models", timeout=2)
            return sorted(m.get("id") for m in r.json().get("data", []) if m.get("id")), ""
        except Exception as e:
            return [], str(e)[:120]

    def refresh_models(self):
        def work():
            models, _ = self._fetch_models()
            self.ui_q.put(lambda: self.model_box.configure(values=[AUTO_MODEL] + models))
        threading.Thread(target=work, daemon=True).start()

    # ----------------------------------------------------------------- review
    def reload_review(self):
        self.runs.delete(*self.runs.get_children())
        self._run_rows = cl.list_runs(RUNS)
        for i, r in enumerate(self._run_rows):
            self.runs.insert("", "end", iid=str(i), values=(r["name"], r["level"], r["turns"], str(r["death"])[:60]))
        self.lessons.delete(*self.lessons.get_children())
        for w in cl.lessons():
            status = "APPROVED" if w.get("approved") is True else "hidden"
            self.lessons.insert("", "end", iid=str(w.get("generation")), values=(w.get("generation"), status, str(w.get("lesson"))[:160]), tags=(status,))

    def show_run(self):
        sel = self.runs.selection()
        if not sel:
            return
        r = self._run_rows[int(sel[0])]
        files = cl.find_chronicle_files(CHRONICLES, r["name"])
        text = "\n\n".join(f"===== {os.path.basename(p)} =====\n{cl.read_text(p)}" for p in files) or f"No chronicle file found for '{r['name']}'."
        self._set(self.chron, text)

    def show_lesson(self):
        sel = self.lessons.selection()
        if not sel:
            return
        gen = int(sel[-1])
        for w in cl.lessons():
            if w.get("generation") == gen:
                self.lesson_detail.set(f"Gen {gen}: {w.get('lesson')}\nDied to: {w.get('death_reason')}")

    def set_approval(self, approve):
        gens = [int(i) for i in self.lessons.selection()]
        if not gens:
            return
        changed = cl.set_approval(gens, approve)
        self.reload_review()
        if hasattr(self, "mem_tree"):
            self.reload_memory()
        self.status_var.set(f"{'Approved' if approve else 'Rejected'} generations {changed}. The brain reads this file when it builds the next prompt.")

    # ----------------------------------------------------------------- memory tab
    def reload_memory(self):
        self.mem_tree.delete(*self.mem_tree.get_children())
        self._mem_items = {}
        items = cl.list_memory_items()
        for kind in cl.MEMORY_KINDS:
            group = [it for it in items if it["kind"] == kind]
            gid = f"group:{kind}"
            self.mem_tree.insert("", "end", iid=gid, text=f"{cl.MEMORY_KIND_NAMES[kind]} ({len(group)})", open=(kind == "lesson"))
            for it in group:
                self._mem_items[it["key"]] = it
                tags = ("approved",) if it.get("approved") else (("data",) if kind == "data" else ())
                self.mem_tree.insert(gid, "end", iid=it["key"], text=it["title"], tags=tags)
        self.show_memory()

    def _selected_memory(self):
        return [self._mem_items[i] for i in self.mem_tree.selection() if i in self._mem_items]

    def show_memory(self):
        sel = self._selected_memory()
        for b in (self.mem_approve, self.mem_archive, self.mem_delete):
            b.configure(state="disabled")
        if not sel:
            self.mem_head.set("Select a memory on the left.")
            self._set(self.mem_text, "")
            return
        first = sel[0]
        self.mem_head.set(f"{len(sel)} selected: {', '.join(i['title'][:40] for i in sel[:3])}{' ...' if len(sel) > 3 else ''}" if len(sel) > 1 else first["title"])
        self._set(self.mem_text, cl.memory_item_text(first))
        safe = all(i.get("safe", True) for i in sel)
        if safe:
            self.mem_archive.configure(state="normal")
            self.mem_delete.configure(state="normal")
        if all(i["kind"] == "lesson" for i in sel):
            self.mem_approve.configure(state="normal", text="Withdraw approval" if all(i.get("approved") for i in sel) else "Approve")
        else:
            self.mem_approve.configure(text="Approve")

    def memory_approve(self):
        sel = [i for i in self._selected_memory() if i["kind"] == "lesson"]
        if not sel:
            return
        approve = not all(i.get("approved") for i in sel)
        changed = cl.set_approval([i["gen"] for i in sel], approve)
        self.mem_status.set(f"{'Approved' if approve else 'Withdrew approval for'} generations {changed}. The brain reads this file when it builds the next prompt.")
        self.reload_memory()
        self.reload_review()

    def memory_archive(self):
        sel = self._selected_memory()
        if not sel or not messagebox.askyesno("Archive", f"Move {len(sel)} memor{'y' if len(sel) == 1 else 'ies'} to the archive folder?\nNothing is lost: they stay in an archive folder."):
            return
        done, errors = [], []
        for it in sel:
            try:
                done.append(cl.archive_memory_item(it))
            except Exception as e:
                errors.append(f"{it['title'][:40]}: {e}")
        self.mem_status.set(f"Archived {len(done)}." + (f" {len(errors)} failed: {'; '.join(errors[:2])}" if errors else ""))
        self.reload_memory()
        self.reload_review()

    def memory_delete(self):
        sel = self._selected_memory()
        if not sel:
            return
        names = "\n".join(f"  {i['title'][:70]}" for i in sel[:6]) + ("\n  ..." if len(sel) > 6 else "")
        if not messagebox.askyesno("Delete for good?", f"Permanently delete {len(sel)} memor{'y' if len(sel) == 1 else 'ies'}?\n\n{names}\n\nThis cannot be undone: git cannot bring back files it never tracked (chronicles, runs).\nChoose Archive if you are not sure.", default="no", icon="warning"):
            return
        done, errors = [], []
        for it in sel:
            try:
                done.append(cl.delete_memory_item(it))
            except Exception as e:
                errors.append(f"{it['title'][:40]}: {e}")
        self.mem_status.set(f"Deleted {len(done)}." + (f" {len(errors)} failed: {'; '.join(errors[:2])}" if errors else ""))
        self.reload_memory()
        self.reload_review()

    # ----------------------------------------------------------------- misc
    @staticmethod
    def open_folder(path):
        try:
            os.startfile(path)
        except OSError as e:
            messagebox.showerror("QudAI", f"Cannot open {path}: {e}")


if __name__ == "__main__":
    Console().mainloop()
