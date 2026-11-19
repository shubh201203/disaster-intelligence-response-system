"""phase5b schema extensions

Revision ID: phase5b_schema_ext
Revises: 
Create Date: 2026-09-15 17:22:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'phase5b_schema_ext'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create vehicles table
    op.create_table(
        'vehicles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('vehicle_code', sa.String(length=50), nullable=False),
        sa.Column('vehicle_type', sa.String(length=50), nullable=False),
        sa.Column('owner_type', sa.String(length=50), nullable=True, server_default='GOVT'),
        sa.Column('owner_id', sa.String(length=36), nullable=True),
        sa.Column('capacity_weight_kg', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('capacity_volume_m3', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('current_location_lat', sa.Float(), nullable=True),
        sa.Column('current_location_lng', sa.Float(), nullable=True),
        sa.Column('depot_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='AVAILABLE'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('operational_constraints', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['depot_id'], ['resources.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vehicle_code')
    )
    op.create_index(op.f('ix_vehicles_vehicle_code'), 'vehicles', ['vehicle_code'], unique=True)
    op.create_index(op.f('ix_vehicles_vehicle_type'), 'vehicles', ['vehicle_type'], unique=False)
    op.create_index(op.f('ix_vehicles_status'), 'vehicles', ['status'], unique=False)

    # 2. Add columns to road_blockages table
    op.add_column('road_blockages', sa.Column('blockage_status', sa.String(length=50), nullable=True, server_default='IMPASSABLE'))
    op.add_column('road_blockages', sa.Column('effective_at', sa.DateTime(), nullable=True))
    op.add_column('road_blockages', sa.Column('expiry_at', sa.DateTime(), nullable=True))
    op.add_column('road_blockages', sa.Column('delay_penalty_mins', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('road_blockages', sa.Column('source', sa.String(length=100), nullable=True, server_default='FIELD_REPORT'))
    op.add_column('road_blockages', sa.Column('created_by_id', sa.String(length=36), nullable=True))
    op.create_foreign_key('fk_road_blockages_created_by', 'road_blockages', 'users', ['created_by_id'], ['id'])
    op.create_index(op.f('ix_road_blockages_blockage_status'), 'road_blockages', ['blockage_status'], unique=False)

    # 3. Add columns to volunteer_profiles table
    op.add_column('volunteer_profiles', sa.Column('skill_category', sa.String(length=50), nullable=True, server_default='GENERAL'))
    op.add_column('volunteer_profiles', sa.Column('assignment_status', sa.String(length=50), nullable=True, server_default='UNASSIGNED'))
    op.create_index(op.f('ix_volunteer_profiles_skill_category'), 'volunteer_profiles', ['skill_category'], unique=False)
    op.create_index(op.f('ix_volunteer_profiles_assignment_status'), 'volunteer_profiles', ['assignment_status'], unique=False)

    # 4. Create optimization_runs table
    op.create_table(
        'optimization_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='PROPOSED'),
        sa.Column('run_timestamp', sa.DateTime(), nullable=True),
        sa.Column('requesting_user_id', sa.String(length=36), nullable=False),
        sa.Column('objective_config_json', sa.JSON(), nullable=True),
        sa.Column('input_snapshot_json', sa.JSON(), nullable=True),
        sa.Column('solver_metadata_json', sa.JSON(), nullable=True),
        sa.Column('runtime_ms', sa.Float(), nullable=True),
        sa.Column('optimality_gap', sa.Float(), nullable=True),
        sa.Column('feasibility_status', sa.String(length=50), nullable=True, server_default='FEASIBLE'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requesting_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_optimization_runs_status'), 'optimization_runs', ['status'], unique=False)
    op.create_index(op.f('ix_optimization_runs_run_timestamp'), 'optimization_runs', ['run_timestamp'], unique=False)

    # 5. Create optimization_recommendations table
    op.create_table(
        'optimization_recommendations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('recommendation_type', sa.String(length=50), nullable=False),
        sa.Column('incident_id', sa.String(length=36), nullable=True),
        sa.Column('depot_id', sa.String(length=36), nullable=True),
        sa.Column('vehicle_id', sa.String(length=36), nullable=True),
        sa.Column('shelter_id', sa.String(length=36), nullable=True),
        sa.Column('volunteer_id', sa.String(length=36), nullable=True),
        sa.Column('commodity_category', sa.String(length=50), nullable=True),
        sa.Column('allocated_quantity', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('proposed_route_json', sa.JSON(), nullable=True),
        sa.Column('objective_contribution', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='PROPOSED'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['optimization_runs.id'], ),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
        sa.ForeignKeyConstraint(['depot_id'], ['resources.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.ForeignKeyConstraint(['shelter_id'], ['shelters.id'], ),
        sa.ForeignKeyConstraint(['volunteer_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_optimization_recommendations_run_id'), 'optimization_recommendations', ['run_id'], unique=False)
    op.create_index(op.f('ix_optimization_recommendations_recommendation_type'), 'optimization_recommendations', ['recommendation_type'], unique=False)
    op.create_index(op.f('ix_optimization_recommendations_status'), 'optimization_recommendations', ['status'], unique=False)

    # 6. Create optimization_override_logs table
    op.create_table(
        'optimization_override_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('original_value_json', sa.JSON(), nullable=True),
        sa.Column('overridden_value_json', sa.JSON(), nullable=True),
        sa.Column('justification_reason', sa.Text(), nullable=False),
        sa.Column('audit_log_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['optimization_runs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['audit_log_id'], ['audit_logs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_optimization_override_logs_run_id'), 'optimization_override_logs', ['run_id'], unique=False)

def downgrade() -> None:
    op.drop_table('optimization_override_logs')
    op.drop_table('optimization_recommendations')
    op.drop_table('optimization_runs')
    op.drop_column('volunteer_profiles', 'assignment_status')
    op.drop_column('volunteer_profiles', 'skill_category')
    op.drop_constraint('fk_road_blockages_created_by', 'road_blockages', type_='foreignkey')
    op.drop_column('road_blockages', 'created_by_id')
    op.drop_column('road_blockages', 'source')
    op.drop_column('road_blockages', 'delay_penalty_mins')
    op.drop_column('road_blockages', 'expiry_at')
    op.drop_column('road_blockages', 'effective_at')
    op.drop_column('road_blockages', 'blockage_status')
    op.drop_table('vehicles')
