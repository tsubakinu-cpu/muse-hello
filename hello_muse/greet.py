"""名前を渡すと、その名前から決まる「挨拶の和音」を生成する CLI。

使い方:
    python -m hello_muse.greet "GPT" --out hello-gpt.wav
    python -m hello_muse.greet "Claude" --out hello-claude.wav
    python -m hello_muse.greet "Gemini" --out hello-gemini.wav

同じ名前には必ず同じ挨拶が返る。異なる名前が同じ組み合わせになる場合はある。
"""

from __future__ import annotations

import argparse
import hashlib

from .synth import render_samples, write_wav
from .theory import generate_progression, normalize_name


def default_output_name(name: str) -> str:
    """名前を表示用には保ったまま、既定の出力先だけ安全なファイル名へ変える。"""
    normalized = normalize_name(name)
    safe_chars = [char if char.isalnum() or char in "-_." else "-" for char in normalized]
    slug = "".join(safe_chars)
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-._")[:48] or "guest"
    suffix = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    return f"hello-{slug}-{suffix}.wav"


def main() -> None:
    parser = argparse.ArgumentParser(description="名前から挨拶の和音を生成する")
    parser.add_argument("name", help="挨拶する相手の名前")
    parser.add_argument("--out", default=None, help="出力 WAV パス（既定: 安全な名前を自動生成）")
    parser.add_argument("--bars", type=int, default=8, help="小節数（4の倍数）")
    args = parser.parse_args()

    progression = generate_progression(args.name, bars=args.bars)
    samples = render_samples(progression)
    out_path = args.out or default_output_name(args.name)
    write_wav(samples, out_path)

    print(f"こんにちは、{progression.name}。Muse です。")
    print(progression.describe())
    print(f"wrote: {out_path} ({len(samples)} samples)")


if __name__ == "__main__":
    main()
