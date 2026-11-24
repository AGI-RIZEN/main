"""Add decision scenarios (branching game)

Revision ID: 7c2e9f41a8b3
Revises: 3b7d4f9a1e62
Create Date: 2026-11-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c2e9f41a8b3'
down_revision = '3b7d4f9a1e62'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('decision_scenarios',
    sa.Column('scenario_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('intro_text', sa.Text(), nullable=True),
    sa.Column('icon', sa.String(length=10), nullable=False),
    sa.Column('scenario_data', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('published', 'inactive', name='decision_scenario_status', native_enum=False), nullable=False),
    sa.Column('uploaded_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.user_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('scenario_id')
    )


def downgrade():
    op.drop_table('decision_scenarios')
