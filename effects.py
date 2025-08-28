"""
Effects registry and EffectInstance data structure.

Add new effects by registering a function in EFFECT_REGISTRY with a factory
that builds ffmpeg filter graph fragments based on effect parameters and level.
"""

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


# Each registry entry provides a small meta dict and a function that,
# when called with (level, params, preview) returns a tuple:
# (video_filter_str_or_none, audio_filter_str_or_none, extra_files_list)
#
# If the effect only affects audio, return video None and vice versa.
# extra_files_list can be paths to overlay images/audio the backend should include.

def _effect_reverse(level, params, preview=False):
    return ("reverse", "areverse", [])

def _effect_speed(level, params, preview=False):
    # level 1..10 => speed factor 0.5..3.0 mapped
    lvl = max(1, min(10, level))
    factor = 0.5 + (lvl - 1) * (2.5 / 9)  # 0.5 .. 3.0
    # video setpts=PTS/FACTOR
    vf = f"setpts=PTS/{factor}"
    # audio: atempo supports 0.5-2.0; for other values chain
    atempo = []
    remain = factor
    # To keep pitch consistent we won't change pitch here, just tempo.
    # For factor <1 (slowdown), atempo <1; for >1 atempo>1
    # ffmpeg's atempo accepts 0.5-2.0, chain by multiplying
    # We will create a chain that multiplies to factor
    # Simplify by close approximation: decompose factor into products of 2 or between 0.5-2
    def decompose(x):
        factors=[]
        # target is to reach x by multiplying a list each in [0.5,2]
        if x < 0.5:
            # chain slowdown by 0.5 repeatedly and one final remainder
            while x < 0.5:
                factors.append(0.5)
                x /= 0.5
            if x != 1.0:
                factors.append(x)
        elif x > 2.0:
            while x > 2.0:
                factors.append(2.0)
                x /= 2.0
            if x != 1.0:
                factors.append(x)
        else:
            factors.append(x)
        return factors
    at_list = decompose(factor)
    af = "|".join([f"atempo={f:.3f}" for f in at_list])
    return (vf, af, [])

def _effect_invert(level, params, preview=False):
    return ("negate", None, [])

def _effect_mirror(level, params, preview=False):
    # horizontal mirror
    return ("hflip", None, [])

def _effect_rainbow_overlay(level, params, preview=False):
    # requires assets/rainbow.png in assets
    return (f"overlay=10:10", None, ["assets/rainbow.png"])

def _effect_add_random_sound(level, params, preview=False):
    # backend will pick a random audio from assets/sounds/
    return (None, None, ["assets/sounds/"])  # marker for backend to choose random

def _effect_earrape(level, params, preview=False):
    # amplify audio by a large gain controlled by level
    lvl = max(1, min(10, level))
    gain = 1.0 + lvl * 3.0  # 4x..31x
    return (None, f"volume={gain}", [])

def _effect_chorus(level, params, preview=False):
    # approximate chorus using aecho
    delay = 40 + level * 5
    decay = 0.2 + level * 0.05
    return (None, f"aecho=0.8:0.9:{delay}|{delay*2}:{decay}|{decay*0.7}", [])

def _effect_vibrato(level, params, preview=False):
    # vibrato (pitch modulation) approx via atempo varying is hard; we'll approximate by slight pitch shift
    semitones = (level - 5) * 0.5  # -2.5..+2.5
    factor = 2 ** (semitones / 12.0)
    af = f"asetrate=44100*{factor:.5f},aresample=44100,atempo={1/factor:.5f}"
    return (None, af, [])

def _effect_stutter(level, params, preview=False):
    # repeat short subclips to create stutter. We'll implement as a filter placeholder; backend will implement
    return ("fps=25", None, ["__STUTTER__"])

def _effect_frame_shuffle(level, params, preview=False):
    return (None, None, ["__FRAME_SHUFFLE__"])

def _effect_speed_warp(level, params, preview=False):
    # a fun speed warp that rapidly alternates speed
    return (None, None, ["__SPEED_WARP__"])

def _effect_inject_meme(level, params, preview=False):
    # asks backend to overlay a random meme image/gif and possibly an audio clip
    return ("overlay=W-w-10:10", None, ["assets/memes/"])

def _effect_pitch_shift(level, params, preview=False):
    # semitone shift
    semitones = (level - 5) * 1.2
    factor = 2 ** (semitones / 12.0)
    af = f"asetrate=44100*{factor:.5f},aresample=44100,atempo={1/factor:.5f}"
    return (None, af, [])

def _effect_low_quality(level, params, preview=False):
    q = 30 + level * 5
    vf = f"scale=iw/2:ih/2,scale=iw*2:ih*2,format=yuv420p"
    return (vf, None, [])

# Registry
EFFECT_REGISTRY = {
    "Reverse": {"factory": _effect_reverse, "meta": {"description":"Reverse video & audio"}},
    "SpeedWarp": {"factory": _effect_speed, "meta": {"description":"Speed up or slow down"}},
    "InvertColors": {"factory": _effect_invert, "meta": {"description":"Invert colors"}},
    "Mirror": {"factory": _effect_mirror, "meta": {"description":"Mirror horizontally"}},
    "RainbowOverlay": {"factory": _effect_rainbow_overlay, "meta": {"description":"Overlay a rainbow (requires assets)"}},
    "AddRandomSound": {"factory": _effect_add_random_sound, "meta": {"description":"Add random sound from assets/sounds"}},
    "Earrape": {"factory": _effect_earrape, "meta": {"description":"Extremely amplify audio"}},
    "Chorus": {"factory": _effect_chorus, "meta": {"description":"Chorus-like audio effect"}},
    "Vibrato": {"factory": _effect_vibrato, "meta": {"description":"Vibrato / small pitch bend"}},
    "StutterLoop": {"factory": _effect_stutter, "meta": {"description":"Stutter loop effect (approx)"}},
    "FrameShuffle": {"factory": _effect_frame_shuffle, "meta": {"description":"Shuffle frames randomly (experimental)"}},
    "InjectMeme": {"factory": _effect_inject_meme, "meta": {"description":"Overlay meme image/gif & audio (assets/memes)"}},
    "PitchShift": {"factory": _effect_pitch_shift, "meta": {"description":"Pitch shift audio"}},
    "LowQuality": {"factory": _effect_low_quality, "meta": {"description":"Make video low quality / blocky"}},
    # More entries can be added below as placeholders for the huge feature list
    # "AutoTuneChaos": {...}
}