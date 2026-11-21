"""加算合成による小さなシンセサイザ。

和音を倍音付きの正弦波で鳴らし、ADSRに近い柔らかいエンベロープをかけ、
標準ライブラリだけで 16bit PCM の WAV を書き出す。
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from .theory import Progression, midi_to_freq

SAMPLE_RATE = 44100


def _envelope(t: float, duration: float) -> float:
    attack = min(0.08, duration * 0.2)
    release = min(0.35, duration * 0.4)
    if t < attack:
        return t / attack
    if t > duration - release:
        return max(0.0, (duration - t) / release)
    return 1.0


def _tone(freq: float, t: float) -> float:
    # 基音 + 弱い倍音で、少しだけ「声」に寄せる
    return (
        math.sin(2 * math.pi * freq * t)
        + 0.35 * math.sin(2 * math.pi * freq * 2 * t)
        + 0.12 * math.sin(2 * math.pi * freq * 3 * t)
    ) / 1.47


BASS_HOLD = 1.25  # ベースは和音の長さの 1.25 倍鳴らして、次の和音の頭まで残す
BASS_LEVEL = 0.9


def render_samples(progression: Progression, seconds_per_chord: float = 1.6) -> list[float]:
    frames_per_chord = int(SAMPLE_RATE * seconds_per_chord)
    bass_seconds = seconds_per_chord * BASS_HOLD if progression.bass else 0.0
    bass_frames = int(SAMPLE_RATE * bass_seconds)
    total = frames_per_chord * len(progression.chords) + max(0, bass_frames - frames_per_chord)
    samples = [0.0] * total
    for index, chord in enumerate(progression.chords):
        start = index * frames_per_chord
        freqs = [midi_to_freq(n) for n in chord]
        for i in range(frames_per_chord):
            t = i / SAMPLE_RATE
            env = _envelope(t, seconds_per_chord)
            value = sum(_tone(f, t) for f in freqs) / len(freqs)
            samples[start + i] += value * env * 0.8 / (1 + BASS_LEVEL * bool(progression.bass))
        # 一番下の声部（根音）は少し長く残して、和音の土台にする
        if progression.bass:
            freq = midi_to_freq(progression.bass[index])
            for i in range(bass_frames):
                t = i / SAMPLE_RATE
                env = _envelope(t, bass_seconds)
                samples[start + i] += _tone(freq, t) * env * 0.8 * BASS_LEVEL / (1 + BASS_LEVEL)
    # 全体の正規化（クリッピング防止）
    peak = max((abs(s) for s in samples), default=0.0)
    if peak > 0.98:
        samples = [s * (0.98 / peak) for s in samples]
    return samples


def write_wav(samples: list[float], out_path: str | Path) -> Path:
    out = Path(out_path)
    frames = b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples
    )
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(frames)
    return out
