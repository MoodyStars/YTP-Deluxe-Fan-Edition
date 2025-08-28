import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import random
import json

from effects import EFFECT_REGISTRY, EffectInstance
from ffmpeg_backend import process_with_effects, check_ffmpeg

CONFIG_PATH = "config.json"

class YTPPlusGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YTP+ Deluxe Edition (Prototype)")
        self.root.geometry("950x620")

        self.input_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar(value="output.mp4")
        self.timeline = []  # list of EffectInstance

        self.build_ui()
        self.load_config()

        # check ffmpeg availability and warn
        if not check_ffmpeg():
            messagebox.showwarning("ffmpeg not found", "ffmpeg binary not found in PATH. Install ffmpeg and add it to PATH.")

    def build_ui(self):
        frm = ttk.Frame(self.root, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)

        # File controls
        file_frm = ttk.LabelFrame(frm, text="Files", padding=6)
        file_frm.pack(fill=tk.X, pady=6)
        ttk.Label(file_frm, text="Input:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(file_frm, width=70, textvariable=self.input_path_var).grid(row=0, column=1, padx=6)
        ttk.Button(file_frm, text="Browse", command=self.browse_input).grid(row=0, column=2)
        ttk.Label(file_frm, text="Output:").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(file_frm, width=70, textvariable=self.output_path_var).grid(row=1, column=1, padx=6)
        ttk.Button(file_frm, text="Browse", command=self.browse_output).grid(row=1, column=2)

        # Effects list / add
        effects_frm = ttk.LabelFrame(frm, text="Effects Library", padding=6)
        effects_frm.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0,6))

        self.effects_listbox = tk.Listbox(effects_frm, height=25)
        self.effects_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for k, v in EFFECT_REGISTRY.items():
            self.effects_listbox.insert(tk.END, f"{k}: {v['meta']['description']}")

        effect_controls = ttk.Frame(effects_frm)
        effect_controls.pack(side=tk.RIGHT, fill=tk.Y, padx=6)
        ttk.Label(effect_controls, text="Probability (0-100%)").pack()
        self.prob_scale = ttk.Scale(effect_controls, from_=0, to=100, orient=tk.HORIZONTAL)
        self.prob_scale.set(100)
        self.prob_scale.pack(fill=tk.X, pady=4)
        ttk.Label(effect_controls, text="Max Level (1-10)").pack()
        self.level_scale = ttk.Scale(effect_controls, from_=1, to=10, orient=tk.HORIZONTAL)
        self.level_scale.set(5)
        self.level_scale.pack(fill=tk.X, pady=4)
        ttk.Button(effect_controls, text="Add to Timeline", command=self.add_effect_to_timeline).pack(fill=tk.X, pady=8)
        ttk.Button(effect_controls, text="Add Random Effects", command=self.add_random_effects).pack(fill=tk.X)

        # Timeline panel
        timeline_frm = ttk.LabelFrame(frm, text="Timeline (Effects Queue)", padding=6)
        timeline_frm.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        self.timeline_listbox = tk.Listbox(timeline_frm, height=18)
        self.timeline_listbox.pack(fill=tk.BOTH, expand=True)
        tl_buttons = ttk.Frame(timeline_frm)
        tl_buttons.pack(fill=tk.X, pady=6)
        ttk.Button(tl_buttons, text="Move Up", command=self.move_effect_up).pack(side=tk.LEFT, padx=4)
        ttk.Button(tl_buttons, text="Move Down", command=self.move_effect_down).pack(side=tk.LEFT, padx=4)
        ttk.Button(tl_buttons, text="Remove", command=self.remove_effect).pack(side=tk.LEFT, padx=4)
        ttk.Button(tl_buttons, text="Clear", command=self.clear_timeline).pack(side=tk.RIGHT, padx=4)

        # Render controls
        render_frm = ttk.Frame(self.root, padding=6)
        render_frm.pack(fill=tk.X)
        ttk.Button(render_frm, text="Render (Process)", command=self.render).pack(side=tk.LEFT)
        ttk.Button(render_frm, text="Preview (small)", command=self.preview).pack(side=tk.LEFT, padx=6)
        ttk.Button(render_frm, text="Save Config", command=self.save_config).pack(side=tk.RIGHT)

        # status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var).pack(fill=tk.X, pady=(6,0))

    def browse_input(self):
        path = filedialog.askopenfilename(title="Select input video", filetypes=[("Video files","*.mp4;*.mkv;*.avi;*.mov;*.webm"),("All files","*.*")])
        if path:
            self.input_path_var.set(path)

    def browse_output(self):
        path = filedialog.asksaveasfilename(title="Select output path", defaultextension=".mp4", filetypes=[("MP4 file","*.mp4"),("All files","*.*")])
        if path:
            self.output_path_var.set(path)

    def add_effect_to_timeline(self):
        sel = self.effects_listbox.curselection()
        if not sel:
            return
        line = self.effects_listbox.get(sel[0])
        effect_key = line.split(":")[0]
        prob = int(self.prob_scale.get())
        level = int(self.level_scale.get())
        inst = EffectInstance(name=effect_key, probability=prob, max_level=level, params={})
        self.timeline.append(inst)
        self.timeline_listbox.insert(tk.END, f"{effect_key} (p={prob}% lvl={level})")

    def add_random_effects(self):
        count = 3
        keys = list(EFFECT_REGISTRY.keys())
        for _ in range(count):
            k = random.choice(keys)
            prob = random.randint(30,100)
            level = random.randint(1,10)
            inst = EffectInstance(name=k, probability=prob, max_level=level, params={})
            self.timeline.append(inst)
            self.timeline_listbox.insert(tk.END, f"{k} (p={prob}% lvl={level})")

    def move_effect_up(self):
        idx = self.timeline_listbox.curselection()
        if not idx: return
        i = idx[0]
        if i == 0: return
        self.timeline[i-1], self.timeline[i] = self.timeline[i], self.timeline[i-1]
        text = self.timeline_listbox.get(i)
        self.timeline_listbox.delete(i)
        self.timeline_listbox.insert(i-1, text)
        self.timeline_listbox.selection_set(i-1)

    def move_effect_down(self):
        idx = self.timeline_listbox.curselection()
        if not idx: return
        i = idx[0]
        if i >= len(self.timeline)-1: return
        self.timeline[i+1], self.timeline[i] = self.timeline[i], self.timeline[i+1]
        text = self.timeline_listbox.get(i)
        self.timeline_listbox.delete(i)
        self.timeline_listbox.insert(i+1, text)
        self.timeline_listbox.selection_set(i+1)

    def remove_effect(self):
        idx = self.timeline_listbox.curselection()
        if not idx: return
        i = idx[0]
        self.timeline_listbox.delete(i)
        del self.timeline[i]

    def clear_timeline(self):
        self.timeline_listbox.delete(0, tk.END)
        self.timeline.clear()

    def render(self):
        input_path = self.input_path_var.get()
        output_path = self.output_path_var.get()
        if not input_path:
            messagebox.showerror("Missing input", "Please select an input file.")
            return
        if not output_path:
            messagebox.showerror("Missing output", "Please select an output file.")
            return
        # copy timeline objects to avoid UI blocking while processing
        timeline_copy = list(self.timeline)
        t = threading.Thread(target=self._render_thread, args=(input_path, output_path, timeline_copy))
        t.start()

    def _render_thread(self, input_path, output_path, timeline):
        try:
            self.set_status("Rendering...")
            process_with_effects(input_path, output_path, timeline, on_progress=self.set_status)
            self.set_status(f"Done: {output_path}")
            messagebox.showinfo("Render complete", f"Rendered to {output_path}")
        except Exception as e:
            self.set_status("Error during render")
            messagebox.showerror("Render error", str(e))

    def preview(self):
        # Build a quick small preview by taking first 6 seconds and applying effects with lower quality
        input_path = self.input_path_var.get()
        if not input_path:
            messagebox.showerror("Missing input", "Please select an input file.")
            return
        preview_output = os.path.splitext(self.output_path_var.get())[0] + "_preview.mp4"
        timeline_copy = list(self.timeline)
        t = threading.Thread(target=self._preview_thread, args=(input_path, preview_output, timeline_copy))
        t.start()

    def _preview_thread(self, input_path, preview_output, timeline):
        try:
            self.set_status("Rendering preview...")
            process_with_effects(input_path, preview_output, timeline, on_progress=self.set_status, preview=True)
            self.set_status(f"Preview done: {preview_output}")
            messagebox.showinfo("Preview complete", f"Preview written to {preview_output}")
        except Exception as e:
            self.set_status("Error during preview")
            messagebox.showerror("Preview error", str(e))

    def set_status(self, msg):
        self.status_var.set(msg)

    def save_config(self):
        data = {
            "input": self.input_path_var.get(),
            "output": self.output_path_var.get(),
            "timeline": [inst.to_dict() for inst in self.timeline]
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.set_status("Config saved")

    def load_config(self):
        try:
            if not os.path.exists(CONFIG_PATH):
                return
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.input_path_var.set(data.get("input",""))
            self.output_path_var.set(data.get("output","output.mp4"))
            for it in data.get("timeline", []):
                inst = EffectInstance.from_dict(it)
                self.timeline.append(inst)
                self.timeline_listbox.insert(tk.END, f"{inst.name} (p={inst.probability}% lvl={inst.max_level})")
            self.set_status("Config loaded")
        except Exception:
            self.set_status("Failed to load config")

    def run(self):
        self.root.mainloop()