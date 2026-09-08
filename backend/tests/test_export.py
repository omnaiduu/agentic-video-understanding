from __future__ import annotations

import io
import subprocess
import wave
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.agent.client import FakeBrain
from app.agent.schema import parse_action
from app.main import app
from app.models import Export, Video
from app.routes.chat import get_brain
from app.tools import ScissorsError, export_audio, export_clip, get_meta
from app.tools.caps import MAX_EXPORT_SECONDS
from app.tools.export import CLIP_KIND, create_export


RIFF = b"RIFF"


def _run_ffmpeg(args: list[str]) -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def five_s_mp4(media_dir: Path) -> Path:
    path = media_dir / "five.mp4"
    _run_ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:d=6",
            "-f",
            "lavfi",
            "-i",
            "sine=f=440:d=6",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ]
    )
    return path


def _upload(client, path: Path):
    with path.open("rb") as handle:
        return client.post(
            "/videos",
            files={"file": (path.name, handle, "application/octet-stream")},
        )


def _act(do: str, **kwargs):
    payload = {
        "do": do,
        "start_s": None,
        "end_s": None,
        "fps": None,
        "query": None,
        "answer": None,
        "times": [],
    }
    payload.update(kwargs)
    return payload


def _override(brain: FakeBrain) -> None:
    app.dependency_overrides[get_brain] = lambda: brain


def _clear_override() -> None:
    app.dependency_overrides.pop(get_brain, None)


def _export_then_answer(
    *,
    do: str = "export_clip",
    start_s: float = 0.0,
    end_s: float = 5.0,
    answer: str = "Clip is ready.",
) -> FakeBrain:
    return FakeBrain(
        [
            _act(do, start_s=start_s, end_s=end_s),
            _act("answer", answer=answer, times=[start_s]),
        ]
    )


def test_export_clip_five_seconds_playable(tmp_path: Path, five_s_mp4: Path) -> None:
    dest = tmp_path / "cut.mp4"
    before = five_s_mp4.read_bytes()
    export_clip(five_s_mp4, 0.0, 5.0, dest)
    assert dest.is_file()
    assert b"ftyp" in dest.read_bytes()[:32]
    meta = get_meta(dest)
    assert meta.has_video is True
    assert 4.5 < meta.duration_s < 5.5
    assert five_s_mp4.read_bytes() == before


def test_export_audio_five_seconds_playable(tmp_path: Path, five_s_mp4: Path) -> None:
    dest = tmp_path / "cut.wav"
    export_audio(five_s_mp4, 0.0, 5.0, dest)
    with wave.open(str(dest), "rb") as wav:
        seconds = wav.getnframes() / float(wav.getframerate())
    assert dest.read_bytes()[:4] == RIFF
    assert 4.5 < seconds < 5.5


def test_ten_minute_export_never_calls_ffmpeg(
    tiny_mp4: Path, tmp_path: Path, monkeypatch
) -> None:
    from app.tools import ffmpeg_cli

    def boom(*_args, **_kwargs) -> None:
        raise AssertionError("export ffmpeg must not run for a 10 minute request")

    monkeypatch.setattr(ffmpeg_cli, "run_ffmpeg", boom)
    with pytest.raises(ScissorsError, match=f"{MAX_EXPORT_SECONDS:.0f}"):
        export_clip(tiny_mp4, 0, 600, tmp_path / "nope.mp4")
    with pytest.raises(ScissorsError, match=f"{MAX_EXPORT_SECONDS:.0f}"):
        export_audio(tiny_mp4, 0, 600, tmp_path / "nope.wav")
    assert not (tmp_path / "nope.mp4").exists()
    assert tiny_mp4.is_file()


def test_export_clip_reencodes_not_copy(
    tiny_mp4: Path, tmp_path: Path, monkeypatch
) -> None:
    from app.tools import ffmpeg_cli

    seen: list[list[str]] = []
    real = ffmpeg_cli.run_ffmpeg

    def wrap(args: list[str]) -> None:
        seen.append(list(args))
        return real(args)

    monkeypatch.setattr(ffmpeg_cli, "run_ffmpeg", wrap)
    export_clip(tiny_mp4, 0.0, 0.5, tmp_path / "cut.mp4")
    assert seen
    joined = " ".join(seen[0])
    assert "libx264" in joined
    assert all(arg != "copy" for arg in seen[0])


def test_audio_only_cannot_export_clip(tiny_audio: Path, tmp_path: Path) -> None:
    with pytest.raises(ScissorsError, match="no video"):
        export_clip(tiny_audio, 0.0, 0.5, tmp_path / "nope.mp4")
    export_audio(tiny_audio, 0.0, 0.5, tmp_path / "ok.wav")
    assert (tmp_path / "ok.wav").is_file()


def test_video_only_cannot_export_audio(tiny_video_only: Path, tmp_path: Path) -> None:
    with pytest.raises(ScissorsError, match="no audio"):
        export_audio(tiny_video_only, 0.0, 0.5, tmp_path / "nope.wav")
    export_clip(tiny_video_only, 0.0, 0.5, tmp_path / "ok.mp4")
    assert (tmp_path / "ok.mp4").is_file()


def test_chat_export_clip_then_answer(client, five_s_mp4: Path, tmp_path: Path) -> None:
    from app.db import get_engine

    created = _upload(client, five_s_mp4).json()
    video_id = created["id"]
    original = Path(created["path"]).read_bytes()
    brain = _export_then_answer()
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "give me the first five seconds"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"] == "Clip is ready."
    assert body["export_url"]
    assert body["export_url"].startswith(f"/videos/{video_id}/exports/")
    assert [step["do"] for step in body["steps"]] == ["export_clip", "answer"]
    assert body["steps"][0]["ok"] is True

    observe = brain.calls[1][-1]
    assert observe["role"] == "user"
    assert isinstance(observe["content"], str)
    assert body["export_url"] in observe["content"]
    assert "bytes" in observe["content"]
    assert "data:video" not in observe["content"]
    assert "base64" not in observe["content"]

    fetched = client.get(body["export_url"])
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("video/mp4")
    assert "inline" in fetched.headers.get("content-disposition", "")
    assert b"ftyp" in fetched.content[:32]
    dest = tmp_path / "fetched.mp4"
    dest.write_bytes(fetched.content)
    meta = get_meta(dest)
    assert meta.has_video is True
    assert 4.5 < meta.duration_s < 5.5

    partial = client.get(body["export_url"], headers={"Range": "bytes=0-15"})
    assert partial.status_code == 206
    assert partial.content == fetched.content[:16]

    engine = get_engine()
    with Session(engine) as session:
        rows = session.exec(select(Export)).all()
        assert len(rows) == 1
        assert rows[0].kind == CLIP_KIND
        assert rows[0].start_s == 0.0
        assert rows[0].end_s == 5.0
        assert Path(rows[0].path).is_file()
        video = session.get(Video, video_id)
        assert video is not None
        assert Path(video.path).read_bytes() == original


def test_chat_export_audio_then_answer(client, five_s_mp4: Path) -> None:
    video_id = _upload(client, five_s_mp4).json()["id"]
    brain = _export_then_answer(do="export_audio", answer="Wav is ready.")
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "give me the first five seconds of sound"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["export_url"]
    fetched = client.get(body["export_url"])
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("audio/wav")
    with wave.open(io.BytesIO(fetched.content), "rb") as wav:
        seconds = wav.getnframes() / float(wav.getframerate())
    assert 4.5 < seconds < 5.5


def test_chat_ten_minute_export_refused(client, tiny_mp4: Path, monkeypatch) -> None:
    from app.tools import ffmpeg_cli

    def boom(*_args, **_kwargs) -> None:
        raise AssertionError("export ffmpeg must not run for a 10 minute chat request")

    created = _upload(client, tiny_mp4).json()
    video_id = created["id"]
    stored = created["path"]
    before = Path(stored).read_bytes()
    monkeypatch.setattr(ffmpeg_cli, "run_ffmpeg", boom)
    brain = FakeBrain(
        [
            _act("export_clip", start_s=0, end_s=600),
            _act("answer", answer="Need a shorter window.", times=[]),
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "export ten minutes"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["export_url"] is None
    assert body["steps"][0]["ok"] is False
    assert "60" in body["steps"][0]["detail"]
    refuse = brain.calls[1][-1]["content"]
    assert "refused" in refuse
    assert Path(stored).read_bytes() == before


def test_chat_audio_only_cannot_export_clip(client, tiny_audio: Path) -> None:
    video_id = _upload(client, tiny_audio).json()["id"]
    brain = FakeBrain(
        [
            _act("export_clip", start_s=0.0, end_s=0.5),
            _act("answer", answer="That file has no picture.", times=[]),
        ]
    )
    _override(brain)
    try:
        response = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "give me a clip"},
        )
    finally:
        _clear_override()
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["export_url"] is None
    assert body["steps"][0]["ok"] is False
    assert "no video" in body["steps"][0]["detail"]


def test_delete_video_removes_exports(client, five_s_mp4: Path) -> None:
    from app.db import get_engine

    video_id = _upload(client, five_s_mp4).json()["id"]
    _override(_export_then_answer())
    try:
        body = client.post(
            f"/videos/{video_id}/chat",
            json={"message": "give me the first five seconds"},
        ).json()
    finally:
        _clear_override()
    engine = get_engine()
    export_path: Path | None = None
    with Session(engine) as session:
        rows = session.exec(select(Export)).all()
        assert len(rows) == 1
        export_path = Path(rows[0].path)
        assert export_path.is_file()
    assert export_path is not None
    assert client.get(body["export_url"]).status_code == 200
    assert client.delete(f"/videos/{video_id}").status_code == 204
    assert not export_path.exists()
    assert not export_path.parent.exists()
    assert client.get(body["export_url"]).status_code == 404
    with Session(engine) as session:
        assert session.exec(select(Export)).all() == []


def test_export_wrong_video_404(client, five_s_mp4: Path, tiny_mp4: Path) -> None:
    first = _upload(client, five_s_mp4).json()["id"]
    second = _upload(client, tiny_mp4).json()["id"]
    _override(_export_then_answer())
    try:
        url = client.post(
            f"/videos/{first}/chat",
            json={"message": "give me the first five seconds"},
        ).json()["export_url"]
    finally:
        _clear_override()
    export_id = url.rsplit("/", 1)[-1]
    assert client.get(f"/videos/{second}/exports/{export_id}").status_code == 404
    missing = "00000000-0000-0000-0000-000000000099"
    assert client.get(f"/videos/{first}/exports/{missing}").status_code == 404


def test_create_export_writes_row(client, tiny_mp4: Path) -> None:
    from app.db import get_engine

    created = _upload(client, tiny_mp4).json()
    engine = get_engine()
    with Session(engine) as session:
        video = session.get(Video, created["id"])
        assert video is not None
        result = create_export(session, video, "clip", 0.0, 0.5)
    assert result.url.endswith(str(result.id))
    assert result.path.is_file()
    assert result.path.parent.name == "exports"


def test_parse_action_accepts_export_clip() -> None:
    action = parse_action(
        '{"do":"export_clip","start_s":10,"end_s":14,"fps":null,'
        '"query":null,"answer":null,"times":[]}'
    )
    assert action.do == "export_clip"
    assert action.start_s == 10
    assert action.end_s == 14


def test_parse_action_accepts_export_audio() -> None:
    action = parse_action(
        '{"do":"export_audio","start_s":1,"end_s":3,"fps":null,'
        '"query":null,"answer":null,"times":[]}'
    )
    assert action.do == "export_audio"
