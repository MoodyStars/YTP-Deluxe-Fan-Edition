YTP+ Deluxe Edition — Python + ffmpeg (Tkinter GUI)
==================================================

Overview
--------
This is a prototype YTP (YouTube Poop) effects editor for Windows 7 / 8.1 implemented in Python with a Tkinter GUI. It uses the system ffmpeg executable (must be installed separately) to apply audio/video filters and generate results.

Features included (implemented or scaffolded)
- Add Random Sound (audio overlay)
- Reverse Clip (video & audio)
- Speed Up / Slow Down
- Chorus Effect (approx via aecho)
- Vibrato / Pitch Bend (asetrate + atempo approximation)
- Stutter Loop
- Earrape Mode (large gain)
- Auto-Tune Chaos (placeholder — requires external autotune tool)
- Add Dance & Squidward Mode (video transforms)
- Invert Colors
- Rainbow Overlay (overlay PNG/GIF, user-provided)
- Mirror Mode
- Sus Effect (random pitch/tempo)
- Explosion Spam (repetitive overlays)
- Frame Shuffle (placeholder; sample simple implementation)
- Meme Injection (overlay image/audio; user provides assets)
- Sentence Mixing / Random Clip Shuffle / Random Cuts
- Effect toggles per effect and per-effect probability and max level
- Plugin-style effect registry — easily add new effects

Requirements
------------
- Python 3.7+ (3.8 recommended for Windows 7/8.1)
- ffmpeg in PATH (download from https://ffmpeg.org)
- No extra pip packages required (uses builtin Tkinter, subprocess, json)

Quick start
-----------
1. Install ffmpeg and ensure the ffmpeg binary is available on PATH.
2. Place any custom assets (memes, overlays, sounds) in the assets/ folder (see assets/README).
3. Run:
   python main.py
4. Use the GUI to pick an input file, add effects, set probability / level, and click "Render".

Extending
---------
- Add new effects in effects.py and register them in EFFECT_REGISTRY.
- For advanced audio effects (autotune, pitch detection) integrate an external tool (e.g. open-source autotune libs or Rubber Band) and call it from ffmpeg_backend or a custom wrapper.

License
-------
MIT
```
