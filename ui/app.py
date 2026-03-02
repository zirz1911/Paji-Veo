import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
import tkinter as tk
import customtkinter as ctk

from api.client import VeoClient, VeoTask
from api.uploader import upload_to_catbox
from utils.config import Config
from ui.settings_dialog import SettingsDialog
from ui.task_form import AddTaskDialog


STATUS_ICONS = {
    "pending": "⏱",
    "uploading": "⬆",
    "generating": "⏳",
    "waiting": "🕐",
    "polling": "🔍",
    "downloading": "⬇",
    "error": "❌",
}


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = Config.load()
        self._tasks: list[VeoTask] = []
        self._ui_queue: queue.Queue = queue.Queue()
        self._executor: ThreadPoolExecutor | None = None
        self._running = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Paji-Veo")
        self.geometry("820x640")
        self.minsize(700, 500)

        self._build()
        self._poll_ui_queue()

    # ─── Build UI ──────────────────────────────────────────────────────────

    def _build(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(header, text="🎬 Paji-Veo", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="⚙ Settings", width=100, command=self._open_settings).pack(side="right")

        # Output folder row
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(folder_frame, text="Output Folder:").pack(side="left")
        self._folder_var = tk.StringVar(value=self.config.output_folder)
        ctk.CTkEntry(folder_frame, textvariable=self._folder_var, width=400).pack(side="left", padx=8)
        ctk.CTkButton(folder_frame, text="Browse", width=70, command=self._browse_folder).pack(side="left")

        # Action row
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(action_frame, text="+ Add Task", width=110, command=self._add_task).pack(side="left", padx=(0, 8))
        self._gen_btn = ctk.CTkButton(action_frame, text="▶ Generate All (0)", width=160,
                                       fg_color="#1a7a3e", hover_color="#145f30",
                                       command=self._generate_all)
        self._gen_btn.pack(side="left")

        # Task table
        table_label = ctk.CTkLabel(self, text="Task Queue", font=ctk.CTkFont(size=13, weight="bold"))
        table_label.pack(anchor="w", padx=16, pady=(8, 2))

        self._table_frame = ctk.CTkScrollableFrame(self, height=200)
        self._table_frame.pack(fill="x", padx=16, pady=(0, 4))
        self._build_table_header()

        self._rows: list[dict] = []  # {task, widgets...}

        ctk.CTkButton(self, text="🗑 Delete Selected", width=140, fg_color="gray40",
                      command=self._delete_selected).pack(anchor="w", padx=16, pady=(0, 8))

        # Log
        log_label = ctk.CTkLabel(self, text="Activity Log", font=ctk.CTkFont(size=13, weight="bold"))
        log_label.pack(anchor="w", padx=16)
        self._log_box = ctk.CTkTextbox(self, height=160, state="disabled")
        self._log_box.pack(fill="both", expand=True, padx=16, pady=(2, 12))

    def _build_table_header(self):
        cols = ["#", "Name", "Prompt", "Mode", "Status", "Sel"]
        widths = [30, 100, 260, 80, 140, 30]
        for col, (c, w) in enumerate(zip(cols, widths)):
            lbl = ctk.CTkLabel(self._table_frame, text=c, width=w,
                                font=ctk.CTkFont(weight="bold"), anchor="w")
            lbl.grid(row=0, column=col, padx=4, pady=2, sticky="w")

    def _add_task_row(self, task: VeoTask, index: int):
        row = index + 1  # header is row 0
        sel_var = tk.BooleanVar(value=False)
        widgets = {
            "task": task,
            "sel_var": sel_var,
            "num": ctk.CTkLabel(self._table_frame, text=str(index + 1), width=30, anchor="w"),
            "name": ctk.CTkLabel(self._table_frame, text=(task.video_name or "(auto)")[:12], width=100, anchor="w"),
            "prompt": ctk.CTkLabel(self._table_frame, text=task.prompt[:35], width=260, anchor="w"),
            "mode": ctk.CTkLabel(self._table_frame, text=task.generation_type.split("_")[0][:8], width=80, anchor="w"),
            "status": ctk.CTkLabel(self._table_frame, text="⏱ pending", width=140, anchor="w"),
            "sel": ctk.CTkCheckBox(self._table_frame, text="", variable=sel_var, width=30),
        }
        for col, key in enumerate(["num", "name", "prompt", "mode", "status", "sel"]):
            widgets[key].grid(row=row, column=col, padx=4, pady=2, sticky="w")
        self._rows.append(widgets)

    def _refresh_table(self):
        for row in self._rows:
            for key in ["num", "name", "prompt", "mode", "status", "sel"]:
                row[key].grid_forget()
        self._rows.clear()
        for i, task in enumerate(self._tasks):
            self._add_task_row(task, i)

    # ─── Actions ───────────────────────────────────────────────────────────

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self._folder_var.set(folder)
            self.config.output_folder = folder

    def _open_settings(self):
        dlg = SettingsDialog(self, self.config)
        self.wait_window(dlg)
        if dlg.result:
            self.config = dlg.result

    def _add_task(self):
        dlg = AddTaskDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._tasks.append(dlg.result)
            self._add_task_row(dlg.result, len(self._tasks) - 1)
            self._update_gen_btn()
            self._log(f"Task added: {dlg.result.video_name or '(auto)'} — {dlg.result.prompt[:40]}")

    def _delete_selected(self):
        keep = []
        for row in self._rows:
            if not row["sel_var"].get():
                keep.append(row["task"])
        removed = len(self._tasks) - len(keep)
        self._tasks = keep
        self._refresh_table()
        self._update_gen_btn()
        if removed:
            self._log(f"Deleted {removed} task(s)")

    def _update_gen_btn(self):
        self._gen_btn.configure(text=f"▶ Generate All ({len(self._tasks)})")

    def _generate_all(self):
        if self._running:
            self._log("Already running — wait for current batch to finish")
            return
        if not self.config.api_key:
            self._log("ERROR: No API key — open Settings and add your KIE.AI key")
            return
        pending = [t for t in self._tasks if t.status in ("pending", "error")]
        if not pending:
            self._log("No pending tasks to run")
            return

        self._running = True
        self._gen_btn.configure(text="⏹ Running...", fg_color="gray40")
        output_folder = self._folder_var.get()

        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent)
        for task in pending:
            self._executor.submit(self._run_task_thread, task, output_folder)

        threading.Thread(target=self._wait_executor, daemon=True).start()

    def _wait_executor(self):
        if self._executor:
            self._executor.shutdown(wait=True)
        self._ui_queue.put(("batch_done", None, None))

    def _run_task_thread(self, task: VeoTask, output_folder: str):
        client = VeoClient(self.config.api_key)
        label = task.video_name or task.uid

        def on_status(s: str):
            task.status = s
            self._ui_queue.put(("status", task.uid, s))
            self._log_from_thread(f"Task [{label}]: {s}")

        try:
            # Upload local image if needed
            if task.local_image_path:
                on_status("uploading")
                task.image_url = upload_to_catbox(task.local_image_path)

            dest = client.run_task(
                task,
                output_folder=output_folder,
                wait_minutes=self.config.wait_minutes,
                poll_interval=self.config.poll_interval,
                on_status=on_status,
            )
            on_status(f"done:{dest.name}")
        except Exception as e:
            task.status = "error"
            self._ui_queue.put(("status", task.uid, "error"))
            self._log_from_thread(f"Task [{label}] ERROR: {e}")

    def _log_from_thread(self, msg: str):
        self._ui_queue.put(("log", None, msg))

    # ─── UI Queue (main thread) ─────────────────────────────────────────────

    def _poll_ui_queue(self):
        try:
            while True:
                event, uid, data = self._ui_queue.get_nowait()
                if event == "status":
                    self._update_row_status(uid, data)
                elif event == "log":
                    self._log(data)
                elif event == "batch_done":
                    self._running = False
                    self._gen_btn.configure(
                        text=f"▶ Generate All ({len(self._tasks)})",
                        fg_color="#1a7a3e",
                        hover_color="#145f30",
                    )
                    self._log("Batch complete.")
        except queue.Empty:
            pass
        self.after(100, self._poll_ui_queue)

    def _update_row_status(self, uid: str, status: str):
        for row in self._rows:
            if row["task"].uid == uid:
                icon = STATUS_ICONS.get(status.split(":")[0], "")
                display = status.replace("done:", "✅ ").replace("error", "❌ error")
                if icon and not display.startswith("✅") and not display.startswith("❌"):
                    display = f"{icon} {display}"
                row["status"].configure(text=display[:22])
                break

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"[{ts}] {msg}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")
