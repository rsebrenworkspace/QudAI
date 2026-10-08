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
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_control, self.tab_health, self.tab_live, self.tab_review, self.tab_items = (ttk.Frame(nb) for _ in range(5))
        for tab, name in ((self.tab_control, "Control"), (self.tab_health, "Mod health"), (self.tab_live, "Live"), (self.tab_review, "Review"), (self.tab_items, "Items")):
            nb.add(tab, text=name)
        self._build_control()
        self._build_health()
        self._build_live()
        self._build_review()
        self._build_items()

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

    def _build_live(self):
        f = self.tab_live
        paned = ttk.PanedWindow(f, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned)
        right = ttk.PanedWindow(paned, orient="vertical")
        paned.add(left, weight=3)
        paned.add(right, weight=2)
        bar = ttk.Frame(left)
        bar.pack(fill="x")
        ttk.Label(bar, text="Brain console   filter:").pack(side="left", padx=4)
        self.filter_var = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.filter_var, width=24)
        e.pack(side="left")
        e.bind("<KeyRelease>", lambda _e: self._redraw_console())
        ttk.Button(bar, text="Clear", command=self._clear_console).pack(side="left", padx=6)
        self.console = self._text(left)
        for tag, colour in (("[INVENTORY]", "#0969da"), ("[AVOID]", "#8250df"), ("[LOOT]", "#1a7f37"), ("[STAND AND FIGHT]", "#bc4c00"), ("[Loop Breaker]", "#9a6700"),
                            ("[AI ENGAGED]", "#1a7f37"), ("[AI PAUSED]", "#9a6700"), ("Traceback", "#cf222e"), ("Error", "#cf222e")):
            self.console.tag_configure(tag, foreground=colour)
        top = ttk.Frame(right)
        bot = ttk.Frame(right)
        right.add(top, weight=1)
        right.add(bot, weight=1)
        ttk.Label(top, text="Last state").pack(anchor="w", padx=4)
        self.state_text = self._text(top)
        ttk.Label(bot, text="Decision trace (latest turns)").pack(anchor="w", padx=4)
        self.trace_text = self._text(bot)

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
        try:
            self._sync_buttons()
            state_path = os.path.join(EX, "last_state.json")
            if self._changed("state", state_path):
                state = cl.read_json(state_path, {})
                self._set(self.state_text, cl.describe_state(state))
                inv = [f"{'*' if i.get('equipped') else ' '} {i.get('name')} x{i.get('count', 1)}   {i.get('weight', 0)} lb" for i in (state or {}).get("inventory") or []]
                self._set(self.inv_text, "\n".join(inv) or "No inventory in the last state.")
            if self._changed("trace", TRACE):
                self._set(self.trace_text, cl.trace_text(TRACE))
                self.trace_text.see("end")
            if self._changed("drops", DROPS):
                self._set(self.drop_text, cl.drop_log_text(DROPS))
        except Exception as e:  # a refresh must never kill the window
            self.status_var.set(f"refresh error: {e}")
        self.after(2000, self._tick)

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
        self.status_var.set(f"{'Approved' if approve else 'Rejected'} generations {changed}. The brain reads this file when it builds the next prompt.")

    # ----------------------------------------------------------------- misc
    @staticmethod
    def open_folder(path):
        try:
            os.startfile(path)
        except OSError as e:
            messagebox.showerror("QudAI", f"Cannot open {path}: {e}")


if __name__ == "__main__":
    Console().mainloop()
