# Updated ffmpeg_backend.py with helpers for Concat Deluxe family (random clip shuffle, random cuts, chaos timeline).
# Replace your current ffmpeg_backend.py with this file to add the new behavior.

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

def _make_concat_list(files):
    # create a temporary file listing files for ffmpeg concat demuxer
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for p in files:
            f.write(f"file '{os.path.abspath(p)}'\n")
    return path

def _run_ffmpeg_blocking(cmd):
    # Run ffmpeg and raise a detailed error on failure.
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as e:
        # include stderr for debugging
        raise RuntimeError(f"ffmpeg failed (rc={e.returncode}):\n{e.stderr}") from e
    return proc.stdout, proc.stderr

def _extract_segment(src, dst, start_s, duration_s):
    # Extract a segment re-encoded to ensure concat compatibility.
    # Re-encode to common codecs (libx264 + aac) to avoid stream mismatch.
    cmd = [
        FFMPEG, "-y", "-ss", f"{start_s:.3f}", "-i", src,
        "-t", f"{duration_s:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        dst
    ]
    _run_ffmpeg_blocking(cmd)

def _concat_files(file_list, dst):
    # Use concat demuxer for lossless concat (requires files to have same codecs/params)
    list_path = _make_concat_list(file_list)
    try:
        cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", dst]
        # If copy fails (codec mismatch), fallback to re-encoding concat
        try:
            _run_ffmpeg_blocking(cmd)
        except RuntimeError:
            # Re-encode concatenation: use filter_complex concat
            inputs = []
            for p in file_list:
                inputs += ["-i", p]
            n = len(file_list)
            vfilt = "".join([f"[{i}:v:0]" for i in range(n)]) + f"concat=n={n}:v=1:a=0[outv]"
            afilt = "".join([f"[{i}:a:0]" for i in range(n)]) + f"concat=n={n}:v=0:a=1[outa]"
            filter_complex = vfilt + ";" + afilt
            tmp = dst + ".tmp_reencode.mp4"
            cmd2 = [FFMPEG, "-y"] + inputs + ["-filter_complex", filter_complex, "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "192k", tmp]
            _run_ffmpeg_blocking(cmd2)
            shutil.move(tmp, dst)
    finally:
        try:
            os.remove(list_path)
        except Exception:
            pass

def _random_clip_shuffle_impl(src, dst, clip_count=6, min_len=0.5, max_len=2.5, preview=False):
    # Extract clip_count random segments from src, then shuffle and concat.
    # If preview=True, cap segment durations and count to be small.
    if preview:
        clip_count = min(4, clip_count)
        max_len = min(max_len, 1.0)
    duration = _probe_duration(src)
    if duration <= 0:
        raise RuntimeError("Cannot determine input duration for random clip shuffle.")
    temps = []
    for i in range(clip_count):
        seg_len = random.uniform(min_len, max_len)
        # choose start so segment fits
        start = random.uniform(0, max(0, duration - seg_len))
        temp_path = os.path.join(tempfile.gettempdir(), f"ytp_shuffle_{os.getpid()}_{i}.mp4")
        _extract_segment(src, temp_path, start, seg_len)
        temps.append(temp_path)
    random.shuffle(temps)
    _concat_files(temps, dst)
    # cleanup temps
    for t in temps:
        try:
            os.remove(t)
        except Exception:
            pass

def _random_cuts_impl(src, dst, cuts=30, min_len=0.05, max_len=0.3, preview=False):
    # Make many micro-cuts and reassemble randomly.
    if preview:
        cuts = min(12, cuts)
        max_len = min(max_len, 0.15)
    duration = _probe_duration(src)
    if duration <= 0:
        raise RuntimeError("Cannot determine input duration for random cuts.")
    temps = []
    for i in range(cuts):
        seg_len = random.uniform(min_len, max_len)
        start = random.uniform(0, max(0, duration - seg_len))
        temp_path = os.path.join(tempfile.gettempdir(), f"ytp_cuts_{os.getpid()}_{i}.mp4")
        _extract_segment(src, temp_path, start, seg_len)
        temps.append(temp_path)
    random.shuffle(temps)
    _concat_files(temps, dst)
    for t in temps:
        try:
            os.remove(t)
        except Exception:
            pass

def _concat_deluxe_impl(src, dst, parts=6, preview=False):
    # Split into "parts" successive parts, optionally duplicate or reverse some
    # to create YTP-like jumpiness.
    duration = _probe_duration(src)
    if duration <= 0:
        raise RuntimeError("Cannot determine input duration for concat deluxe.")
    parts = max(2, parts)
    seg_len = duration / parts
    temps = []
    for i in range(parts):
        start = i * seg_len
        temp_path = os.path.join(tempfile.gettempdir(), f"ytp_conc_{os.getpid()}_{i}.mp4")
        _extract_segment(src, temp_path, start, seg_len)
        temps.append(temp_path)
    out_list = []
    for t in temps:
        # sometimes duplicate or reverse
        r = random.random()
        if r < 0.12:
            # duplicate once
            out_list.append(t)
            out_list.append(t)
        elif r < 0.22:
            # reverse clip and append reversed version (create a reversed encoded file)
            rev = t + ".rev.mp4"
            _reverse_file(t, rev)
            out_list.append(rev)
        else:
            out_list.append(t)
    # optionally shuffle a bit
    if random.random() < 0.3:
        random.shuffle(out_list)
    _concat_files(out_list, dst)
    # cleanup
    for f in temps + [x for x in out_list if x.endswith(".rev.mp4")]:
        try:
            os.remove(f)
        except Exception:
            pass

def _chaos_timeline_impl(src, dst, segments=8, preview=False):
    # Slice input into many segments; for each segment randomly apply one of a few simple ffmpeg filters.
    # This implementation re-encodes each segment with its effect and then concatenates.
    if preview:
        segments = min(6, segments)
    duration = _probe_duration(src)
    if duration <= 0:
        raise RuntimeError("Cannot determine input duration for chaos timeline.")
    seg_len = max(0.2, duration / segments)
    processed = []
    for i in range(segments):
        start = i * seg_len
        # avoid overflow on last segment
        if start + seg_len > duration:
            seg_len = max(0.1, duration - start)
        tmp_in = os.path.join(tempfile.gettempdir(), f"ytp_chaos_in_{os.getpid()}_{i}.mp4")
        tmp_out = os.path.join(tempfile.gettempdir(), f"ytp_chaos_out_{os.getpid()}_{i}.mp4")
        _extract_segment(src, tmp_in, start, seg_len)
        # pick an effect
        choice = random.choice(["hflip", "negate", "tblend=all_mode=average,framestep=1", None, None])
        cmd = [FFMPEG, "-y", "-i", tmp_in]
        if choice:
            cmd += ["-vf", choice]
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", "-b:a", "192k", tmp_out]
        _run_ffmpeg_blocking(cmd)
        processed.append(tmp_out)
        # remove tmp_in
        try:
            os.remove(tmp_in)
        except Exception:
            pass
    _concat_files(processed, dst)
    for p in processed:
        try:
            os.remove(p)
        except Exception:
            pass

def _reverse_file(src, dst):
    # Reverse both video and audio using ffmpeg reverse filters
    cmd = [FFMPEG, "-y", "-i", src, "-vf", "reverse", "-af", "areverse", "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", dst]
    _run_ffmpeg_blocking(cmd)

def _probe_duration(path):
    # Use ffprobe to get duration (returns seconds float) - fallback to 0 on failure
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", path]
        out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(out.stdout.strip())
    except Exception:
        return 0.0

def _apply_effects_sequence(input_path, output_path, timeline: List[EffectInstance], preview=False, on_progress=None):
    """
    Build the ffmpeg processing pipeline by iterating the timeline. Special extras
    (concat deluxe markers) are handled by specific implementations that operate
    on a whole-file basis.
    """
    applied = []
    for inst in timeline:
        if not inst.enabled:
            continue
        roll = random.randint(0,100)
        if roll <= inst.probability:
            level = random.randint(1, max(1, inst.max_level))
            applied.append((inst.name, level, inst.params or {}))
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
            # Handle concat-deluxe markers first
            handled_special = False
            if extras:
                for e in extras:
                    if e == "__RANDOM_CLIP_SHUFFLE__":
                        out = os.path.join(tempdir, f"randshuffle_{idx}.mp4")
                        clip_count = params.get("clip_count", max(4, level * 2))
                        min_len = params.get("min_len", 0.2)
                        max_len = params.get("max_len", 2.0)
                        _random_clip_shuffle_impl(working, out, clip_count=clip_count, min_len=min_len, max_len=max_len, preview=preview)
                        working = out
                        handled_special = True
                        break
                    if e == "__RANDOM_CUTS__":
                        out = os.path.join(tempdir, f"randcuts_{idx}.mp4")
                        cuts = params.get("cuts", level * 10)
                        min_len = params.get("min_len", 0.03)
                        max_len = params.get("max_len", 0.25)
                        _random_cuts_impl(working, out, cuts=cuts, min_len=min_len, max_len=max_len, preview=preview)
                        working = out
                        handled_special = True
                        break
                    if e == "__CONCAT_DELUXE__":
                        out = os.path.join(tempdir, f"concatdeluxe_{idx}.mp4")
                        parts = params.get("parts", max(4, level * 2))
                        _concat_deluxe_impl(working, out, parts=parts, preview=preview)
                        working = out
                        handled_special = True
                        break
                    if e == "__CHAOS_TIMELINE__":
                        out = os.path.join(tempdir, f"chaostl_{idx}.mp4")
                        segments = params.get("segments", max(6, level * 2))
                        _chaos_timeline_impl(working, out, segments=segments, preview=preview)
                        working = out
                        handled_special = True
                        break
                if handled_special:
                    intermediates.append(working)
                    continue
            # Fallback: apply simple vf/af if present
            tmp_out = os.path.join(tempdir, f"step_{idx}.mp4")
            cmd = [FFMPEG, "-y", "-i", working]
            if vf:
                cmd += ["-vf", vf]
            if af:
                cmd += ["-af", af]
            if preview:
                cmd += ["-t", "6", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac"]
            else:
                cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac"]
            cmd.append(tmp_out)
            _run_ffmpeg_blocking(cmd)
            working = tmp_out
            intermediates.append(working)
        # finalize
        if os.path.abspath(working) != os.path.abspath(output_path):
            shutil.copyfile(working, output_path)
    finally:
        try:
            shutil.rmtree(tempdir)
        except Exception:
            pass

def process_with_effects(input_path, output_path, timeline, on_progress=None, preview=False):
    if not os.path.exists(input_path):
        raise FileNotFoundError("Input not found: " + input_path)
    _apply_effects_sequence(input_path, output_path, timeline, preview=preview, on_progress=on_progress)