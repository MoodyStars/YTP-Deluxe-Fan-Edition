"""
Effects registry and EffectInstance data structure.

This updated file ensures AddRandomSound and InjectMeme accept
params["sounds_dir"] / params["memes_dir"] so backends choose
the correct assets directory provided by GUI/CLI.
"""

from dataclasses import dataclass, asdict
import random
from typing import Dict, Any

@dataclass
class EffectInstance:
    name: str
    probability: int = 100   # 0-100
    max_level: int = 5       # 1-10
    params: Dict[str, Any] = None
    enabled: bool = True

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        return EffectInstance(
            name=d.get("name"),
            probability=d.get("probability", 100),
            max_level=d.get("max_level", 5),
            params=d.get("params", {}) or {},
            enabled=d.get("enabled", True)
        )

# --- Effect factories ---
def _effect_reverse(level, params, preview=False):
    return ("reverse", "areverse", [])

def _effect_speed(level, params, preview=False):
    lvl = max(1, min(10, level))
    factor = 0.5 + (lvl - 1) * (2.5 / 9)
    vf = f"setpts=PTS/{factor}"
    def decompose(x):
        parts = []
        while x > 2.0:
            parts.append(2.0)
            x /= 2.0
        while x < 0.5:
            parts.append(0.5)
            x /= 0.5
        if abs(x - 1.0) > 1e-6:
            parts.append(x)
        if not parts:
            parts = [1.0]
        return parts
    at_list = decompose(factor)
    af = ",".join([f"atempo={f:.6f}" for f in at_list])
    return (vf, af, [])

def _effect_invert(level, params, preview=False):
    return ("negate", None, [])

def _effect_mirror(level, params, preview=False):
    return ("hflip", None, [])

def _effect_rainbow_overlay(level, params, preview=False):
    path = params.get("overlay") if params else "assets/rainbow.png"
    return (f"overlay=10:10", None, [path])

def _effect_add_random_sound(level, params, preview=False):
    # Backend will choose a random sound from the provided directory
    sounds_dir = None
    if params:
        sounds_dir = params.get("sounds_dir") or params.get("sounds") or params.get("sounds_dir_override")
    if not sounds_dir:
        sounds_dir = "assets/sounds"
    return (None, None, [sounds_dir])

def _effect_earrape(level, params, preview=False):
    lvl = max(1, min(10, level))
    gain = 1.0 + lvl * 3.0
    return (None, f"volume={gain}", [])

def _effect_chorus(level, params, preview=False):
    delay = 40 + level * 5
    decay = 0.2 + level * 0.05
    return (None, f"aecho=0.8:0.9:{delay}|{delay*2}:{decay}|{decay*0.7}", [])

def _effect_vibrato(level, params, preview=False):
    semitones = (level - 5) * 0.5
    factor = 2 ** (semitones / 12.0)
    af = f"asetrate=44100*{factor:.5f},aresample=44100,atempo={1/factor:.5f}"
    return (None, af, [])

def _effect_stutter(level, params, preview=False):
    return ("fps=25", None, ["__STUTTER__"])

def _effect_frame_shuffle(level, params, preview=False):
    return (None, None, ["__FRAME_SHUFFLE__"])

def _effect_speed_warp(level, params, preview=False):
    return (None, None, ["__SPEED_WARP__"])

def _effect_inject_meme(level, params, preview=False):
    memes_dir = None
    if params:
        memes_dir = params.get("memes_dir") or params.get("memes") or "assets/memes"
    if not memes_dir:
        memes_dir = "assets/memes"
    # overlay default position; backend uses chosen file and the vf overlay instruction
    return ("overlay=W-w-10:10", None, [memes_dir])

def _effect_pitch_shift(level, params, preview=False):
    semitones = (level - 5) * 1.2
    factor = 2 ** (semitones / 12.0)
    af = f"asetrate=44100*{factor:.5f},aresample=44100,atempo={1/factor:.5f}"
    return (None, af, [])

def _effect_low_quality(level, params, preview=False):
    vf = f"scale=iw/2:ih/2,scale=iw*2:ih*2,format=yuv420p"
    return (vf, None, [])

# Concat / Deluxe markers (backend handles)
def _effect_concat_deluxe(level, params, preview=False):
    return (None, None, ["__CONCAT_DELUXE__"])

def _effect_random_clip_shuffle(level, params, preview=False):
    return (None, None, ["__RANDOM_CLIP_SHUFFLE__"])

def _effect_random_cuts(level, params, preview=False):
    return (None, None, ["__RANDOM_CUTS__"])

def _effect_chaos_timeline(level, params, preview=False):
    return (None, None, ["__CHAOS_TIMELINE__"])

# Registry
EFFECT_REGISTRY = {
    "Reverse": {"factory": _effect_reverse, "meta": {"description":"Reverse video & audio"}},
    "SpeedWarp": {"factory": _effect_speed, "meta": {"description":"Speed up or slow down"}},
    "InvertColors": {"factory": _effect_invert, "meta": {"description":"Invert colors"}},
    "Mirror": {"factory": _effect_mirror, "meta": {"description":"Mirror horizontally"}},
    "RainbowOverlay": {"factory": _effect_rainbow_overlay, "meta": {"description":"Overlay a rainbow (requires assets)"}},
    "AddRandomSound": {"factory": _effect_add_random_sound, "meta": {"description":"Add random sound from assets/sounds or custom dir"}},
    "Earrape": {"factory": _effect_earrape, "meta": {"description":"Extremely amplify audio"}},
    "Chorus": {"factory": _effect_chorus, "meta": {"description":"Chorus-like audio effect"}},
    "Vibrato": {"factory": _effect_vibrato, "meta": {"description":"Vibrato / small pitch bend"}},
    "StutterLoop": {"factory": _effect_stutter, "meta": {"description":"Stutter loop effect (approx)"}},
    "FrameShuffle": {"factory": _effect_frame_shuffle, "meta": {"description":"Shuffle frames randomly (experimental)"}},
    "InjectMeme": {"factory": _effect_inject_meme, "meta": {"description":"Overlay meme image/gif & audio (assets/memes or custom)"}},
    "PitchShift": {"factory": _effect_pitch_shift, "meta": {"description":"Pitch shift audio"}},
    "LowQuality": {"factory": _effect_low_quality, "meta": {"description":"Make video low quality / blocky"}},
    "ConcatDeluxe": {"factory": _effect_concat_deluxe, "meta": {"description":"Advanced concat: split, duplicate, reorder"}},
    "RandomClipShuffle": {"factory": _effect_random_clip_shuffle, "meta": {"description":"Extract random clips and shuffle them"}},
    "RandomCuts": {"factory": _effect_random_cuts, "meta": {"description":"Many micro-cuts and reassemble randomly"}},
    "ChaosTimeline": {"factory": _effect_chaos_timeline, "meta": {"description":"Slice timeline and randomly apply per-slice effects"}},
}