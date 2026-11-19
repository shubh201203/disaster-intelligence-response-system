"""phase5f schema extensions

Revision ID: phase5f_schema_ext
Revises: phase5b_schema_ext
Create Date: 2026-09-22 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'phase5f_schema_ext'
down_revision = 'phase5b_schema_ext'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Extend shelters table
    op.add_column('shelters', sa.Column('accessibility_features', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('shelters', sa.Column('power_available', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('shelters', sa.Column('sanitation_available', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('shelters', sa.Column('disaster_compatibility', sa.JSON(), nullable=True))
    op.add_column('shelters', sa.Column('last_verified_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_shelters_accessibility_features'), 'shelters', ['accessibility_features'], unique=False)

    # 2. Extend volunteer_profiles table
    op.add_column('volunteer_profiles', sa.Column('max_shift_hours', sa.Float(), nullable=True, server_default='8.0'))
    op.add_column('volunteer_profiles', sa.Column('max_travel_time_mins', sa.Float(), nullable=True, server_default='45.0'))
    op.add_column('volunteer_profiles', sa.Column('shift_availability', sa.JSON(), nullable=True))

    # 3. Extend incidents table
    op.add_column('incidents', sa.Column('required_skills', sa.JSON(), nullable=True))
    op.add_column('incidents', sa.Column('evacuation_demographics', sa.JSON(), nullable=True))

    # 4. Extend optimization_runs table
    op.add_column('optimization_runs', sa.Column('graph_version', sa.String(length=64), nullable=True))

    # 5. Extend optimization_recommendations table
    op.add_column('optimization_recommendations', sa.Column('demographic_group', sa.String(length=50), nullable=True))
    op.add_column('optimization_recommendations', sa.Column('skill_category', sa.String(length=50), nullable=True))
    op.add_column('optimization_recommendations', sa.Column('shift_id', sa.String(length=50), nullable=True))
    op.add_column('optimization_recommendations', sa.Column('transit_time_minutes', sa.Float(), nullable=True))
    op.add_column('optimization_recommendations', sa.Column('transit_distance_km', sa.Float(), nullable=True))
    op.create_index(op.f('ix_optimization_recommendations_demographic_group'), 'optimization_recommendations', ['demographic_group'], unique=False)
    op.create_index(op.f('ix_optimization_recommendations_skill_category'), 'optimization_recommendations', ['skill_category'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_optimization_recommendations_skill_category'), table_name='optimization_recommendations')
    op.drop_index(op.f('ix_optimization_recommendations_demographic_group'), table_name='optimization_recommendations')
    op.drop_column('optimization_recommendations', 'transit_distance_km')
    op.drop_column('optimization_recommendations', 'transit_time_minutes')
    op.drop_column('optimization_recommendations', 'shift_id')
    op.drop_column('optimization_recommendations', 'skill_category')
    op.drop_column('optimization_recommendations', 'demographic_group')

    op.drop_column('optimization_runs', 'graph_version')

    op.drop_column('incidents', 'evacuation_demographics')
    op.drop_column('incidents', 'required_skills')

    op.drop_column('volunteer_profiles', 'shift_availability')
    op.drop_column('volunteer_profiles', 'max_travel_time_mins')
    op.drop_column('volunteer_profiles', 'max_shift_hours')

    op.drop_index(op.f('ix_shelters_accessibility_features'), table_name='shelters')
    op.drop_column('shelters', 'last_verified_at')
    op.drop_column('shelters', 'disaster_compatibility')
    op.drop_column('shelters', 'sanitation_available')
    op.drop_column('shelters', 'power_available')
    op.drop_column('shelters', 'accessibility_features')
