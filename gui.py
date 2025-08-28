import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import random
import json
import tempfile
import subprocess
import shutil

from effects import EFFECT_REGISTRY, EffectInstance
from ffmpeg_backend import process_with_effects, check_ffmpeg

CONFIG_PATH = "config.json"

class YTPPlusGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YTP+ Deluxe Fan Edition (Prototype)")
        self.root.geometry("1000x720")

        self.input_path_var = tk.StringVar()
        self.output_path_var = tk.StringVar(value="output.mp4")
        self.intro_path_var = tk.StringVar()
        self.memes_dir_var = tk.StringVar(value=os.path.join("assets", "memes"))
        self.sounds_dir_var = tk.StringVar(value=os.path.join("assets", "sounds"))
        self.xp_sounds_dir_var = tk.StringVar(value=os.path.join("assets", "xp_sounds"))

        self.use_memes_var = tk.BooleanVar(value=False)
        self.meme_count_var = tk.IntVar(value=2)
        self.use_sounds_var = tk.BooleanVar(value=False)
        self.sound_count_var = tk.IntVar(value=2)
        self.use_xp_var = tk.BooleanVar(value=False)
        self.xp_sound_count_var = tk.IntVar(value=2)

        self.min_stream_var = tk.DoubleVar(value=0.2)
        self.max_stream_var = tk.DoubleVar(value=2.0)
        self.clip_count_var = tk.IntVar(value=6)

        self.effects_deluxe_var = tk.BooleanVar(value=False)
        self.concat_deluxe_var = tk.BooleanVar(value=False)
        self.random_clip_shuffle_var = tk.BooleanVar(value=False)
        self.random_cuts_var = tk.BooleanVar(value=False)

        self.timeline = []  # list of EffectInstance

        self.build_ui()
        self.load_config()

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
        ttk.Label(file_frm, text="Intro (optional):").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(file_frm, width=70, textvariable=self.intro_path_var).grid(row=2, column=1, padx=6)
        ttk.Button(file_frm, text="Browse Intro", command=self.browse_intro).grid(row=2, column=2)

        # Options column
        options_frm = ttk.LabelFrame(frm, text="Quick Options", padding=6)
        options_frm.pack(fill=tk.X, pady=6)
        ttk.Checkbutton(options_frm, text="Effects Deluxe (demo set)", variable=self.effects_deluxe_var).grid(row=0, column=0, sticky=tk.W, padx=4)
        ttk.Checkbutton(options_frm, text="Concat Deluxe", variable=self.concat_deluxe_var).grid(row=0, column=1, sticky=tk.W, padx=4)
        ttk.Checkbutton(options_frm, text="Random Clip Shuffle", variable=self.random_clip_shuffle_var).grid(row=0, column=2, sticky=tk.W, padx=4)
        ttk.Checkbutton(options_frm, text="Random Cuts", variable=self.random_cuts_var).grid(row=0, column=3, sticky=tk.W, padx=4)

        # Meme / Sound options
        assets_frm = ttk.LabelFrame(frm, text="Memes & Sounds", padding=6)
        assets_frm.pack(fill=tk.X, pady=6)
        ttk.Checkbutton(assets_frm, text="Use Memes", variable=self.use_memes_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(assets_frm, text="Memes Dir:").grid(row=0, column=1, sticky=tk.E)
        ttk.Entry(assets_frm, textvariable=self.memes_dir_var, width=40).grid(row=0, column=2, padx=6)
        ttk.Button(assets_frm, text="Browse", command=self.browse_memes).grid(row=0, column=3)
        ttk.Label(assets_frm, text="Count:").grid(row=0, column=4)
        ttk.Spinbox(assets_frm, from_=0, to=20, textvariable=self.meme_count_var, width=5).grid(row=0, column=5)

        ttk.Checkbutton(assets_frm, text="Use Random Sounds", variable=self.use_sounds_var).grid(row=1, column=0, sticky=tk.W)
        ttk.Label(assets_frm, text="Sounds Dir:").grid(row=1, column=1, sticky=tk.E)
        ttk.Entry(assets_frm, textvariable=self.sounds_dir_var, width=40).grid(row=1, column=2, padx=6)
        ttk.Button(assets_frm, text="Browse", command=self.browse_sounds).grid(row=1, column=3)
        ttk.Label(assets_frm, text="Count:").grid(row=1, column=4)
        ttk.Spinbox(assets_frm, from_=0, to=20, textvariable=self.sound_count_var, width=5).grid(row=1, column=5)

        ttk.Checkbutton(assets_frm, text="Use Windows XP Sounds", variable=self.use_xp_var).grid(row=2, column=0, sticky=tk.W)
        ttk.Label(assets_frm, text="XP Sounds Dir:").grid(row=2, column=1, sticky=tk.E)
        ttk.Entry(assets_frm, textvariable=self.xp_sounds_dir_var, width=40).grid(row=2, column=2, padx=6)
        ttk.Button(assets_frm, text="Browse", command=self.browse_xp_sounds).grid(row=2, column=3)
        ttk.Label(assets_frm, text="Count:").grid(row=2, column=4)
        ttk.Spinbox(assets_frm, from_=0, to=20, textvariable=self.xp_sound_count_var, width=5).grid(row=2, column=5)

        # Clip duration / count options
        clip_frm = ttk.LabelFrame(frm, text="Clip / Stream Bounds", padding=6)
        clip_frm.pack(fill=tk.X, pady=6)
        ttk.Label(clip_frm, text="Min stream duration (s):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(clip_frm, textvariable=self.min_stream_var, width=10).grid(row=0, column=1, padx=6)
        ttk.Label(clip_frm, text="Max stream duration (s):").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(clip_frm, textvariable=self.max_stream_var, width=10).grid(row=0, column=3, padx=6)
        ttk.Label(clip_frm, text="Clip count:").grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(clip_frm, textvariable=self.clip_count_var, width=6).grid(row=0, column=5, padx=6)

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
        self.timeline_listbox = tk.Listbox(timeline_frm, height=20)
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

    # --- Browse helpers ---
    def browse_input(self):
        path = filedialog.askopenfilename(title="Select input video", filetypes=[("Video files","*.mp4;*.mkv;*.avi;*.mov;*.webm"),("All files","*.*")])
        if path:
            self.input_path_var.set(path)

    def browse_output(self):
        path = filedialog.asksaveasfilename(title="Select output path", defaultextension=".mp4", filetypes=[("MP4 file","*.mp4"),("All files","*.*")])
        if path:
            self.output_path_var.set(path)

    def browse_intro(self):
        path = filedialog.askopenfilename(title="Select intro video", filetypes=[("Video files","*.mp4;*.mov;*.mkv"),("All files","*.*")])
        if path:
            self.intro_path_var.set(path)

    def browse_memes(self):
        path = filedialog.askdirectory(title="Select memes directory")
        if path:
            self.memes_dir_var.set(path)

    def browse_sounds(self):
        path = filedialog.askdirectory(title="Select sounds directory")
        if path:
            self.sounds_dir_var.set(path)

    def browse_xp_sounds(self):
        path = filedialog.askdirectory(title="Select XP sounds directory")
        if path:
            self.xp_sounds_dir_var.set(path)

    # --- Timeline manipulation ---
    def add_effect_to_timeline(self):
        sel = self.effects_listbox.curselection()
        if not sel:
            return
        line = self.effects_listbox.get(sel[0])
        effect_key = line.split(":")[0]
        prob = int(self.prob_scale.get())
        level = int(self.level_scale.get())
        params = {}
        # inject current default dirs for meme/sound effects
        if effect_key == "InjectMeme":
            params["memes_dir"] = self.memes_dir_var.get()
        if effect_key == "AddRandomSound":
            params["sounds_dir"] = self.sounds_dir_var.get()
        inst = EffectInstance(name=effect_key, probability=prob, max_level=level, params=params)
        self.timeline.append(inst)
        self.timeline_listbox.insert(tk.END, f"{effect_key} (p={prob}% lvl={level})")

    def add_random_effects(self):
        count = 3
        keys = list(EFFECT_REGISTRY.keys())
        for _ in range(count):
            k = random.choice(keys)
            prob = random.randint(30,100)
            level = random.randint(1,10)
            params = {}
            if k == "InjectMeme":
                params["memes_dir"] = self.memes_dir_var.get()
            if k == "AddRandomSound":
                params["sounds_dir"] = self.sounds_dir_var.get()
            inst = EffectInstance(name=k, probability=prob, max_level=level, params=params)
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

    # --- Render / preview ---
    def render(self):
        input_path = self.input_path_var.get()
        output_path = self.output_path_var.get()
        if not input_path:
            messagebox.showerror("Missing input", "Please select an input file.")
            return
        if not output_path:
            messagebox.showerror("Missing output", "Please select an output file.")
            return
        t = threading.Thread(target=self._render_thread, args=(input_path, output_path, False))
        t.start()

    def _render_thread(self, input_path, output_path, preview_flag):
        try:
            self.set_status("Preparing timeline...")
            timeline_copy = self._build_timeline_for_render()
            # handle intro if provided -> create working input
            working_input = input_path
            tempdir = None
            if self.intro_path_var.get():
                tempdir = tempfile.mkdtemp(prefix="ytp_intro_")
                tmp_with_intro = os.path.join(tempdir, "with_intro.mp4")
                try:
                    self.set_status("Merging intro...")
                    self._reencode_concat([self.intro_path_var.get(), input_path], tmp_with_intro)
                    working_input = tmp_with_intro
                except Exception as e:
                    shutil.rmtree(tempdir, ignore_errors=True)
                    raise
            self.set_status("Rendering...")
            process_with_effects(working_input, output_path, timeline_copy, on_progress=self.set_status, preview=preview_flag)
            self.set_status(f"Done: {output_path}")
            messagebox.showinfo("Render complete", f"Rendered to {output_path}")
        except Exception as e:
            self.set_status("Error during render")
            messagebox.showerror("Render error", str(e))
        finally:
            if 'tempdir' in locals() and tempdir:
                try:
                    shutil.rmtree(tempdir)
                except Exception:
                    pass

    def preview(self):
        input_path = self.input_path_var.get()
        if not input_path:
            messagebox.showerror("Missing input", "Please select an input file.")
            return
        preview_output = os.path.splitext(self.output_path_var.get())[0] + "_preview.mp4"
        t = threading.Thread(target=self._preview_thread, args=(input_path, preview_output))
        t.start()

    def _preview_thread(self, input_path, preview_output):
        try:
            self.set_status("Building preview timeline...")
            timeline_copy = self._build_timeline_for_render()
            self.set_status("Rendering preview...")
            process_with_effects(input_path, preview_output, timeline_copy, on_progress=self.set_status, preview=True)
            self.set_status(f"Preview done: {preview_output}")
            messagebox.showinfo("Preview complete", f"Preview written to {preview_output}")
        except Exception as e:
            self.set_status("Error during preview")
            messagebox.showerror("Preview error", str(e))

    def _build_timeline_for_render(self):
        # start with user timeline items
        tlist = [EffectInstance(name=inst.name, probability=inst.probability, max_level=inst.max_level, params=dict(inst.params or {}), enabled=inst.enabled) for inst in self.timeline]
        # add quick options selected from the GUI
        if self.effects_deluxe_var.get():
            demo_effects = ["InvertColors", "Mirror", "StutterLoop", "PitchShift", "LowQuality"]
            for name in demo_effects:
                tlist.append(EffectInstance(name=name, probability=80, max_level=4, params={}))
        if self.concat_deluxe_var.get():
            tlist.append(EffectInstance(name="ConcatDeluxe", probability=100, max_level=5, params={"parts": self.clip_count_var.get()}))
        if self.random_clip_shuffle_var.get():
            tlist.append(EffectInstance(name="RandomClipShuffle", probability=100, max_level=5, params={"clip_count": self.clip_count_var.get(), "min_len": self.min_stream_var.get(), "max_len": self.max_stream_var.get()}))
        if self.random_cuts_var.get():
            tlist.append(EffectInstance(name="RandomCuts", probability=100, max_level=5, params={"cuts": self.clip_count_var.get(), "min_len": self.min_stream_var.get(), "max_len": self.max_stream_var.get()}))
        if self.use_memes_var.get():
            for _ in range(max(1, self.meme_count_var.get())):
                tlist.append(EffectInstance(name="InjectMeme", probability=95, max_level=5, params={"memes_dir": self.memes_dir_var.get()}))
        if self.use_sounds_var.get():
            for _ in range(max(1, self.sound_count_var.get())):
                tlist.append(EffectInstance(name="AddRandomSound", probability=95, max_level=5, params={"sounds_dir": self.sounds_dir_var.get()}))
        if self.use_xp_var.get():
            for _ in range(max(1, self.xp_sound_count_var.get())):
                tlist.append(EffectInstance(name="AddRandomSound", probability=95, max_level=5, params={"sounds_dir": self.xp_sounds_dir_var.get()}))
        return tlist

    def _reencode_concat(self, files, out_path):
        if not files:
            raise ValueError("No files to concat")
        cmd = ["ffmpeg", "-y"]
        for f in files:
            cmd += ["-i", f]
        n = len(files)
        v_inputs = "".join([f"[{i}:v:0]" for i in range(n)])
        a_inputs = "".join([f"[{i}:a:0]" for i in range(n)])
        filter_complex = f"{v_inputs}{a_inputs}concat=n={n}:v=1:a=1[outv][outa]"
        cmd += ["-filter_complex", filter_complex, "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "192k",
                out_path]
        subprocess.run(cmd, check=True)

    # --- Config save/load / status ---
    def save_config(self):
        data = {
            "input": self.input_path_var.get(),
            "output": self.output_path_var.get(),
            "intro": self.intro_path_var.get(),
            "memes_dir": self.memes_dir_var.get(),
            "sounds_dir": self.sounds_dir_var.get(),
            "xp_sounds_dir": self.xp_sounds_dir_var.get(),
            "use_memes": self.use_memes_var.get(),
            "meme_count": self.meme_count_var.get(),
            "use_sounds": self.use_sounds_var.get(),
            "sound_count": self.sound_count_var.get(),
            "use_xp": self.use_xp_var.get(),
            "xp_sound_count": self.xp_sound_count_var.get(),
            "min_stream": self.min_stream_var.get(),
            "max_stream": self.max_stream_var.get(),
            "clip_count": self.clip_count_var.get(),
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
            self.intro_path_var.set(data.get("intro",""))
            self.memes_dir_var.set(data.get("memes_dir", self.memes_dir_var.get()))
            self.sounds_dir_var.set(data.get("sounds_dir", self.sounds_dir_var.get()))
            self.xp_sounds_dir_var.set(data.get("xp_sounds_dir", self.xp_sounds_dir_var.get()))
            self.use_memes_var.set(data.get("use_memes", False))
            self.meme_count_var.set(data.get("meme_count", 2))
            self.use_sounds_var.set(data.get("use_sounds", False))
            self.sound_count_var.set(data.get("sound_count", 2))
            self.use_xp_var.set(data.get("use_xp", False))
            self.xp_sound_count_var.set(data.get("xp_sound_count", 2))
            self.min_stream_var.set(data.get("min_stream", 0.2))
            self.max_stream_var.set(data.get("max_stream", 2.0))
            self.clip_count_var.set(data.get("clip_count", 6))
            for it in data.get("timeline", []):
                inst = EffectInstance.from_dict(it)
                self.timeline.append(inst)
                self.timeline_listbox.insert(tk.END, f"{inst.name} (p={inst.probability}% lvl={inst.max_level})")
            self.set_status("Config loaded")
        except Exception:
            self.set_status("Failed to load config")

    def set_status(self, msg):
        try:
            self.status_var.set(str(msg))
        except Exception:
            pass

    def run(self):
        self.root.mainloop()