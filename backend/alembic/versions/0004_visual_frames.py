"""visual_status and visual_frames

Revision ID: 0004_visual_frames
Revises: 0003_transcript_lines
Create Date: 2026-09-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_visual_frames"
down_revision: Union[str, Sequence[str], None] = "0003_transcript_lines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column(
            "visual_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.execute(
        """
        CREATE TABLE visual_frames (
            id UUID NOT NULL,
            video_id UUID NOT NULL,
            t_s FLOAT NOT NULL,
            embedding vector(1152),
            PRIMARY KEY (id),
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        )
        """
    )
    op.create_index("ix_visual_frames_video_id", "visual_frames", ["video_id"])
    op.execute(
        "CREATE INDEX ix_visual_frames_embedding_hnsw "
        "ON visual_frames USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_visual_frames_embedding_hnsw")
    op.drop_index("ix_visual_frames_video_id", table_name="visual_frames")
    op.drop_table("visual_frames")
    op.drop_column("videos", "visual_status")
