import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog

from utils.config import Config


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, config: Config):
        super().__init__(parent)
        self.config = config
        self.result: Config | None = None

        self.title("Settings")
        self.geometry("420x320")
        self.resizable(False, False)
        self.grab_set()

        self._build()
        self._load()
        self.after(50, self.lift)

    def _build(self):
        pad = {"padx": 16, "pady": 6}

        ctk.CTkLabel(self, text="API Key:").grid(row=0, column=0, sticky="w", **pad)
        self._api_key_var = tk.StringVar()
        self._api_entry = ctk.CTkEntry(self, textvariable=self._api_key_var, width=220, show="*")
        self._api_entry.grid(row=0, column=1, sticky="ew", padx=(0, 4), pady=6)
        self._eye_btn = ctk.CTkButton(self, text="👁", width=36, command=self._toggle_show)
        self._eye_btn.grid(row=0, column=2, padx=(0, 16), pady=6)

        ctk.CTkLabel(self, text="Output Folder:").grid(row=1, column=0, sticky="w", **pad)
        self._folder_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self._folder_var, width=220).grid(row=1, column=1, sticky="ew", padx=(0, 4), pady=6)
        ctk.CTkButton(self, text="Browse", width=60, command=self._browse).grid(row=1, column=2, padx=(0, 16), pady=6)

        ctk.CTkLabel(self, text="Max Concurrent:").grid(row=2, column=0, sticky="w", **pad)
        self._max_var = tk.StringVar()
        ctk.CTkOptionMenu(self, variable=self._max_var, values=["1", "2", "3", "5", "10"]).grid(row=2, column=1, sticky="w", padx=(0, 4), pady=6)

        ctk.CTkLabel(self, text="1080P Wait (min):").grid(row=3, column=0, sticky="w", **pad)
        self._wait_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self._wait_var, width=80).grid(row=3, column=1, sticky="w", padx=(0, 4), pady=6)

        ctk.CTkLabel(self, text="Poll Interval (sec):").grid(row=4, column=0, sticky="w", **pad)
        self._poll_var = tk.StringVar()
        ctk.CTkEntry(self, textvariable=self._poll_var, width=80).grid(row=4, column=1, sticky="w", padx=(0, 4), pady=6)

        self.columnconfigure(1, weight=1)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, columnspan=3, pady=16)
        ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color="gray40", command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Save", width=100, command=self._save).pack(side="left", padx=8)

    def _load(self):
        self._api_key_var.set(self.config.api_key)
        self._folder_var.set(self.config.output_folder)
        self._max_var.set(str(self.config.max_concurrent))
        self._wait_var.set(str(self.config.wait_minutes))
        self._poll_var.set(str(self.config.poll_interval))

    def _toggle_show(self):
        current = self._api_entry.cget("show")
        self._api_entry.configure(show="" if current == "*" else "*")

    def _browse(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self._folder_var.set(folder)

    def _save(self):
        self.config.api_key = self._api_key_var.get().strip()
        self.config.output_folder = self._folder_var.get().strip()
        try:
            self.config.max_concurrent = int(self._max_var.get())
            self.config.wait_minutes = int(self._wait_var.get())
            self.config.poll_interval = int(self._poll_var.get())
        except ValueError:
            pass
        self.config.save()
        self.result = self.config
        self.destroy()
