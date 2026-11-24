"""Add posters and infographics content tables

Revision ID: 3b7d4f9a1e62
Revises: 8e6f1a2b9c3d
Create Date: 2026-11-21 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b7d4f9a1e62'
down_revision = '8e6f1a2b9c3d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('posters',
    sa.Column('poster_id', sa.Integer(), nullable=False),
    sa.Column('tone', sa.String(length=10), nullable=False),
    sa.Column('icon', sa.String(length=10), nullable=False),
    sa.Column('title_en', sa.String(length=200), nullable=False),
    sa.Column('tips_en', sa.Text(), nullable=False),
    sa.Column('title_hi', sa.String(length=200), nullable=False),
    sa.Column('tips_hi', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('published', 'inactive', name='poster_status', native_enum=False), nullable=False),
    sa.Column('uploaded_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.user_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('poster_id')
    )
    op.create_table('infographics',
    sa.Column('infographic_id', sa.Integer(), nullable=False),
    sa.Column('icon', sa.String(length=10), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('published', 'inactive', name='infographic_status', native_enum=False), nullable=False),
    sa.Column('uploaded_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.user_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('infographic_id')
    )


def downgrade():
    op.drop_table('infographics')
    op.drop_table('posters')
