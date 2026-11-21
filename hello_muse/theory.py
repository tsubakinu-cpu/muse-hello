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

# 進行の型。数字は音階上の度数（0始まり）。
# コメントの和音記号は長音階（ionian）で読んだ場合のもので、
# ほかの旋法では同じ度数でも和音の性格が変わる（例: phrygian の 4 は減三和音）。
PROGRESSION_SHAPES: tuple[tuple[int, ...], ...] = (
    (0, 4, 5, 3),  # I - V - vi - IV
    (0, 5, 3, 4),  # I - vi - IV - V
    (0, 3, 4, 5),  # I - IV - V - vi
    (0, 5, 1, 4),  # I - vi - ii - V
)

# 旋法ごとの終止の和音（主和音の直前に置く度数）。どれも長三和音。
# aeolian の bVII には特性音（b6）が入らないので、直前に bVI を置く（PRE_CADENCE）。
CADENCE_DEGREE: dict[str, int] = {
    "ionian": 4,  # V    -> I
    "dorian": 3,  # IV   -> i
    "phrygian": 1,  # bII  -> i
    "lydian": 1,  # II   -> I
    "mixolydian": 6,  # bVII -> I
    "aeolian": 6,  # bVII -> i
}

# 終止の和音の直前に置く和音（旋法の特性音を終止形に入れるため）
PRE_CADENCE: dict[str, int] = {
    "aeolian": 5,  # bVI -> bVII -> i
}

# 旋法の特性音（主音からの半音数）。終止形のどこかに必ず入る。
CHARACTERISTIC: dict[str, int] = {
    "ionian": 11,  # 導音（mixolydian との違い）
    "dorian": 9,  # 長6度
    "phrygian": 1,  # 短2度
    "lydian": 6,  # 増4度
    "mixolydian": 10,  # 短7度
    "aeolian": 8,  # 短6度
}

# 上三声の最低音を置く窓（G3..F#4）。繰り返しても音域がずれていかないようにする。
VOICE_LOW = 55
# ベース（根音）を置く窓（E2..D#3）。
BASS_LOW = 40


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
    bass: tuple[int, ...] = ()  # 各和音の根音（低音域）
    degrees: tuple[int, ...] = ()  # 各和音の度数

    def describe(self) -> str:
        chords = " -> ".join(
            "/".join(note_name(n) for n in chord) for chord in self.chords
        )
        lines = [
            f"{self.name}: root={note_name(self.root_midi)} mode={self.mode}",
            f"progression: {chords}",
        ]
        if self.bass:
            lines.append("bass: " + " -> ".join(note_name(n) for n in self.bass))
        return "\n".join(lines)


def _seed_int(name: str) -> int:
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _degree_pc(root_midi: int, mode: str, degree: int) -> int:
    """度数の根音のピッチクラス (0..11)。"""
    return (root_midi + MODES[mode][degree % 7]) % 12


def _triad_pcs(root_midi: int, mode: str, degree: int) -> tuple[int, int, int]:
    """度数を根音とする三和音のピッチクラスを、根音・3度・5度の順で返す。"""
    return tuple(_degree_pc(root_midi, mode, degree + k) for k in (0, 2, 4))


def _voicings(pcs: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    """最低音が窓 [VOICE_LOW, VOICE_LOW+11] に入る密集配置を、
    基本形・第1転回形・第2転回形の順で返す。"""
    result: list[tuple[int, int, int]] = []
    for rotation in range(3):
        order = pcs[rotation:] + pcs[:rotation]
        low = VOICE_LOW + (order[0] - VOICE_LOW) % 12
        notes = [low]
        for pc in order[1:]:
            notes.append(notes[-1] + (pc - notes[-1]) % 12)
        result.append(tuple(notes))
    return result


def _movement(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum(abs(x - y) for x, y in zip(sorted(a), sorted(b)))


def _voice_lead(previous: tuple[int, int, int], pcs: tuple[int, int, int]) -> tuple[int, int, int]:
    """窓の中の転回形から、前の和音からの総移動量が最小になる配置を選ぶ。
    候補を窓の中に限るので、進行を何周しても音域が上下にずれていかない。"""
    return min(_voicings(pcs), key=lambda cand: _movement(previous, cand))


def _bass_note(pc: int) -> int:
    return BASS_LOW + (pc - BASS_LOW) % 12


def _degrees(shape: tuple[int, ...], mode: str, bars: int) -> list[int]:
    """型を繰り返し、最後の4小節だけ終止形にして主和音で終える。"""
    degrees = [shape[i % 4] for i in range(bars)]
    cadence = CADENCE_DEGREE[mode]
    if mode in PRE_CADENCE:
        middle = PRE_CADENCE[mode]
    else:
        # 終止の和音が直前で重ならないように、型の2つ目と同じなら3つ目を使う
        middle = shape[1] if shape[1] != cadence else shape[2]
    degrees[-4:] = [shape[0], middle, cadence, 0]
    return degrees


def generate_progression(name: str, bars: int = 8) -> Progression:
    """名前から調・モード・コード進行を決定的に生成する。

    bars は 4 の倍数で、進行の型を繰り返す。最後の4小節は終止形で、
    旋法ごとの終止の和音から主和音へ帰って終わる。
    """
    if bars % 4 != 0 or bars <= 0:
        raise ValueError("bars must be a positive multiple of 4")
    seed = _seed_int(name)
    mode = list(MODES)[seed % len(MODES)]
    root_midi = 48 + (seed >> 8) % 12  # C3..B3
    shape = PROGRESSION_SHAPES[(seed >> 16) % len(PROGRESSION_SHAPES)]

    degrees = _degrees(shape, mode, bars)
    chords: list[tuple[int, int, int]] = []
    previous: tuple[int, int, int] | None = None
    for degree in degrees:
        pcs = _triad_pcs(root_midi, mode, degree)
        if previous is None:
            triad = _voicings(pcs)[0]  # 最初の主和音は基本形で始める
        else:
            triad = _voice_lead(previous, pcs)
        chords.append(triad)
        previous = triad
    bass = tuple(_bass_note(_degree_pc(root_midi, mode, d)) for d in degrees)
    return Progression(
        name=name,
        root_midi=root_midi,
        mode=mode,
        chords=tuple(chords),
        bass=bass,
        degrees=tuple(degrees),
    )
