"""Add image_url fields to housing and activity options

Revision ID: 002_add_image_fields
Revises: 001_add_trip_fields
Create Date: 2025-01-26 09:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_image_fields'
down_revision = '001_add_trip_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Add image_url column to housing_option table
    op.add_column('housing_option', sa.Column('image_url', sa.String(length=500), nullable=True))
    
    # Add image_url column to activity_option table
    op.add_column('activity_option', sa.Column('image_url', sa.String(length=500), nullable=True))

def downgrade():
    # Remove image_url column from activity_option table
    op.drop_column('activity_option', 'image_url')
    
    # Remove image_url column from housing_option table
    op.drop_column('housing_option', 'image_url')
