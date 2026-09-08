"""audio_status and audio_chunks

Revision ID: 0005_audio_chunks
Revises: 0004_visual_frames
Create Date: 2026-09-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_audio_chunks"
down_revision: Union[str, Sequence[str], None] = "0004_visual_frames"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column(
            "audio_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.execute(
        """
        CREATE TABLE audio_chunks (
            id UUID NOT NULL,
            video_id UUID NOT NULL,
            start_s FLOAT NOT NULL,
            end_s FLOAT NOT NULL,
            embedding vector(512),
            PRIMARY KEY (id),
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        )
        """
    )
    op.create_index("ix_audio_chunks_video_id", "audio_chunks", ["video_id"])
    op.execute(
        "CREATE INDEX ix_audio_chunks_embedding_hnsw "
        "ON audio_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audio_chunks_embedding_hnsw")
    op.drop_index("ix_audio_chunks_video_id", table_name="audio_chunks")
    op.drop_table("audio_chunks")
    op.drop_column("videos", "audio_status")
