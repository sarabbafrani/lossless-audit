"""Build reference audio with a known spectrum.

A lossy encoder's fingerprint is a brick wall. We can produce that exactly
by synthesising in the frequency domain and leaving every bin above the
cutoff empty, which gives us files whose correct answer we already know -
without shipping binaries in the repository or depending on an encoder.
"""

import math
import os
import random
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from losslessaudit.engine import fft  # noqa: E402

RATE = 44100
BLOCK = 16384
BLOCKS = 5
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_fixtures")


def _ifft(spectrum):
    a = [z.conjugate() for z in spectrum]
    fft(a)
    n = len(a)
    return [(z.conjugate() / n) for z in a]


def _channel(cutoff_hz, seed):
    rnd = random.Random(seed)
    samples = []
    top = int(cutoff_hz * BLOCK / RATE)
    for _ in range(BLOCKS):
        spectrum = [0j] * BLOCK
        for k in range(1, min(top, BLOCK // 2)):
            # 1/sqrt(f) amplitude: roughly how music sits on a spectrum
            magnitude = 1.0 / math.sqrt(k * RATE / BLOCK)
            phase = rnd.uniform(0, 2 * math.pi)
            z = complex(magnitude * math.cos(phase), magnitude * math.sin(phase))
            spectrum[k] = z
            spectrum[BLOCK - k] = z.conjugate()
        samples.extend(x.real for x in _ifft(spectrum))
    return samples


def build(name, cutoff_hz, peak=0.7):
    """Write one fixture and return its path. Cached between runs."""
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, name)
    if os.path.exists(path):
        return path

    left = _channel(cutoff_hz, 1)
    right = _channel(cutoff_hz, 2)
    loudest = max(max(abs(x) for x in left), max(abs(x) for x in right))
    gain = peak * 32767 / loudest

    rnd = random.Random(99)
    frames = bytearray()
    for i in range(len(left)):
        # +-1 LSB of dither, exactly as any real 16-bit render carries. This
        # matters: it pushes the noise floor up to Nyquist in every file, so
        # a detector cannot cheat by asking "is there anything up there".
        l = max(-32768, min(32767, int(left[i] * gain) + rnd.randint(-1, 1)))
        r = max(-32768, min(32767, int(right[i] * gain) + rnd.randint(-1, 1)))
        frames += struct.pack("<hh", l, r)

    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))
    return path


def full_band():
    return build("full_band.wav", RATE / 2)


def wall_at_20k():
    return build("wall_20k.wav", 20000)


def wall_at_16k():
    return build("wall_16k.wav", 16000)


def clipped():
    return build("clipped.wav", RATE / 2, peak=1.6)


if __name__ == "__main__":
    for f in (full_band(), wall_at_20k(), wall_at_16k(), clipped()):
        print("built", f)
