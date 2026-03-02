import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from typing import Optional

from api.client import VeoTask


GENERATION_TYPES = {
    "Image→Video (1 frame)": "FIRST_AND_LAST_FRAMES_2_VIDEO",
    "Image→Video (start only)": "IMAGE_2_VIDEO",
    "Text→Video": "TEXT_2_VIDEO",
}
MODELS = ["veo3_fast", "veo3"]
RATIOS = ["9:16", "16:9", "1:1", "4:3", "3:4"]


class AddTaskDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.result: Optional[VeoTask] = None
        self._local_image: Optional[str] = None
        self._advanced_visible = False

        self.title("Add New Task")
        self.geometry("480x560")
        self.resizable(False, False)
        self.grab_set()

        self._build()
        self.after(50, self.lift)

    def _build(self):
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=12)

        # Video Name
        ctk.CTkLabel(main, text="Video Name:").pack(anchor="w")
        self._name_var = tk.StringVar()
        ctk.CTkEntry(main, textvariable=self._name_var, placeholder_text="(auto-generated if empty)").pack(fill="x", pady=(2, 8))

        # Prompt
        ctk.CTkLabel(main, text="Prompt:").pack(anchor="w")
        self._prompt_text = ctk.CTkTextbox(main, height=80)
        self._prompt_text.pack(fill="x", pady=(2, 8))

        # Image section
        ctk.CTkLabel(main, text="Image:").pack(anchor="w")
        img_frame = ctk.CTkFrame(main, fg_color="transparent")
        img_frame.pack(fill="x", pady=(2, 4))
        ctk.CTkButton(img_frame, text="Browse Local File", width=140, command=self._browse_image).pack(side="left", padx=(0, 8))
        ctk.CTkButton(img_frame, text="Paste URL", width=100, command=self._paste_url).pack(side="left")

        self._image_label = ctk.CTkLabel(main, text="No image selected", text_color="gray60", wraplength=420)
        self._image_label.pack(anchor="w", pady=(0, 8))

        # Advanced toggle
        self._adv_btn = ctk.CTkButton(main, text="▶ Advanced", fg_color="transparent",
                                       text_color=("gray40", "gray60"), hover=False,
                                       command=self._toggle_advanced)
        self._adv_btn.pack(anchor="w")

        self._adv_frame = ctk.CTkFrame(main, fg_color=("gray90", "gray20"))
        # (not packed until toggled)

        self._build_advanced(self._adv_frame)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="Cancel", width=110, fg_color="gray40", command=self.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Add Task", width=110, command=self._submit).pack(side="left", padx=8)

    def _build_advanced(self, parent):
        pad = {"padx": 12, "pady": 4}

        ctk.CTkLabel(parent, text="Mode:").grid(row=0, column=0, sticky="w", **pad)
        self._mode_var = tk.StringVar(value=list(GENERATION_TYPES.keys())[0])
        ctk.CTkOptionMenu(parent, variable=self._mode_var, values=list(GENERATION_TYPES.keys()), width=220).grid(row=0, column=1, sticky="w", **pad)

        ctk.CTkLabel(parent, text="Model:").grid(row=1, column=0, sticky="w", **pad)
        self._model_var = tk.StringVar(value=MODELS[0])
        ctk.CTkOptionMenu(parent, variable=self._model_var, values=MODELS, width=140).grid(row=1, column=1, sticky="w", **pad)

        ctk.CTkLabel(parent, text="Ratio:").grid(row=2, column=0, sticky="w", **pad)
        self._ratio_var = tk.StringVar(value=RATIOS[0])
        ctk.CTkOptionMenu(parent, variable=self._ratio_var, values=RATIOS, width=100).grid(row=2, column=1, sticky="w", **pad)

        ctk.CTkLabel(parent, text="Seed:").grid(row=3, column=0, sticky="w", **pad)
        self._seed_var = tk.StringVar()
        ctk.CTkEntry(parent, textvariable=self._seed_var, placeholder_text="(optional)", width=120).grid(row=3, column=1, sticky="w", **pad)

        ctk.CTkLabel(parent, text="Watermark:").grid(row=4, column=0, sticky="w", **pad)
        self._watermark_var = tk.StringVar()
        ctk.CTkEntry(parent, textvariable=self._watermark_var, placeholder_text="(optional)", width=180).grid(row=4, column=1, sticky="w", **pad)

        ctk.CTkLabel(parent, text="Enable Translation:").grid(row=5, column=0, sticky="w", **pad)
        self._translation_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(parent, text="", variable=self._translation_var).grid(row=5, column=1, sticky="w", **pad)

    def _toggle_advanced(self):
        self._advanced_visible = not self._advanced_visible
        if self._advanced_visible:
            self._adv_frame.pack(fill="x", pady=4)
            self._adv_btn.configure(text="▼ Advanced")
        else:
            self._adv_frame.pack_forget()
            self._adv_btn.configure(text="▶ Advanced")

    def _browse_image(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp"), ("All files", "*.*")]
        )
        if path:
            self._local_image = path
            short = path if len(path) <= 50 else "..." + path[-47:]
            self._image_label.configure(text=f"Local: {short}", text_color=("gray20", "gray80"))

    def _paste_url(self):
        try:
            url = self.clipboard_get().strip()
        except Exception:
            url = ""
        if url.startswith("http"):
            self._local_image = None
            self._image_label.configure(text=f"URL: {url[:60]}", text_color=("gray20", "gray80"))
            self._pasted_url = url
        else:
            self._image_label.configure(text="Clipboard doesn't contain a URL", text_color="orange")

    def _submit(self):
        prompt = self._prompt_text.get("1.0", "end").strip()
        if not prompt:
            self._prompt_text.configure(border_color="red")
            return

        image_url: Optional[str] = None
        local_image: Optional[str] = None

        if self._local_image:
            local_image = self._local_image
        elif hasattr(self, "_pasted_url"):
            image_url = self._pasted_url

        seed_str = self._seed_var.get().strip() if self._advanced_visible else ""
        seed = int(seed_str) if seed_str.isdigit() else None

        gen_type_label = self._mode_var.get() if self._advanced_visible else list(GENERATION_TYPES.keys())[0]
        gen_type = GENERATION_TYPES.get(gen_type_label, "FIRST_AND_LAST_FRAMES_2_VIDEO")

        model = self._model_var.get() if self._advanced_visible else "veo3_fast"
        ratio = self._ratio_var.get() if self._advanced_visible else "9:16"
        watermark = self._watermark_var.get().strip() if self._advanced_visible else None
        translation = self._translation_var.get() if self._advanced_visible else True

        self.result = VeoTask(
            prompt=prompt,
            image_url=image_url,
            local_image_path=local_image,
            video_name=self._name_var.get().strip() or None,
            model=model,
            generation_type=gen_type,
            aspect_ratio=ratio,
            seed=seed,
            watermark=watermark or None,
            enable_translation=translation,
        )
        self.destroy()
