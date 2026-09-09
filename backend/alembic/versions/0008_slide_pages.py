"""slides_status and slide_pages

Revision ID: 0008_slide_pages
Revises: 0007_session_memory
Create Date: 2026-09-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_slide_pages"
down_revision: Union[str, Sequence[str], None] = "0007_session_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "videos",
        sa.Column(
            "slides_status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.execute(
        """
        CREATE TABLE slide_pages (
            id UUID NOT NULL,
            video_id UUID NOT NULL,
            t_start_s FLOAT NOT NULL,
            t_end_s FLOAT NOT NULL,
            embeddings JSON NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        )
        """
    )
    op.create_index("ix_slide_pages_video_id", "slide_pages", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_slide_pages_video_id", table_name="slide_pages")
    op.drop_table("slide_pages")
    op.drop_column("videos", "slides_status")
