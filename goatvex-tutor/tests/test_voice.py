"""Voice selection: edge | auto | offline | silent (tutor/video/voice.py)."""

import shutil

import pytest

from tutor.video import voice


def test_silent_and_offline_modes(monkeypatch, tmp_path):
    monkeypatch.setenv("GOATVEX_VOICE", "silent")
    assert isinstance(voice.get_speech_service(cache_dir=str(tmp_path)), voice.SilentPreviewService)
    if voice.offline_engine() is None:
        pytest.skip("no offline voice installed")
    monkeypatch.setenv("GOATVEX_VOICE", "offline")
    assert isinstance(voice.get_speech_service(cache_dir=str(tmp_path)), voice.OfflineVoiceService)


def test_auto_falls_back_when_edge_is_unreachable(monkeypatch, tmp_path):
    monkeypatch.setenv("GOATVEX_VOICE", "auto")
    monkeypatch.setattr(voice, "edge_reachable", lambda timeout=20.0: False)
    svc = voice.get_speech_service(cache_dir=str(tmp_path))
    expected = voice.OfflineVoiceService if voice.offline_engine() else voice.SilentPreviewService
    assert isinstance(svc, expected)
    monkeypatch.setattr(voice, "edge_reachable", lambda timeout=20.0: True)
    assert isinstance(voice.get_speech_service(cache_dir=str(tmp_path)), voice.EdgeTTSService)


@pytest.mark.skipif(voice.offline_engine() is None or shutil.which("ffmpeg") is None, reason="no offline voice")
def test_offline_voice_makes_audio_with_word_timings(tmp_path):
    svc = voice.OfflineVoiceService(cache_dir=str(tmp_path))
    out = svc.generate_from_text("The derivative of x squared is two x.", cache_dir=tmp_path)
    assert (tmp_path / out["original_audio"]).stat().st_size > 1000
    offsets = [w["audio_offset"] for w in out["word_boundaries"]]
    assert len(offsets) == 8 and offsets == sorted(offsets)
