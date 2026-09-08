from __future__ import annotations

from pathlib import Path

from app.settings import get_settings


def _upload(client, path: Path, name: str | None = None):
    filename = name or path.name
    with path.open("rb") as handle:
        return client.post(
            "/videos",
            files={"file": (filename, handle, "application/octet-stream")},
        )


def test_upload_mp4_ready_with_duration(client, tiny_mp4: Path) -> None:
    response = _upload(client, tiny_mp4)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["kind"] == "video"
    assert body["has_video"] is True
    assert body["has_audio"] is True
    assert body["duration_s"] is not None
    assert 0.5 < body["duration_s"] < 2.5
    assert body["fps"] is not None
    assert Path(body["path"]).is_file()
    assert not Path(body["path"]).is_symlink()
    assert body["path"].endswith("/original.mp4")


def test_path_register_copies_file(client, tiny_mp4: Path) -> None:
    response = client.post("/videos", json={"path": str(tiny_mp4)})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["kind"] == "video"
    assert body["original_filename"] == "tiny.mp4"
    stored = Path(body["path"])
    assert stored.is_file()
    assert stored.resolve() != tiny_mp4.resolve()
    assert stored.read_bytes() == tiny_mp4.read_bytes()


def test_audio_kind(client, tiny_audio: Path) -> None:
    response = _upload(client, tiny_audio)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["kind"] == "audio"
    assert body["has_video"] is False
    assert body["has_audio"] is True
    assert body["fps"] is None
    assert body["duration_s"] is not None


def test_garbage_becomes_error(client) -> None:
    response = client.post(
        "/videos",
        files={"file": ("junk.mp4", b"this is not a media file" * 32, "video/mp4")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "error"
    assert body["error_message"]
    assert "Copyright" not in body["error_message"]
    assert "configuration:" not in body["error_message"]


def test_oversize_rejected(client, tiny_mp4: Path, monkeypatch, data_dir: Path) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_bytes", 32)
    response = _upload(client, tiny_mp4)
    assert response.status_code == 413
    videos_root = data_dir / "videos"
    leftovers = list(videos_root.rglob("*")) if videos_root.exists() else []
    assert leftovers == []
    listed = client.get("/videos")
    assert listed.status_code == 200
    assert listed.json() == []


def test_get_file_bytes_and_range(client, tiny_mp4: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    video_id = created["id"]
    full = client.get(f"/videos/{video_id}/file")
    assert full.status_code == 200
    assert full.content == tiny_mp4.read_bytes()
    assert "inline" in full.headers.get("content-disposition", "")

    partial = client.get(
        f"/videos/{video_id}/file",
        headers={"Range": "bytes=0-15"},
    )
    assert partial.status_code == 206
    assert partial.content == tiny_mp4.read_bytes()[:16]
    assert partial.headers["content-range"].startswith("bytes 0-15/")
    assert partial.headers.get("accept-ranges") == "bytes"


def test_delete_removes_row_and_files(client, tiny_mp4: Path) -> None:
    created = _upload(client, tiny_mp4).json()
    stored = Path(created["path"])
    video_id = created["id"]
    assert stored.is_file()

    deleted = client.delete(f"/videos/{video_id}")
    assert deleted.status_code == 204
    assert not stored.exists()
    assert not stored.parent.exists()
    assert client.get(f"/videos/{video_id}").status_code == 404
    assert client.get(f"/videos/{video_id}/file").status_code == 404


def test_list_and_get_metadata(client, tiny_mp4: Path, tiny_audio: Path) -> None:
    first = _upload(client, tiny_mp4).json()
    _upload(client, tiny_audio)
    listed = client.get("/videos")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 2
    detail = client.get(f"/videos/{first['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == first["id"]


def test_missing_video_404(client) -> None:
    missing = "00000000-0000-0000-0000-000000000001"
    assert client.get(f"/videos/{missing}").status_code == 404
    assert client.get(f"/videos/{missing}/file").status_code == 404
    assert client.delete(f"/videos/{missing}").status_code == 404


def test_path_rejects_dotdot(client, tiny_mp4: Path) -> None:
    sneaky = str(tiny_mp4.parent / ".." / tiny_mp4.name)
    response = client.post("/videos", json={"path": sneaky})
    assert response.status_code == 400


def test_path_rejects_missing_file(client) -> None:
    response = client.post("/videos", json={"path": "/tmp/does-not-exist-phase1.mp4"})
    assert response.status_code == 400
