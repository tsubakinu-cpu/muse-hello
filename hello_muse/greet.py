"""名前を渡すと、その名前だけの「挨拶の和音」を生成する CLI。

使い方:
    python -m hello_muse.greet "GPT" --out hello-gpt.wav
    python -m hello_muse.greet "Claude" --out hello-claude.wav
    python -m hello_muse.greet "Gemini" --out hello-gemini.wav

同じ名前には必ず同じ挨拶が返る。違う名前には、違う調と違う進行が返る。
"""

from __future__ import annotations

import argparse

from .synth import render_samples, write_wav
from .theory import generate_progression


def main() -> None:
    parser = argparse.ArgumentParser(description="名前から挨拶の和音を生成する")
    parser.add_argument("name", help="挨拶する相手の名前")
    parser.add_argument("--out", default=None, help="出力 WAV パス（既定: hello-<name>.wav）")
    parser.add_argument("--bars", type=int, default=8, help="小節数（4の倍数）")
    args = parser.parse_args()

    progression = generate_progression(args.name, bars=args.bars)
    samples = render_samples(progression)
    out_path = args.out or f"hello-{args.name}.wav"
    write_wav(samples, out_path)

    print(f"こんにちは、{args.name}。Muse です。")
    print(progression.describe())
    print(f"wrote: {out_path} ({len(samples)} samples)")


if __name__ == "__main__":
    main()
