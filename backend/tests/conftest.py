from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlmodel import Session, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = "postgresql+psycopg://video:video@127.0.0.1:5432/video_test"


def _run_ffmpeg(args: list[str]) -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("data")


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("media")


@pytest.fixture(scope="session")
def tiny_mp4(media_dir: Path) -> Path:
    path = media_dir / "tiny.mp4"
    _run_ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=f=440:d=1",
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


@pytest.fixture(scope="session")
def tiny_audio(media_dir: Path) -> Path:
    path = media_dir / "tiny.wav"
    _run_ffmpeg(["-y", "-f", "lavfi", "-i", "sine=f=440:d=1", str(path)])
    return path


def _ensure_test_database() -> None:
    admin = create_engine(
        "postgresql+psycopg://video:video@127.0.0.1:5432/postgres",
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'video_test'")
        ).first()
        if exists is None:
            conn.execute(text("CREATE DATABASE video_test"))
    admin.dispose()


@pytest.fixture(scope="session")
def configured_env(data_dir: Path) -> None:
    _ensure_test_database()
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["MAX_UPLOAD_BYTES"] = str(2 * 1024 * 1024 * 1024)

    from app.db import reset_engine
    from app.settings import get_settings

    get_settings.cache_clear()
    reset_engine()

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture
def client(configured_env: None, data_dir: Path) -> TestClient:
    from app.db import get_engine
    from app.main import app
    from app.models import Video
    from app.storage import remove_folder

    with TestClient(app) as test_client:
        yield test_client

    engine = get_engine()
    with Session(engine) as session:
        for row in session.exec(select(Video)).all():
            session.delete(row)
        session.commit()
    videos_root = data_dir / "videos"
    if videos_root.exists():
        remove_folder(videos_root)
