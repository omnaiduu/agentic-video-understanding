from __future__ import annotations

import io
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from app.tools import ScissorsError, get_audio, get_frames, get_meta
from app.tools.caps import MAX_AUDIO_SECONDS, MAX_FRAMES


JPEG_MAGIC = b"\xff\xd8\xff"


def _safe_end(path: Path, want_s: float = 0.8) -> float:
    meta = get_meta(path)
    return min(meta.duration_s, want_s)


def test_get_meta_video(tiny_mp4: Path) -> None:
    meta = get_meta(tiny_mp4)
    assert meta.has_video is True
    assert meta.has_audio is True
    assert meta.duration_s > 0.5
    assert meta.fps is not None


def test_get_frames_short_jpegs_and_timestamps(tiny_mp4: Path) -> None:
    end = _safe_end(tiny_mp4)
    frames = get_frames(tiny_mp4, 0, end, fps=2)
    assert 1 <= len(frames) <= MAX_FRAMES
    times = [frame.t for frame in frames]
    assert times == sorted(times)
    for frame in frames:
        assert frame.jpeg.startswith(JPEG_MAGIC)
        assert 0 <= frame.t <= end + 0.05


def test_get_frames_default_fps_is_one(tiny_mp4: Path) -> None:
    from app.tools.caps import DEFAULT_SHORT_FPS, resolve_fps

    assert DEFAULT_SHORT_FPS == 1.0
    assert resolve_fps(4.0, None) == 1.0


def test_get_frames_scales_wide_frames(tiny_mp4: Path, monkeypatch) -> None:
    from app.tools import ffmpeg_cli
    from app.tools.caps import LOOK_MAX_WIDTH

    seen: list[list[str]] = []
    real = ffmpeg_cli.run_ffmpeg

    def wrap(args: list[str]) -> None:
        seen.append(list(args))
        real(args)

    monkeypatch.setattr(ffmpeg_cli, "run_ffmpeg", wrap)
    end = _safe_end(tiny_mp4, 0.5)
    frames = get_frames(tiny_mp4, 0, end, fps=1)
    assert frames
    joined = " ".join(seen[0])
    assert f"scale='if(gt(iw,{LOOK_MAX_WIDTH}),{LOOK_MAX_WIDTH},iw)':-2" in joined
    assert "-q:v" in seen[0]
    assert "5" in seen[0]


def test_get_audio_16khz_mono_wav(tiny_mp4: Path) -> None:
    end = _safe_end(tiny_mp4, 0.8)
    data = get_audio(tiny_mp4, 0, end)
    with wave.open(io.BytesIO(data), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000
        seconds = wav.getnframes() / float(wav.getframerate())
    assert 0.2 < seconds < 1.5


def test_get_audio_audio_only_file(tiny_audio: Path) -> None:
    end = _safe_end(tiny_audio, 0.8)
    data = get_audio(tiny_audio, 0, end)
    with wave.open(io.BytesIO(data), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000


def test_get_frames_audio_only_errors(tiny_audio: Path) -> None:
    end = _safe_end(tiny_audio, 0.5)
    with pytest.raises(ScissorsError, match="no video"):
        get_frames(tiny_audio, 0, end, fps=2)


def test_oversize_frames_never_calls_extract(tiny_mp4: Path, monkeypatch) -> None:
    from app.tools import ffmpeg_cli

    def boom(*_args, **_kwargs) -> None:
        raise AssertionError("extract ffmpeg must not run for an oversize request")

    monkeypatch.setattr(ffmpeg_cli, "run_ffmpeg", boom)
    with pytest.raises(ScissorsError, match="12"):
        get_frames(tiny_mp4, 0, 7200, fps=1)
    with pytest.raises(ScissorsError, match="12"):
        get_frames(tiny_mp4, 0, 70)


def test_oversize_audio_never_calls_extract(tiny_mp4: Path, monkeypatch) -> None:
    from app.tools import ffmpeg_cli

    def boom(*_args, **_kwargs) -> None:
        raise AssertionError("extract ffmpeg must not run for an oversize request")

    monkeypatch.setattr(ffmpeg_cli, "run_ffmpeg", boom)
    with pytest.raises(ScissorsError, match=f"{MAX_AUDIO_SECONDS:.0f}"):
        get_audio(tiny_mp4, 0, 31)


def test_invalid_window_refused(tiny_mp4: Path, monkeypatch) -> None:
    from app.tools import ffmpeg_cli

    monkeypatch.setattr(
        ffmpeg_cli,
        "run_ffmpeg",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no extract")),
    )
    with pytest.raises(ScissorsError, match="start"):
        get_frames(tiny_mp4, -1, 1, fps=1)
    with pytest.raises(ScissorsError, match="after start"):
        get_audio(tiny_mp4, 2, 1)


def test_window_past_duration_refused(tiny_mp4: Path) -> None:
    meta = get_meta(tiny_mp4)
    with pytest.raises(ScissorsError, match="past the end"):
        get_frames(tiny_mp4, 0, meta.duration_s + 5, fps=1)


def test_original_file_unchanged(tiny_mp4: Path) -> None:
    before = tiny_mp4.read_bytes()
    end = _safe_end(tiny_mp4, 0.5)
    get_frames(tiny_mp4, 0, end, fps=2)
    get_audio(tiny_mp4, 0, end)
    assert tiny_mp4.read_bytes() == before
    siblings = {p.name for p in tiny_mp4.parent.iterdir()}
    assert "tiny.mp4" in siblings
    assert not any(name.startswith("scissors-") for name in siblings)


def test_temp_files_deleted_after_frames(tiny_mp4: Path, monkeypatch) -> None:
    from app.tools import frames as frames_mod

    seen: list[Path] = []
    real = TemporaryDirectory

    class Tracking(real):
        def __enter__(self):
            path = super().__enter__()
            seen.append(Path(path))
            return path

    monkeypatch.setattr(frames_mod, "TemporaryDirectory", Tracking)
    end = _safe_end(tiny_mp4, 0.5)
    get_frames(tiny_mp4, 0, end, fps=2)
    assert seen
    assert not seen[0].exists()


def test_temp_files_deleted_after_audio(tiny_mp4: Path, monkeypatch) -> None:
    from app.tools import audio as audio_mod

    seen: list[Path] = []
    real = TemporaryDirectory

    class Tracking(real):
        def __enter__(self):
            path = super().__enter__()
            seen.append(Path(path))
            return path

    monkeypatch.setattr(audio_mod, "TemporaryDirectory", Tracking)
    end = _safe_end(tiny_mp4, 0.5)
    get_audio(tiny_mp4, 0, end)
    assert seen
    assert not seen[0].exists()
