import tempfile
import unittest
from pathlib import Path

from pipeline import MOTION_PRESETS, PipelineError, keep_intervals, motion_filter, split_script, timeline_for, write_srt
from voice_clone import VoiceCloneError, audio_probe, voice_id_for


class PipelineUnitTests(unittest.TestCase):
    def test_split_script_preserves_content(self):
        text = "第一句话很重要。第二句话继续解释！最后给行动。"
        lines = split_script(text, max_chars=9)
        self.assertGreaterEqual(len(lines), 3)
        self.assertEqual("".join(lines), text)

    def test_keep_intervals_removes_middle_silence_with_margin(self):
        intervals = keep_intervals(10.0, [(2.0, 4.0), (7.0, 8.0)], margin=0.2)
        self.assertEqual(intervals, [(0.0, 2.2), (3.8, 7.2), (7.8, 10.0)])

    def test_timeline_covers_full_duration(self):
        timeline = timeline_for(["短句", "这是一句更长的话"], 12.5)
        self.assertEqual(timeline[0]["start"], 0)
        self.assertAlmostEqual(timeline[-1]["end"], 12.5)
        self.assertLess(timeline[0]["end"], timeline[1]["end"])

    def test_srt_written_with_valid_timecodes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.srt"
            write_srt([{"index": 1, "start": 0.0, "end": 1.25, "text": "测试字幕"}], path)
            content = path.read_text(encoding="utf-8")
            self.assertIn("00:00:00,000 --> 00:00:01,250", content)
            self.assertIn("测试字幕", content)

    def test_every_motion_skill_builds_a_filter(self):
        for preset in MOTION_PRESETS:
            value = motion_filter(preset)
            self.assertIn("scale=1080:1920", value)
        self.assertIn("zoompan", motion_filter("smart_push"))
        self.assertNotIn("zoompan", motion_filter("none"))

    def test_unknown_motion_skill_is_rejected(self):
        with self.assertRaises(PipelineError):
            motion_filter("fake-effect")

    def test_clone_voice_id_is_provider_safe(self):
        value = voice_id_for("我的 专属 音色")
        self.assertRegex(value, r"^[A-Za-z][A-Za-z0-9_-]{7,}$")

    def test_short_clone_sample_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            sample = Path(directory) / "short.wav"
            import subprocess
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                 "-i", "sine=frequency=440:duration=1", str(sample)],
                check=True,
            )
            with self.assertRaises(VoiceCloneError):
                audio_probe(sample)


if __name__ == "__main__":
    unittest.main()
