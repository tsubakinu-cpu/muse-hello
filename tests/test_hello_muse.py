import unittest
import wave

from hello_muse import generate_progression, midi_to_freq
from hello_muse.synth import render_samples, write_wav
from hello_muse.theory import (
    BASS_LOW,
    CADENCE_DEGREE,
    MODES,
    VOICE_LOW,
    _movement,
    _triad_pcs,
    _voicings,
)

NAMES = ("GPT", "Claude", "Gemini", "Muse", "Tsubaki", "椿", "聖司", "Seiji")


class TheoryTests(unittest.TestCase):
    def test_a4_is_440hz(self):
        self.assertAlmostEqual(midi_to_freq(69), 440.0)

    def test_deterministic_for_same_name(self):
        self.assertEqual(generate_progression("Claude"), generate_progression("Claude"))

    def test_different_names_usually_differ(self):
        self.assertNotEqual(generate_progression("GPT"), generate_progression("Gemini"))

    def test_all_notes_stay_in_mode(self):
        for name in ("GPT", "Claude", "Gemini", "Muse"):
            prog = generate_progression(name)
            allowed = {
                (prog.root_midi + step) % 12 for step in MODES[prog.mode]
            }
            for chord in prog.chords:
                for note in chord:
                    self.assertIn(note % 12, allowed)

    def test_voice_leading_moves_less_than_naive(self):
        for name in NAMES:
            prog = generate_progression(name, bars=8)
            led = sum(_movement(a, b) for a, b in zip(prog.chords, prog.chords[1:]))
            # 比較対象: 全部を基本形のまま窓に置いた場合
            naive = [
                _voicings(_triad_pcs(prog.root_midi, prog.mode, d))[0] for d in prog.degrees
            ]
            naive_total = sum(_movement(a, b) for a, b in zip(naive, naive[1:]))
            self.assertLessEqual(led, naive_total, name)

    def test_register_does_not_drift(self):
        for name in NAMES:
            prog = generate_progression(name, bars=64)
            for chord in prog.chords:
                self.assertTrue(VOICE_LOW <= min(chord) < VOICE_LOW + 12, (name, chord))
                self.assertLess(max(chord) - min(chord), 12, (name, chord))
            for note in prog.bass:
                self.assertTrue(BASS_LOW <= note < BASS_LOW + 12, (name, note))

    def test_ends_on_tonic_after_cadence(self):
        for name in NAMES:
            for bars in (4, 8, 16):
                prog = generate_progression(name, bars=bars)
                tonic = set(_triad_pcs(prog.root_midi, prog.mode, 0))
                self.assertEqual({n % 12 for n in prog.chords[-1]}, tonic, name)
                self.assertEqual(prog.bass[-1] % 12, prog.root_midi % 12, name)
                self.assertEqual(prog.degrees[-2], CADENCE_DEGREE[prog.mode], name)
                self.assertNotEqual(prog.degrees[-3], prog.degrees[-2], name)

    def test_cadence_chords_are_major(self):
        for mode, degree in CADENCE_DEGREE.items():
            root, third, fifth = _triad_pcs(60, mode, degree)
            self.assertEqual(((third - root) % 12, (fifth - root) % 12), (4, 7), mode)

    def test_bass_is_chord_root(self):
        for name in NAMES:
            prog = generate_progression(name)
            for degree, chord, bass in zip(prog.degrees, prog.chords, prog.bass):
                root = _triad_pcs(prog.root_midi, prog.mode, degree)[0]
                self.assertEqual(bass % 12, root)
                self.assertIn(root, {n % 12 for n in chord})

    def test_bars_must_be_multiple_of_four(self):
        with self.assertRaises(ValueError):
            generate_progression("Muse", bars=6)
        with self.assertRaises(ValueError):
            generate_progression("Muse", bars=0)


class SynthTests(unittest.TestCase):
    def test_wav_is_written_and_readable(self):
        prog = generate_progression("Muse", bars=4)
        samples = render_samples(prog, seconds_per_chord=0.2)
        out = write_wav(samples, "/tmp/test-hello.wav")
        with wave.open(str(out), "rb") as wf:
            self.assertEqual(wf.getframerate(), 44100)
            self.assertGreater(wf.getnframes(), 0)

    def test_samples_do_not_clip(self):
        prog = generate_progression("GPT", bars=4)
        samples = render_samples(prog, seconds_per_chord=0.2)
        self.assertLessEqual(max(abs(s) for s in samples), 0.99)


if __name__ == "__main__":
    unittest.main()
