"""Spectral analysis and scoring.

A lossy encoder throws away the top of the spectrum and leaves a brick wall
behind. Real recordings do not have one. This module measures the long-term
average spectrum, looks for that wall, and turns what it finds into a score.

Nothing here builds a sentence: results carry message codes from `i18n`, so
the same analysis renders in any language the caller asks for.
"""

import ctypes
import ctypes.util
import math
import os

SFM_READ = 0x10
SUBMASK = 0x0000FFFF
TYPEMASK = 0x0FFF0000

SUBTYPES = {
    0x0001: ("PCM 8", 8), 0x0002: ("PCM 16", 16), 0x0003: ("PCM 24", 24),
    0x0004: ("PCM 32", 32), 0x0005: ("PCM u8", 8), 0x0006: ("float32", 32),
    0x0007: ("float64", 64),
}
CONTAINERS = {0x010000: "WAV", 0x020000: "AIFF", 0x040000: "AU",
              0x170000: "FLAC", 0x180000: "CAF", 0x200000: "OGG",
              0x230000: "MPEG"}

EXTENSIONS = (".flac", ".wav", ".aiff", ".aif", ".ogg", ".oga", ".au",
              ".caf", ".w64")

FFT_SIZE = 4096
MAX_WINDOWS = 90

# A wall this steep across this narrow a span does not occur in nature.
WALL_DB = 18.0
STEP_DB = 12.0
WALL_SPAN_HZ = 600.0
# Above this the wall is close enough to Nyquist to be a resampler artefact.
LOSSY_CEILING_HZ = 20700.0


class _SfInfo(ctypes.Structure):
    _fields_ = [("frames", ctypes.c_int64), ("samplerate", ctypes.c_int),
                ("channels", ctypes.c_int), ("format", ctypes.c_int),
                ("sections", ctypes.c_int), ("seekable", ctypes.c_int)]


def _load_libsndfile():
    for name in ("libsndfile.so.1", "libsndfile.so", "libsndfile.dylib",
                 "sndfile.dll"):
        try:
            return ctypes.CDLL(name)
        except OSError:
            continue
    found = ctypes.util.find_library("sndfile")
    if found:
        return ctypes.CDLL(found)
    raise RuntimeError(
        "libsndfile not found. Install it: "
        "apt install libsndfile1 / brew install libsndfile")


_SF = _load_libsndfile()
_SF.sf_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(_SfInfo)]
_SF.sf_open.restype = ctypes.c_void_p
_SF.sf_close.argtypes = [ctypes.c_void_p]
_SF.sf_seek.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_int]
_SF.sf_seek.restype = ctypes.c_int64
_SF.sf_readf_int.argtypes = [ctypes.c_void_p,
                             ctypes.POINTER(ctypes.c_int32), ctypes.c_int64]
_SF.sf_readf_int.restype = ctypes.c_int64
_SF.sf_strerror.argtypes = [ctypes.c_void_p]
_SF.sf_strerror.restype = ctypes.c_char_p


def fft(buf):
    """In-place iterative radix-2 FFT. Pure Python on purpose: the whole
    point of this tool is that it runs with nothing installed."""
    n = len(buf)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            buf[i], buf[j] = buf[j], buf[i]
    size = 2
    while size <= n:
        ang = -2.0 * math.pi / size
        step = complex(math.cos(ang), math.sin(ang))
        half = size >> 1
        for start in range(0, n, size):
            w = 1.0 + 0j
            for k in range(start, start + half):
                u = buf[k]
                v = buf[k + half] * w
                buf[k] = u + v
                buf[k + half] = u - v
                w *= step
        size <<= 1
    return buf


def _trailing_zero_bits(v):
    if v == 0:
        return 32
    n = 0
    while not v & 1:
        v >>= 1
        n += 1
    return n


def _moving_average(xs, width):
    n = len(xs)
    out = [0.0] * n
    half = width // 2
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        out[i] = sum(xs[lo:hi]) / (hi - lo)
    return out


def _interpolate(x, points):
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    return points[-1][1]


def analyse(path):
    """Measure one file. Returns a dict; on failure it has an 'error' key
    holding an i18n code."""
    info = _SfInfo()
    handle = _SF.sf_open(str(path).encode("utf-8"), SFM_READ,
                         ctypes.byref(info))
    if not handle:
        return {"error": "err.unread", "name": os.path.basename(str(path)),
                "detail": _SF.sf_strerror(None).decode("utf-8", "replace")}

    rate, channels, frames = info.samplerate, info.channels, info.frames
    subtype, container = info.format & SUBMASK, info.format & TYPEMASK
    subtype_name, declared_bits = SUBTYPES.get(subtype, ("unknown", 16))
    container_name = CONTAINERS.get(container, "0x%06x" % container)

    if frames < FFT_SIZE * 2 or channels < 1:
        _SF.sf_close(handle)
        return {"error": "err.short", "name": os.path.basename(str(path))}

    window = [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (FFT_SIZE - 1))
              for i in range(FFT_SIZE)]

    # Skip the first and last 5%: fade-ins and run-out grooves are not
    # representative of the material.
    margin = int(frames * 0.05)
    usable = frames - 2 * margin
    count = min(MAX_WINDOWS, max(1, usable // FFT_SIZE))
    stride = max(FFT_SIZE, usable // count)

    frame_buf = (ctypes.c_int32 * (FFT_SIZE * channels))()
    bins = FFT_SIZE // 2
    power = [0.0] * bins
    taken = 0
    bits_seen = 0
    peak = 0
    # One LSB below full scale, in the 32-bit left-justified domain.
    clip_level = (1 << 31) - (1 << (32 - max(8, min(32, declared_bits))))
    clipped = clip_runs = run = total = 0

    for index in range(count):
        pos = margin + index * stride
        if pos + FFT_SIZE > frames:
            break
        if _SF.sf_seek(handle, pos, 0) < 0:
            break
        if _SF.sf_readf_int(handle, frame_buf, FFT_SIZE) < FFT_SIZE:
            break

        signal = [0j] * FFT_SIZE
        for i in range(FFT_SIZE):
            base = i * channels
            left = frame_buf[base]
            mag_l = left if left >= 0 else -left
            bits_seen |= mag_l & 0xFFFFFFFF
            at_ceiling = mag_l >= clip_level
            if channels > 1:
                right = frame_buf[base + 1]
                mag_r = right if right >= 0 else -right
                bits_seen |= mag_r & 0xFFFFFFFF
                at_ceiling = at_ceiling or mag_r >= clip_level
                peak = max(peak, mag_r)
                mid = (left + right) * 0.5
            else:
                mid = float(left)
            peak = max(peak, mag_l)
            total += 1
            if at_ceiling:
                clipped += 1
                run += 1
                if run == 3:
                    clip_runs += 1
            else:
                run = 0
            signal[i] = complex(mid * window[i] / 2147483648.0, 0.0)

        fft(signal)
        for k in range(bins):
            z = signal[k]
            power[k] += z.real * z.real + z.imag * z.imag
        taken += 1

    _SF.sf_close(handle)
    if taken == 0:
        return {"error": "err.unread", "name": os.path.basename(str(path))}

    db = [10.0 * math.log10(power[k] / taken + 1e-30) for k in range(bins)]
    loudest = max(db)
    db = [d - loudest for d in db]
    smoothed = _moving_average(db, 9)

    bin_hz = rate / float(FFT_SIZE)
    nyquist = rate / 2.0

    # Where the noise floor finally gives out. Dither reaches Nyquist on
    # almost any real file, so on its own this proves very little.
    floor_reach = nyquist
    for k in range(bins - 1, 0, -1):
        if smoothed[k] > -90.0:
            floor_reach = k * bin_hz
            break

    span = max(1, int(WALL_SPAN_HZ / bin_hz))
    wall_db = 0.0
    wall_hz = 0.0
    for k in range(int(8000.0 / bin_hz), bins - span):
        drop = smoothed[k] - smoothed[k + span]
        if drop > wall_db:
            wall_db = drop
            wall_hz = k * bin_hz

    near_nyquist = wall_hz >= nyquist - 800.0
    has_wall = wall_db >= WALL_DB and not near_nyquist
    has_step = (not has_wall) and wall_db >= STEP_DB and not near_nyquist
    bandwidth = wall_hz if has_wall else floor_reach

    effective_bits = 32 - _trailing_zero_bits(bits_seen) if bits_seen else 0
    peak_dbfs = 20.0 * math.log10(peak / 2147483648.0) if peak else -999.0

    chart = []
    for i in range(130):
        k0 = int(i * bins / 130)
        k1 = max(k0 + 1, int((i + 1) * bins / 130))
        chart.append([round(k0 * bin_hz / 1000.0, 2),
                      round(max(smoothed[k0:k1]), 1)])

    result = {
        "path": str(path), "name": os.path.basename(str(path)),
        "size": os.path.getsize(path),
        "rate": rate, "channels": channels, "frames": frames,
        "duration": frames / float(rate),
        "container": container_name, "subtype": subtype_name,
        "declared_bits": declared_bits, "effective_bits": effective_bits,
        "nyquist": nyquist, "floor_reach": floor_reach, "bandwidth": bandwidth,
        "wall_db": round(wall_db, 1), "wall_hz": round(wall_hz, 1),
        "has_wall": has_wall, "has_step": has_step,
        "peak_dbfs": round(peak_dbfs, 2),
        "clip_ratio": clipped / float(total) if total else 0.0,
        "clip_runs": clip_runs,
        "chart": chart,
    }
    result.update(score(result))
    return result


def _note(code, **args):
    return {"code": code, "args": args}


def score(r):
    """Turn measurements into 0-100, split across four things a file can get
    wrong. Weights are documented in docs/scoring.md."""
    parts = []

    # Bandwidth - 60. The only component that can detect a lossy source.
    bandwidth = r["bandwidth"]
    points = _interpolate(bandwidth, [
        (13000, 4), (15000, 10), (16000, 16), (17000, 24),
        (18000, 30), (19000, 38), (20000, 48), (20800, 60), (24000, 60)])
    if r["has_step"]:
        points -= 6
    points = max(0.0, min(60.0, points))
    if r["has_wall"]:
        note = _note("bw.wall", f=round(r["wall_hz"] / 1000.0, 1))
    elif r["has_step"]:
        note = _note("bw.step", f=round(r["wall_hz"] / 1000.0, 1))
    else:
        note = _note("bw.clean", f=round(bandwidth / 1000.0, 1))
    parts.append(("part.bandwidth", points, 60, note))

    # Bit depth - 15. 16 honest bits is transparent; there is no bonus for
    # 24, only a penalty for claiming it without carrying it.
    declared, effective = r["declared_bits"], r["effective_bits"]
    if declared >= 24 and effective <= 16:
        parts.append(("part.bits", 8.0, 15,
                      _note("bits.padded", declared=declared, eff=effective)))
    elif effective >= 16:
        parts.append(("part.bits", 15.0, 15, _note("bits.ok", eff=effective)))
    elif effective >= 14:
        parts.append(("part.bits", 10.0, 15, _note("bits.low", eff=effective)))
    else:
        parts.append(("part.bits", 5.0, 15,
                      _note("bits.verylow", eff=effective)))

    # Sample rate - 10.
    rate = r["rate"]
    if rate > 50000 and r["has_wall"] and r["wall_hz"] < 22500:
        parts.append(("part.rate", 6.0, 10,
                      _note("rate.upsampled", sr=rate,
                            f=round(r["wall_hz"] / 1000.0, 1))))
    elif rate >= 44100:
        parts.append(("part.rate", 10.0, 10, _note("rate.ok", sr=rate)))
    elif rate >= 32000:
        parts.append(("part.rate", 6.0, 10, _note("rate.low", sr=rate)))
    else:
        parts.append(("part.rate", 3.0, 10, _note("rate.verylow", sr=rate)))

    # Headroom - 15.
    ratio = r["clip_ratio"]
    for limit, pts, code in ((0.0, 15.0, "clip.none"),
                             (1e-5, 14.0, "clip.few"),
                             (1e-4, 12.0, "clip.tiny"),
                             (1e-3, 9.0, "clip.some"),
                             (1e-2, 6.0, "clip.lots")):
        if ratio <= limit:
            break
    else:
        pts, code = 3.0, "clip.severe"
    suffix = None
    if r["clip_runs"] > 0 and pts > 6:
        pts -= 2
        suffix = r["clip_runs"]
    note = _note(code)
    if suffix:
        note["suffix"] = {"code": "clip.runs", "args": {"n": suffix}}
    parts.append(("part.headroom", pts, 15, note))

    total = sum(p[1] for p in parts)

    # A proven lossy origin is disqualifying, not one factor among four.
    # Without this cap a fake FLAC coasts to ~87 on bit depth and headroom.
    proven_lossy = r["has_wall"] and r["wall_hz"] < LOSSY_CEILING_HZ
    if proven_lossy:
        total = min(total, _interpolate(r["wall_hz"], [
            (13000, 8), (15000, 18), (16000, 25), (17500, 34),
            (19000, 45), (20000, 52), (20700, 58)]))
    elif r["has_step"]:
        total = min(total, 78.0)

    total = max(0, min(100, int(round(total))))

    if total >= 90:
        grade = "grade.excellent"
    elif total >= 75:
        grade = "grade.good"
    elif total >= 55:
        grade = "grade.suspect"
    else:
        grade = "grade.poor"

    if proven_lossy:
        tag = "tag.from_lossy"
    elif r["has_step"]:
        tag = "tag.anomaly"
    elif total >= 90:
        tag = "tag.clean"
    elif total >= 75:
        tag = "tag.minor"
    else:
        tag = "tag.low"

    return {
        "total": total, "grade": grade, "tag": tag,
        "proven_lossy": proven_lossy,
        "parts": [{"key": k, "got": round(g, 1), "max": m, "note": n}
                  for k, g, m, n in parts],
    }


def localise(result, lang):
    """Replace every message code with text, for callers that just want
    strings (the command line, mostly)."""
    from . import i18n
    out = dict(result)
    if "error" in out:
        out["error_text"] = i18n.t(lang, out["error"])
        return out
    out["grade_text"] = i18n.t(lang, out["grade"])
    out["tag_text"] = i18n.t(lang, out["tag"])
    parts = []
    for p in out["parts"]:
        note = p["note"]
        text = i18n.t(lang, note["code"], **note.get("args", {}))
        if "suffix" in note:
            s = note["suffix"]
            text += i18n.t(lang, s["code"], **s.get("args", {}))
        q = dict(p)
        q["name"] = i18n.t(lang, p["key"])
        q["note_text"] = text
        parts.append(q)
    out["parts"] = parts
    return out


def collect(paths):
    """Expand files and folders into a sorted list of audio files."""
    found = []
    for item in paths:
        item = os.path.expanduser(str(item))
        if os.path.isdir(item):
            for root, _, files in os.walk(item):
                for f in sorted(files):
                    if f.lower().endswith(EXTENSIONS):
                        found.append(os.path.join(root, f))
        elif os.path.isfile(item):
            found.append(item)
    return found
