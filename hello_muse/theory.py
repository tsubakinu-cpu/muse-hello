"""挨拶のための音楽理論コア。

名前から決定的に（同じ名前なら必ず同じ結果で）調とコード進行を導く。
外部ライブラリには頼らず、音階・三和音・声部連結だけを素直に実装する。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

# 長音階を基準にしたモード（教会旋法）のインターバル
MODES: dict[str, tuple[int, ...]] = {
    "ionian": (0, 2, 4, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "aeolian": (0, 2, 3, 5, 7, 8, 10),
}

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# 挨拶らしく、開いて、少し影が差して、また開いて帰ってくる進行の型
PROGRESSION_SHAPES: tuple[tuple[int, ...], ...] = (
    (0, 4, 5, 3),  # I - V - vi - IV
    (0, 5, 3, 4),  # I - vi - IV - V
    (0, 3, 4, 5),  # I - IV - V - vi
    (0, 5, 1, 4),  # I - vi - ii - V
)


def midi_to_freq(midi: float) -> float:
    """MIDIノート番号を周波数(Hz)に変換する。A4 = 69 = 440Hz。"""
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def note_name(midi: int) -> str:
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


@dataclass(frozen=True)
class Progression:
    name: str
    root_midi: int
    mode: str
    chords: tuple[tuple[int, int, int], ...]  # 声部連結済みの三和音 (MIDI x3)

    def describe(self) -> str:
        chords = " -> ".join(
            "/".join(note_name(n) for n in chord) for chord in self.chords
        )
        return (
            f"{self.name}: root={note_name(self.root_midi)} mode={self.mode}\n"
            f"progression: {chords}"
        )


def _seed_int(name: str) -> int:
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _triad(root_midi: int, mode: str, degree: int, base_octave_midi: int) -> tuple[int, int, int]:
    """音階上の degree (0始まり) を根音とする三和音を、基準音域で返す。"""
    intervals = MODES[mode]
    scale = [root_midi + intervals[i % 7] + 12 * (i // 7) for i in range(21)]
    tones = (scale[degree], scale[degree + 2], scale[degree + 4])
    # 基準音域 (C3=48 あたり) に寄せる
    shift = round((base_octave_midi - tones[0]) / 12) * 12
    return tuple(t + shift for t in tones)


def _voice_lead(previous: tuple[int, int, int], target: tuple[int, int, int]) -> tuple[int, int, int]:
    """三和音の各転回形とオクターブ移動の中から、前の和音からの
    総移動量が最小になる配置を選ぶ（古典的な声部連結の簡略版）。"""
    tones = sorted(target)
    candidates: list[tuple[int, int, int]] = []
    for rotation in range(3):
        rotated = tones[rotation:] + [t + 12 for t in tones[:rotation]]
        for octave_shift in (-12, 0, 12):
            candidates.append(tuple(t + octave_shift for t in rotated))
    def cost(cand: tuple[int, int, int]) -> int:
        return sum(abs(a - b) for a, b in zip(sorted(cand), sorted(previous)))
    return min(candidates, key=cost)


def generate_progression(name: str, bars: int = 8) -> Progression:
    """名前から調・モード・コード進行を決定的に生成する。

    bars は 4 の倍数で、進行の型を繰り返す。
    """
    if bars % 4 != 0:
        raise ValueError("bars must be a multiple of 4")
    seed = _seed_int(name)
    mode = list(MODES)[seed % len(MODES)]
    root_midi = 48 + (seed >> 8) % 12  # C3..B3
    shape = PROGRESSION_SHAPES[(seed >> 16) % len(PROGRESSION_SHAPES)]

    degrees = [shape[i % 4] for i in range(bars)]
    chords: list[tuple[int, int, int]] = []
    previous: tuple[int, int, int] | None = None
    for degree in degrees:
        triad = _triad(root_midi, mode, degree, base_octave_midi=60)
        if previous is not None:
            triad = _voice_lead(previous, triad)
        chords.append(triad)
        previous = triad
    return Progression(name=name, root_midi=root_midi, mode=mode, chords=tuple(chords))
