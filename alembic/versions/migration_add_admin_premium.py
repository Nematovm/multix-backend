"""add is_admin is_premium to users + create categories and tests tables

Revision ID: 001_admin_setup
Revises:
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = '001_admin_setup'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. users jadvaliga yangi ustunlar qo'shish
    op.add_column('users', sa.Column('is_admin',   sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'))

    # 2. categories jadvali yaratish
    op.create_table(
        'categories',
        sa.Column('id',          sa.Integer(),     primary_key=True),
        sa.Column('name',        sa.String(150),   nullable=False, unique=True),
        sa.Column('description', sa.String(300),   nullable=True),
        sa.Column('created_at',  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 3. tests jadvali yaratish
    op.create_table(
        'tests',
        sa.Column('id',              sa.Integer(),   primary_key=True),
        sa.Column('name',            sa.String(200), nullable=False),
        sa.Column('description',     sa.String(400), nullable=True),
        sa.Column('category_id',     sa.Integer(),   sa.ForeignKey('categories.id'), nullable=False),
        sa.Column('level',           sa.String(20),  nullable=False, server_default='medium'),
        sa.Column('test_type',       sa.String(20),  nullable=False, server_default='free'),
        sa.Column('skill',           sa.String(20),  nullable=False, server_default='reading'),
        sa.Column('duration',        sa.Integer(),   nullable=False, server_default='60'),
        sa.Column('questions_count', sa.Integer(),   nullable=False, server_default='40'),
        sa.Column('is_active',       sa.Boolean(),   nullable=False, server_default='true'),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_tests_category_id', 'tests', ['category_id'])


def downgrade():
    op.drop_table('tests')
    op.drop_table('categories')
    op.drop_column('users', 'is_premium')
    op.drop_column('users', 'is_admin')
