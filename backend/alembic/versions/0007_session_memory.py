"""session last_times and chat message kind

Revision ID: 0007_session_memory
Revises: 0006_exports
Create Date: 2026-09-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_session_memory"
down_revision: Union[str, Sequence[str], None] = "0006_exports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column(
            "last_times",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "kind",
            sa.String(),
            nullable=False,
            server_default="question",
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "kind")
    op.drop_column("chat_sessions", "last_times")
