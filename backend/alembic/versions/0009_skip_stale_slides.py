"""Skip leftover pending slides on videos whose other books finished.

Revision ID: 0009_skip_stale_slides
Revises: 0008_slide_pages
Create Date: 2026-09-09

0008 added slides_status NOT NULL DEFAULT pending. Rows that already
finished speech / pictures / sound never scheduled ColQwen, so they
stayed pending and the website kept polling / locked chat.

"""

from typing import Sequence, Union

from alembic import op

revision: str = "0009_skip_stale_slides"
down_revision: Union[str, Sequence[str], None] = "0008_slide_pages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TERMINAL = "('ready', 'skipped', 'error')"


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE videos
        SET slides_status = 'skipped'
        WHERE slides_status = 'pending'
          AND transcript_status IN {_TERMINAL}
          AND visual_status IN {_TERMINAL}
          AND audio_status IN {_TERMINAL}
        """
    )


def downgrade() -> None:
    pass
