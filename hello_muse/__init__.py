"""hello_muse — 名前から挨拶の和音を生成する小さなパッケージ。"""

from .theory import Progression, generate_progression, midi_to_freq

__all__ = ["Progression", "generate_progression", "midi_to_freq"]
