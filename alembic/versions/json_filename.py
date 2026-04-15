"""add json_filename to tests

Revision ID: add_json_filename
Revises: 
Create Date: 2026-01-01

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_json_filename'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tests', sa.Column('json_filename', sa.String(300), nullable=True))


def downgrade():
    op.drop_column('tests', 'json_filename')