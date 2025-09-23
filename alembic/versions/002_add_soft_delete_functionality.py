"""Add soft delete functionality

Revision ID: 002_add_soft_delete
Revises: 001_initial_migration
Create Date: 2024-09-23 10:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '002_add_soft_delete'
down_revision = '001_initial_migration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add soft delete columns to all main tables."""
    # Add soft delete columns to validation_sessions
    op.add_column(
        'validation_sessions',
        sa.Column(
            'deleted_at',
            sa.DateTime(
                timezone=True),
            nullable=True))
    op.add_column(
        'validation_sessions',
        sa.Column(
            'deleted_by',
            sa.String(255),
            nullable=True))
    op.add_column(
        'validation_sessions',
        sa.Column(
            'deletion_reason',
            sa.Text(),
            nullable=True))
    op.add_column(
        'validation_sessions',
        sa.Column(
            'is_deleted',
            sa.Boolean(),
            nullable=False,
            server_default='false'))

    # Create index on is_deleted for performance
    op.create_index(
        op.f('ix_validation_sessions_is_deleted'),
        'validation_sessions',
        ['is_deleted'],
        unique=False)
    op.create_index(
        op.f('ix_validation_sessions_deleted_at'),
        'validation_sessions',
        ['deleted_at'],
        unique=False)

    # Add soft delete columns to validation_results
    op.add_column(
        'validation_results',
        sa.Column(
            'deleted_at',
            sa.DateTime(
                timezone=True),
            nullable=True))
    op.add_column(
        'validation_results',
        sa.Column(
            'deleted_by',
            sa.String(255),
            nullable=True))
    op.add_column(
        'validation_results',
        sa.Column(
            'deletion_reason',
            sa.Text(),
            nullable=True))
    op.add_column(
        'validation_results',
        sa.Column(
            'is_deleted',
            sa.Boolean(),
            nullable=False,
            server_default='false'))

    # Create index on is_deleted for performance
    op.create_index(
        op.f('ix_validation_results_is_deleted'),
        'validation_results',
        ['is_deleted'],
        unique=False)
    op.create_index(
        op.f('ix_validation_results_deleted_at'),
        'validation_results',
        ['deleted_at'],
        unique=False)

    # Add soft delete columns to validation_discrepancies
    op.add_column(
        'validation_discrepancies',
        sa.Column(
            'deleted_at',
            sa.DateTime(
                timezone=True),
            nullable=True))
    op.add_column(
        'validation_discrepancies',
        sa.Column(
            'deleted_by',
            sa.String(255),
            nullable=True))
    op.add_column(
        'validation_discrepancies',
        sa.Column(
            'deletion_reason',
            sa.Text(),
            nullable=True))
    op.add_column(
        'validation_discrepancies',
        sa.Column(
            'is_deleted',
            sa.Boolean(),
            nullable=False,
            server_default='false'))

    # Create index on is_deleted for performance
    op.create_index(
        op.f('ix_validation_discrepancies_is_deleted'),
        'validation_discrepancies',
        ['is_deleted'],
        unique=False)
    op.create_index(
        op.f('ix_validation_discrepancies_deleted_at'),
        'validation_discrepancies',
        ['deleted_at'],
        unique=False)

    # Add soft delete columns to behavioral_test_results
    op.add_column(
        'behavioral_test_results',
        sa.Column(
            'deleted_at',
            sa.DateTime(
                timezone=True),
            nullable=True))
    op.add_column(
        'behavioral_test_results',
        sa.Column(
            'deleted_by',
            sa.String(255),
            nullable=True))
    op.add_column(
        'behavioral_test_results',
        sa.Column(
            'deletion_reason',
            sa.Text(),
            nullable=True))
    op.add_column(
        'behavioral_test_results',
        sa.Column(
            'is_deleted',
            sa.Boolean(),
            nullable=False,
            server_default='false'))

    # Create index on is_deleted for performance
    op.create_index(
        op.f('ix_behavioral_test_results_is_deleted'),
        'behavioral_test_results',
        ['is_deleted'],
        unique=False)
    op.create_index(
        op.f('ix_behavioral_test_results_deleted_at'),
        'behavioral_test_results',
        ['deleted_at'],
        unique=False)

    # Add soft delete columns to validation_metrics
    op.add_column(
        'validation_metrics',
        sa.Column(
            'deleted_at',
            sa.DateTime(
                timezone=True),
            nullable=True))
    op.add_column(
        'validation_metrics',
        sa.Column(
            'deleted_by',
            sa.String(255),
            nullable=True))
    op.add_column(
        'validation_metrics',
        sa.Column(
            'deletion_reason',
            sa.Text(),
            nullable=True))
    op.add_column(
        'validation_metrics',
        sa.Column(
            'is_deleted',
            sa.Boolean(),
            nullable=False,
            server_default='false'))

    # Create index on is_deleted for performance
    op.create_index(
        op.f('ix_validation_metrics_is_deleted'),
        'validation_metrics',
        ['is_deleted'],
        unique=False)
    op.create_index(
        op.f('ix_validation_metrics_deleted_at'),
        'validation_metrics',
        ['deleted_at'],
        unique=False)


def downgrade() -> None:
    """Remove soft delete columns from all main tables."""
    # Drop indexes first
    op.drop_index(
        op.f('ix_validation_metrics_deleted_at'),
        table_name='validation_metrics')
    op.drop_index(
        op.f('ix_validation_metrics_is_deleted'),
        table_name='validation_metrics')
    op.drop_index(
        op.f('ix_behavioral_test_results_deleted_at'),
        table_name='behavioral_test_results')
    op.drop_index(
        op.f('ix_behavioral_test_results_is_deleted'),
        table_name='behavioral_test_results')
    op.drop_index(op.f('ix_validation_discrepancies_deleted_at'),
                  table_name='validation_discrepancies')
    op.drop_index(op.f('ix_validation_discrepancies_is_deleted'),
                  table_name='validation_discrepancies')
    op.drop_index(
        op.f('ix_validation_results_deleted_at'),
        table_name='validation_results')
    op.drop_index(
        op.f('ix_validation_results_is_deleted'),
        table_name='validation_results')
    op.drop_index(
        op.f('ix_validation_sessions_deleted_at'),
        table_name='validation_sessions')
    op.drop_index(
        op.f('ix_validation_sessions_is_deleted'),
        table_name='validation_sessions')

    # Drop columns from validation_metrics
    op.drop_column('validation_metrics', 'is_deleted')
    op.drop_column('validation_metrics', 'deletion_reason')
    op.drop_column('validation_metrics', 'deleted_by')
    op.drop_column('validation_metrics', 'deleted_at')

    # Drop columns from behavioral_test_results
    op.drop_column('behavioral_test_results', 'is_deleted')
    op.drop_column('behavioral_test_results', 'deletion_reason')
    op.drop_column('behavioral_test_results', 'deleted_by')
    op.drop_column('behavioral_test_results', 'deleted_at')

    # Drop columns from validation_discrepancies
    op.drop_column('validation_discrepancies', 'is_deleted')
    op.drop_column('validation_discrepancies', 'deletion_reason')
    op.drop_column('validation_discrepancies', 'deleted_by')
    op.drop_column('validation_discrepancies', 'deleted_at')

    # Drop columns from validation_results
    op.drop_column('validation_results', 'is_deleted')
    op.drop_column('validation_results', 'deletion_reason')
    op.drop_column('validation_results', 'deleted_by')
    op.drop_column('validation_results', 'deleted_at')

    # Drop columns from validation_sessions
    op.drop_column('validation_sessions', 'is_deleted')
    op.drop_column('validation_sessions', 'deletion_reason')
    op.drop_column('validation_sessions', 'deleted_by')
    op.drop_column('validation_sessions', 'deleted_at')
