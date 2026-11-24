"""Add event media gallery

Revision ID: 8e6f1a2b9c3d
Revises: 5c8f12b4a1d0
Create Date: 2026-11-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8e6f1a2b9c3d'
down_revision = '5c8f12b4a1d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('event_media',
    sa.Column('media_id', sa.Integer(), nullable=False),
    sa.Column('media_type', sa.Enum('image', 'video', name='event_media_type', native_enum=False), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('caption', sa.Text(), nullable=True),
    sa.Column('image_path', sa.String(length=255), nullable=True),
    sa.Column('video_url', sa.String(length=255), nullable=True),
    sa.Column('status', sa.Enum('published', 'inactive', name='event_media_status', native_enum=False), nullable=False),
    sa.Column('uploaded_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.user_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('media_id')
    )


def downgrade():
    op.drop_table('event_media')
