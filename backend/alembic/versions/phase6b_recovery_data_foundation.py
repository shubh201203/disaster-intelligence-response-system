"""phase6b recovery data foundation

Revision ID: phase6b_recovery_foundation
Revises: phase5f_schema_ext
Create Date: 2026-11-16 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = 'phase6b_recovery_foundation'
down_revision = 'phase5f_schema_ext'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. recovery_assessments
    op.create_table(
        'recovery_assessments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('assessment_code', sa.String(length=50), nullable=False),
        sa.Column('incident_id', sa.String(length=36), nullable=False),
        sa.Column('inspector_id', sa.String(length=36), nullable=False),
        sa.Column('sector', sa.String(length=50), nullable=False),
        sa.Column('facility_name', sa.String(length=255), nullable=False),
        sa.Column('damage_level', sa.String(length=30), nullable=False),
        sa.Column('is_operational', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('estimated_reconstruction_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('structural_notes', sa.Text(), nullable=True),
        sa.Column('evidence_media_urls', sa.JSON(), nullable=True),
        sa.Column('cv_assessment_id', sa.String(length=36), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('geom', Geometry(geometry_type='POINT', srid=4326, spatial_index=False, use_typmod=True), nullable=True),
        sa.Column('assessment_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('superseded_by_id', sa.String(length=36), nullable=True),
        sa.Column('is_current_version', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('deduplication_cluster_id', sa.String(length=36), nullable=True),
        sa.Column('reconciliation_status', sa.String(length=30), nullable=False, server_default='UNRECONCILED'),
        sa.Column('provenance_tier', sa.String(length=50), nullable=False, server_default='TIER_2_GOVT_OFFICIAL'),
        sa.Column('data_confidence', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('freshness_status', sa.String(length=20), nullable=False, server_default='FRESH'),
        sa.Column('verification_status', sa.String(length=30), nullable=False, server_default='PENDING_VERIFICATION'),
        sa.Column('verified_by_id', sa.String(length=36), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cv_assessment_id'], ['cv_damage_assessments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['inspector_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['superseded_by_id'], ['recovery_assessments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_code')
    )
    op.create_index(op.f('ix_recovery_assessments_assessment_code'), 'recovery_assessments', ['assessment_code'], unique=True)
    op.create_index(op.f('ix_recovery_assessments_created_at'), 'recovery_assessments', ['created_at'], unique=False)
    op.create_index(op.f('ix_recovery_assessments_deduplication_cluster_id'), 'recovery_assessments', ['deduplication_cluster_id'], unique=False)
    op.create_index(op.f('ix_recovery_assessments_incident_id'), 'recovery_assessments', ['incident_id'], unique=False)
    op.create_index(op.f('ix_recovery_assessments_inspector_id'), 'recovery_assessments', ['inspector_id'], unique=False)
    op.create_index(op.f('ix_recovery_assessments_is_current_version'), 'recovery_assessments', ['is_current_version'], unique=False)
    op.create_index(op.f('ix_recovery_assessments_sector'), 'recovery_assessments', ['sector'], unique=False)

    # 2. recovery_needs
    op.create_table(
        'recovery_needs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('assessment_id', sa.String(length=36), nullable=True),
        sa.Column('ward_code', sa.String(length=50), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('sector', sa.String(length=50), nullable=False),
        sa.Column('affected_households', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('displaced_persons', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('vulnerable_persons', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('beneficiary_id_hash', sa.String(length=64), nullable=True),
        sa.Column('household_head_name_masked', sa.String(length=100), nullable=True),
        sa.Column('potable_water_demand_liters_day', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('temporary_shelter_units_needed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('livelihood_support_households', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('unmet_need_score', sa.Float(), nullable=True, server_default='50.0'),
        sa.Column('census_baseline_population', sa.Integer(), nullable=False),
        sa.Column('is_reconciled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('reconciliation_notes', sa.String(length=255), nullable=True),
        sa.Column('data_timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['recovery_assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_needs_assessment_id'), 'recovery_needs', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_recovery_needs_beneficiary_id_hash'), 'recovery_needs', ['beneficiary_id_hash'], unique=False)
    op.create_index(op.f('ix_recovery_needs_sector'), 'recovery_needs', ['sector'], unique=False)
    op.create_index(op.f('ix_recovery_needs_ward_code'), 'recovery_needs', ['ward_code'], unique=False)

    # 3. recovery_projects
    op.create_table(
        'recovery_projects',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_code', sa.String(length=50), nullable=False),
        sa.Column('need_id', sa.String(length=36), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sector', sa.String(length=50), nullable=False),
        sa.Column('priority_tier', sa.String(length=20), nullable=False, server_default='TIER_3'),
        sa.Column('priority_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PROPOSED'),
        sa.Column('estimated_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('actual_expenditure', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('funding_source', sa.String(length=100), nullable=True),
        sa.Column('time_indexed_cost_profile', sa.JSON(), nullable=True),
        sa.Column('estimated_duration_days', sa.Integer(), nullable=False),
        sa.Column('actual_duration_days', sa.Integer(), nullable=True),
        sa.Column('earliest_start_date', sa.DateTime(), nullable=True),
        sa.Column('planned_completion_date', sa.DateTime(), nullable=True),
        sa.Column('actual_completion_date', sa.DateTime(), nullable=True),
        sa.Column('lead_agency', sa.String(length=100), nullable=False),
        sa.Column('contractor_name', sa.String(length=150), nullable=True),
        sa.Column('assigned_manager_id', sa.String(length=36), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('geom', Geometry(geometry_type='GEOMETRY', srid=4326, spatial_index=False, use_typmod=True), nullable=True),
        sa.Column('approval_status', sa.String(length=30), nullable=False, server_default='PENDING_APPROVAL'),
        sa.Column('approved_by_id', sa.String(length=36), nullable=True),
        sa.Column('sanction_order_number', sa.String(length=100), nullable=True),
        sa.Column('approval_timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_manager_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['need_id'], ['recovery_needs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_code')
    )
    op.create_index(op.f('ix_recovery_projects_created_at'), 'recovery_projects', ['created_at'], unique=False)
    op.create_index(op.f('ix_recovery_projects_priority_score'), 'recovery_projects', ['priority_score'], unique=False)
    op.create_index(op.f('ix_recovery_projects_project_code'), 'recovery_projects', ['project_code'], unique=True)
    op.create_index(op.f('ix_recovery_projects_sector'), 'recovery_projects', ['sector'], unique=False)
    op.create_index(op.f('ix_recovery_projects_status'), 'recovery_projects', ['status'], unique=False)

    # 4. project_dependencies
    op.create_table(
        'project_dependencies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('predecessor_project_id', sa.String(length=36), nullable=False),
        sa.Column('successor_project_id', sa.String(length=36), nullable=False),
        sa.Column('dependency_type', sa.String(length=30), nullable=False, server_default='FINISH_TO_START'),
        sa.Column('lag_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_critical_path', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['predecessor_project_id'], ['recovery_projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['successor_project_id'], ['recovery_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('predecessor_project_id', 'successor_project_id', name='uq_project_dependency')
    )
    op.create_index(op.f('ix_project_dependencies_predecessor_project_id'), 'project_dependencies', ['predecessor_project_id'], unique=False)
    op.create_index(op.f('ix_project_dependencies_successor_project_id'), 'project_dependencies', ['successor_project_id'], unique=False)

    # 5. recovery_resources
    op.create_table(
        'recovery_resources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('material_category', sa.String(length=50), nullable=False),
        sa.Column('item_description', sa.String(length=255), nullable=False),
        sa.Column('quantity_required', sa.Float(), nullable=False),
        sa.Column('quantity_delivered', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('unit_of_measure', sa.String(length=30), nullable=False),
        sa.Column('unit_cost_estimate', sa.Float(), nullable=False),
        sa.Column('actual_unit_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('supplier_info', sa.String(length=255), nullable=True),
        sa.Column('delivery_status', sa.String(length=30), nullable=False, server_default='ORDERED'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['recovery_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_resources_material_category'), 'recovery_resources', ['material_category'], unique=False)
    op.create_index(op.f('ix_recovery_resources_project_id'), 'recovery_resources', ['project_id'], unique=False)

    # 6. community_recovery_metrics
    op.create_table(
        'community_recovery_metrics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('ward_code', sa.String(length=50), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('metric_date', sa.DateTime(), nullable=False),
        sa.Column('active_shelter_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('remaining_displaced_persons', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('power_grid_restoration_pct', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('potable_water_access_pct', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('healthcare_facility_operational_pct', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('schools_open_pct', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('livelihoods_resumed_pct', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('overall_recovery_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('data_confidence', sa.Float(), nullable=True, server_default='100.0'),
        sa.Column('freshness_status', sa.String(length=20), nullable=True, server_default='FRESH'),
        sa.Column('last_verified_at', sa.DateTime(), nullable=True),
        sa.Column('verified_by_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ward_code', 'metric_date', name='uq_ward_metric_date')
    )
    op.create_index(op.f('ix_community_recovery_metrics_metric_date'), 'community_recovery_metrics', ['metric_date'], unique=False)
    op.create_index(op.f('ix_community_recovery_metrics_ward_code'), 'community_recovery_metrics', ['ward_code'], unique=False)

    # 7. recovery_override_logs
    op.create_table(
        'recovery_override_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('original_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('justification_reason', sa.Text(), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['recovery_projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_override_logs_project_id'), 'recovery_override_logs', ['project_id'], unique=False)
    op.create_index(op.f('ix_recovery_override_logs_timestamp'), 'recovery_override_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_recovery_override_logs_user_id'), 'recovery_override_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('recovery_override_logs')
    op.drop_table('community_recovery_metrics')
    op.drop_table('recovery_resources')
    op.drop_table('project_dependencies')
    op.drop_table('recovery_projects')
    op.drop_table('recovery_needs')
    op.drop_table('recovery_assessments')
