import unittest
import wave

from hello_muse import generate_progression, midi_to_freq
from hello_muse.synth import render_samples, write_wav
from hello_muse.theory import MODES


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
        prog = generate_progression("Tsubaki", bars=8)
        movements = [
            sum(abs(a - b) for a, b in zip(sorted(prev), sorted(cur)))
            for prev, cur in zip(prog.chords, prog.chords[1:])
        ]
        # 声部連結が効いていれば、1和音あたりの総移動は控えめになる
        self.assertTrue(all(m <= 12 for m in movements), movements)

    def test_bars_must_be_multiple_of_four(self):
        with self.assertRaises(ValueError):
            generate_progression("Muse", bars=6)


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
