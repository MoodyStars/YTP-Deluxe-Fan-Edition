# Updated effects registry with Concat Deluxe family (RandomClipShuffle, RandomCuts, ConcatDeluxe, ChaosTimeline)
# Keep other effects unchanged; only additions shown here for brevity.
#
# Replace the existing effects.py with this file to include the concat deluxe features.

from dataclasses import dataclass, asdict
import random
from typing import Dict, Any, Tuple, Optional, List, Callable

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
        return EffectInstance(name=d.get("name"), probability=d.get("probability",100), max_level=d.get("max_level",5), params=d.get("params",{}), enabled=d.get("enabled",True))


# Existing effect factories (a subset - keep the original ones in your file)
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
    return (f"overlay=10:10", None, ["assets/rainbow.png"])

def _effect_add_random_sound(level, params, preview=False):
    return (None, None, ["assets/sounds/"])

def _effect_earrape(level, params, preview=False):
    lvl = max(1, min(10, level))
    gain = 1.0 + lvl * 3.0
    return (None, f"volume={gain}", [])

# --- Concat Deluxe effect factories ---
# The factories return special extras markers which the backend recognizes and runs
# advanced segment/concat logic for.

def _effect_concat_deluxe(level, params, preview=False):
    # Basic deluxe concat: split into N parts then randomly duplicate/reverse some parts.
    # We pass a marker and the backend will handle behavior and options via params.
    return (None, None, ["__CONCAT_DELUXE__"])

def _effect_random_clip_shuffle(level, params, preview=False):
    # level controls number of clips and variability. Backend will extract random clips and shuffle.
    # Pass params to backend (like desired_clip_count)
    # Provide a marker; backend will use params.get("clip_count") if present
    return (None, None, ["__RANDOM_CLIP_SHUFFLE__"])

def _effect_random_cuts(level, params, preview=False):
    # Many micro-cuts. Level controls intensity (number of cuts).
    return (None, None, ["__RANDOM_CUTS__"])

def _effect_chaos_timeline(level, params, preview=False):
    # Chaos timeline: slice timeline into many fragments and for each fragment optionally apply small effects.
    return (None, None, ["__CHAOS_TIMELINE__"])

# Keep other effect factories below or above as needed (pitch shift, stutter, etc.)
# For completeness, include a minimal set so the registry is valid.
def _effect_pitch_shift(level, params, preview=False):
    semitones = (level - 5) * 1.2
    factor = 2 ** (semitones / 12.0)
    af = f"asetrate=44100*{factor:.5f},aresample=44100,atempo={1/factor:.5f}"
    return (None, af, [])

def _effect_low_quality(level, params, preview=False):
    vf = f"scale=iw/2:ih/2,scale=iw*2:ih*2,format=yuv420p"
    return (vf, None, [])

# Registry: include the concat deluxe effects plus others
EFFECT_REGISTRY = {
    "Reverse": {"factory": _effect_reverse, "meta": {"description":"Reverse video & audio"}},
    "SpeedWarp": {"factory": _effect_speed, "meta": {"description":"Speed up or slow down"}},
    "InvertColors": {"factory": _effect_invert, "meta": {"description":"Invert colors"}},
    "Mirror": {"factory": _effect_mirror, "meta": {"description":"Mirror horizontally"}},
    "RainbowOverlay": {"factory": _effect_rainbow_overlay, "meta": {"description":"Overlay a rainbow (requires assets)"}},
    "AddRandomSound": {"factory": _effect_add_random_sound, "meta": {"description":"Add random sound from assets/sounds"}},
    "Earrape": {"factory": _effect_earrape, "meta": {"description":"Extremely amplify audio"}},
    "PitchShift": {"factory": _effect_pitch_shift, "meta": {"description":"Pitch shift audio"}},
    "LowQuality": {"factory": _effect_low_quality, "meta": {"description":"Make video low quality / blocky"}},
    # Concat Deluxe family
    "ConcatDeluxe": {"factory": _effect_concat_deluxe, "meta": {"description":"Advanced concat: split, duplicate, reverse, reorder"}},
    "RandomClipShuffle": {"factory": _effect_random_clip_shuffle, "meta": {"description":"Extract random clips and shuffle them"}},
    "RandomCuts": {"factory": _effect_random_cuts, "meta": {"description":"Make many micro-cuts and reassemble randomly"}},
    "ChaosTimeline": {"factory": _effect_chaos_timeline, "meta": {"description":"Slice timeline and randomly apply per-slice effects (experimental)"}},
}