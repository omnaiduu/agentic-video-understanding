"""pgvector extension, transcript_status, transcript_lines

Revision ID: 0003_transcript_lines
Revises: 0002_chat_sessions
Create Date: 2026-09-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_transcript_lines"
down_revision: Union[str, Sequence[str], None] = "0002_chat_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "videos",
        sa.Column(
            "transcript_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.execute(
        """
        CREATE TABLE transcript_lines (
            id UUID NOT NULL,
            video_id UUID NOT NULL,
            start_s FLOAT NOT NULL,
            end_s FLOAT NOT NULL,
            text TEXT NOT NULL,
            tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
            embedding vector(384),
            PRIMARY KEY (id),
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        )
        """
    )
    op.create_index("ix_transcript_lines_video_id", "transcript_lines", ["video_id"])
    op.execute(
        "CREATE INDEX ix_transcript_lines_tsv ON transcript_lines USING gin (tsv)"
    )
    op.execute(
        "CREATE INDEX ix_transcript_lines_embedding_hnsw "
        "ON transcript_lines USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_transcript_lines_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_transcript_lines_tsv")
    op.drop_index("ix_transcript_lines_video_id", table_name="transcript_lines")
    op.drop_table("transcript_lines")
    op.drop_column("videos", "transcript_status")
