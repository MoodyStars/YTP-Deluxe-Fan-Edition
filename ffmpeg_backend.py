"""
Backend that constructs ffmpeg commands and runs them.

This file implements how to combine video filters (-vf) and audio filters (-af),
handle extra asset injection, and process per-effect probability / level.

Note: This is a prototype. Some complex YTP effects are approximated or left as
placeholders that you can fill in with additional processing or external tools.
"""
import os
import subprocess
import shlex
import random
import glob
import tempfile
import shutil
from typing import List
from effects import EFFECT_REGISTRY, EffectInstance

FFMPEG = "ffmpeg"  # expects ffmpeg in PATH

def check_ffmpeg():
    try:
        subprocess.run([FFMPEG, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def _choose_random_asset(path):
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        files = []
        for ext in ("*.mp3","*.wav","*.m4a","*.ogg","*.mp4","*.webm","*.gif","*.png","*.jpg"):
            files.extend(glob.glob(os.path.join(path, ext)))
        if not files:
            return None
        return random.choice(files)
    return None

def _apply_effects_sequence(input_path, output_path, timeline: List[EffectInstance], preview=False, on_progress=None):
    """
    Build the ffmpeg command by iterating the timeline and combining video filters and audio filters.
    For a subset of special effect placeholders, create temporary intermediate files.
    """
    # decide which effects actually apply based on probability
    applied = []
    for inst in timeline:
        if not inst.enabled:
            continue
        roll = random.randint(0,100)
        if roll <= inst.probability:
            # choose a concrete level (1..max_level)
            level = random.randint(1, max(1, inst.max_level))
            applied.append((inst.name, level, inst.params))
    # start with the original file
    working = input_path
    tempdir = tempfile.mkdtemp(prefix="ytpdeluxe_")
    intermediates = []
    try:
        for idx, (ename, level, params) in enumerate(applied):
            meta = EFFECT_REGISTRY.get(ename)
            if not meta:
                continue
            factory = meta["factory"]
            vf, af, extras = factory(level, params, preview=preview)
            # handle special markers
            if extras:
                # if extras list contains a directory path, choose a random file
                chosen_files = []
                for e in extras:
                    if e == "__STUTTER__":
                        # implement a simple stutter: cut 0.1s segment and loop it a few times
                        tmp = os.path.join(tempdir, f"stutter_{idx}.mp4")
                        _make_stutter_clip(working, tmp, repeat=3, segment_ms=120)
                        working = tmp
                        chosen_files = []
                        break
                    if e == "__FRAME_SHUFFLE__":
                        tmp = os.path.join(tempdir, f"frameshuf_{idx}.mp4")
                        _simple_frame_shuffle(working, tmp, intensity=level)
                        working = tmp
                        chosen_files = []
                        break
                    if e == "__SPEED_WARP__":
                        tmp = os.path.join(tempdir, f"speedwarp_{idx}.mp4")
                        _simple_speed_warp(working, tmp, intensity=level)
                        working = tmp
                        chosen_files = []
                        break
                    # else choose an existing asset
                    chosen = _choose_random_asset(e)
                    if chosen:
                        chosen_files.append(chosen)
                # if chosen_files includes an audio or image, build a complex filter to overlay it
                if chosen_files:
                    # if the effect returns a vf overlay, attach overlay; if audio only, merge audio
                    if vf:
                        # overlay the first chosen file as a video/image (or gif)
                        overlay_file = chosen_files[0]
                        tmp_out = os.path.join(tempdir, f"overlay_{idx}.mp4")
                        cmd = [
                            FFMPEG, "-y", "-i", working, "-i", overlay_file,
                            "-filter_complex", vf,
                            "-map", "0:v", "-map", "0:a?",
                            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                            tmp_out
                        ]
                        _run_ffmpeg(cmd, on_progress)
                        working = tmp_out
                    else:
                        # audio overlay: mix the first chosen audio into the video
                        overlay_audio = chosen_files[0]
                        tmp_out = os.path.join(tempdir, f"audioinject_{idx}.mp4")
                        # delay overlay randomly between 0 and 2s
                        delay_ms = random.randint(0,2000)
                        cmd = [
                            FFMPEG, "-y", "-i", working, "-i", overlay_audio,
                            "-filter_complex", f"[1:a]adelay={delay_ms}|{delay_ms}[s1];[0:a][s1]amix=inputs=2:duration=first:dropout_transition=3[aout]",
                            "-map", "0:v", "-map", "[aout]",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                            tmp_out
                        ]
                        _run_ffmpeg(cmd, on_progress)
                        working = tmp_out
            else:
                # no extras, just apply video filter (vf) and/or audio filter (af)
                tmp_out = os.path.join(tempdir, f"step_{idx}.mp4")
                cmd = [FFMPEG, "-y", "-i", working]
                if vf:
                    cmd += ["-vf", vf]
                if af:
                    cmd += ["-af", af]
                # for preview use faster presets and limit duration
                if preview:
                    cmd += ["-t", "6", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac"]
                else:
                    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac"]
                cmd.append(tmp_out)
                _run_ffmpeg(cmd, on_progress)
                working = tmp_out
            intermediates.append(working)
        # final move to output
        shutil.copyfile(working, output_path)
    finally:
        # clean temp files
        try:
            shutil.rmtree(tempdir)
        except Exception:
            pass

def _run_ffmpeg(cmd, on_progress=None):
    # run ffmpeg command and stream stderr lines optionally to a progress callback
    # cmd is a list
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    for line in proc.stderr:
        if on_progress:
            on_progress(line.strip())
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + " ".join(cmd))

def process_with_effects(input_path, output_path, timeline, on_progress=None, preview=False):
    """
    Public API: process input_path with timeline (list of EffectInstance)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError("Input not found: " + input_path)
    _apply_effects_sequence(input_path, output_path, timeline, preview=preview, on_progress=on_progress)

# ---------- Simple special effect implementations ------------
def _make_stutter_clip(src, dst, repeat=3, segment_ms=100):
    # extract a small segment from 0.5s, then repeat it
    tmp = dst + ".tmp.mp4"
    cmd1 = [FFMPEG, "-y", "-ss", "0.5", "-i", src, "-t", f"{segment_ms/1000.0}", "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", tmp]
    subprocess.run(cmd1, check=True)
    inputs = []
    filter_parts = []
    cmd = [FFMPEG, "-y"]
    for i in range(repeat):
        cmd += ["-i", tmp]
    # concat
    n = repeat
    # build concat filter
    concat_parts = "".join([f"[{i}:v:0][{i}:a:0]" for i in range(n)])
    filter_complex = concat_parts + f"concat=n={n}:v=1:a=1[outv][outa]"
    cmd += ["-filter_complex", filter_complex, "-map", "[outv]", "-map", "[outa]", dst]
    subprocess.run(cmd, check=True)
    try:
        os.remove(tmp)
    except Exception:
        pass

def _simple_frame_shuffle(src, dst, intensity=5):
    # Basic approach: re-encode with frame drop/jitter using 'tblend' to create weirdness.
    # This is not a true shuffle but produces chaotic frames.
    vf = f"tblend=all_mode=average,framestep=1"
    cmd = [FFMPEG, "-y", "-i", src, "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "28", "-c:a", "copy", dst]
    subprocess.run(cmd, check=True)

def _simple_speed_warp(src, dst, intensity=5):
    # Alternate speeds: split into three segments and change their speeds randomly then concat
    tmp1 = dst + ".seg1.mp4"
    tmp2 = dst + ".seg2.mp4"
    tmp3 = dst + ".seg3.mp4"
    # create three 1s clips
    subprocess.run([FFMPEG, "-y", "-i", src, "-ss", "0", "-t", "1", "-c", "copy", tmp1], check=True)
    subprocess.run([FFMPEG, "-y", "-i", src, "-ss", "1", "-t", "1", "-c", "copy", tmp2], check=True)
    subprocess.run([FFMPEG, "-y", "-i", src, "-ss", "2", "-t", "1", "-c", "copy", tmp3], check=True)
    # modify speed of each
    def change_speed(inf, outf, factor):
        vf = f"setpts=PTS/{factor}"
        atempo_list = []
        f = factor
        while f > 2.0:
            atempo_list.append(2.0)
            f /= 2.0
        while f < 0.5:
            atempo_list.append(0.5)
            f /= 0.5
        atempo_list.append(f)
        af = ",".join([f"atempo={x:.3f}" for x in atempo_list if x!=1.0])
        cmd = [FFMPEG, "-y", "-i", inf]
        if vf: cmd += ["-vf", vf]
        if af: cmd += ["-af", af]
        cmd += ["-c:v", "libx264", "-crf", "23", "-preset", "fast", outf]
        subprocess.run(cmd, check=True)
    change_speed(tmp1, tmp1 + ".out.mp4", random.uniform(0.6, 2.0))
    change_speed(tmp2, tmp2 + ".out.mp4", random.uniform(0.6, 2.0))
    change_speed(tmp3, tmp3 + ".out.mp4", random.uniform(0.6, 2.0))
    # concat
    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", _make_concat_list([tmp1+".out.mp4", tmp2+".out.mp4", tmp3+".out.mp4"]), "-c", "copy", dst]
    subprocess.run(cmd, check=True)
    # cleanup
    for f in [tmp1, tmp2, tmp3, tmp1+".out.mp4", tmp2+".out.mp4", tmp3+".out.mp4"]:
        try:
            os.remove(f)
        except Exception:
            pass

def _make_concat_list(files):
    # create a temporary file listing files for ffmpeg concat
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for p in files:
            f.write(f"file '{os.path.abspath(p)}'\n")
    return path