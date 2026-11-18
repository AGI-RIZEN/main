"""Mark demo quizzes and store news key points.

Revision ID: 5c8f12b4a1d0
Revises: 212a73fe285f
Create Date: 2026-11-17 23:08:45.235000
"""
from alembic import op
import sqlalchemy as sa


revision = "5c8f12b4a1d0"
down_revision = "212a73fe285f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "quizzes",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.execute(
        "UPDATE quizzes SET is_demo = 1 "
        "WHERE description = 'Clearly labeled seed content for local project demonstration.'"
    )

    op.add_column("cyber_news", sa.Column("display_title", sa.String(length=300), nullable=True))
    op.add_column("cyber_news", sa.Column("key_points", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("cyber_news", "key_points")
    op.drop_column("cyber_news", "display_title")
    op.drop_column("quizzes", "is_demo")
