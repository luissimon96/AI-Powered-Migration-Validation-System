"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-09-22 16:30:00.000000

"""
from typing import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create validation_sessions table
    op.create_table(
        "validation_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "source_technology",
            sa.Enum(
                "PYTHON_FLASK",
                "PYTHON_DJANGO",
                "JAVA_SPRING",
                "CSHARP_DOTNET",
                "PHP_LARAVEL",
                "JAVASCRIPT_REACT",
                "JAVASCRIPT_VUE",
                "JAVASCRIPT_ANGULAR",
                "TYPESCRIPT_REACT",
                "TYPESCRIPT_VUE",
                "TYPESCRIPT_ANGULAR",
                name="technologytype",
            ),
            nullable=False,
        ),
        sa.Column("source_technology_version", sa.String(length=100), nullable=True),
        sa.Column("source_framework_details", sa.JSON(), nullable=True),
        sa.Column(
            "target_technology",
            sa.Enum(
                "PYTHON_FLASK",
                "PYTHON_DJANGO",
                "JAVA_SPRING",
                "CSHARP_DOTNET",
                "PHP_LARAVEL",
                "JAVASCRIPT_REACT",
                "JAVASCRIPT_VUE",
                "JAVASCRIPT_ANGULAR",
                "TYPESCRIPT_REACT",
                "TYPESCRIPT_VUE",
                "TYPESCRIPT_ANGULAR",
                name="technologytype",
            ),
            nullable=False,
        ),
        sa.Column("target_technology_version", sa.String(length=100), nullable=True),
        sa.Column("target_framework_details", sa.JSON(), nullable=True),
        sa.Column(
            "validation_scope",
            sa.Enum(
                "UI_LAYOUT",
                "BACKEND_FUNCTIONALITY",
                "DATA_STRUCTURE",
                "API_ENDPOINTS",
                "BUSINESS_LOGIC",
                "BEHAVIORAL_VALIDATION",
                "FULL_SYSTEM",
                name="validationscope",
            ),
            nullable=False,
        ),
        sa.Column(
            "source_input_type",
            sa.Enum("CODE_FILES", "SCREENSHOTS", "HYBRID", name="inputtype"),
            nullable=False,
        ),
        sa.Column("source_files", sa.JSON(), nullable=True),
        sa.Column("source_screenshots", sa.JSON(), nullable=True),
        sa.Column("source_urls", sa.JSON(), nullable=True),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "target_input_type",
            sa.Enum("CODE_FILES", "SCREENSHOTS", "HYBRID", name="inputtype"),
            nullable=False,
        ),
        sa.Column("target_files", sa.JSON(), nullable=True),
        sa.Column("target_screenshots", sa.JSON(), nullable=True),
        sa.Column("target_urls", sa.JSON(), nullable=True),
        sa.Column("target_metadata", sa.JSON(), nullable=True),
        sa.Column("validation_scenarios", sa.JSON(), nullable=True),
        sa.Column("behavioral_timeout", sa.Integer(), nullable=True),
        sa.Column("processing_log", sa.JSON(), nullable=True),
        sa.Column("execution_time", sa.Float(), nullable=True),
        sa.Column("session_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_sessions")),
        sa.UniqueConstraint(
            "request_id", name=op.f("uq_validation_sessions_request_id")
        ),
    )

    # Create indexes for validation_sessions
    op.create_index(
        "ix_validation_sessions_created_at",
        "validation_sessions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_sessions_request_id",
        "validation_sessions",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_validation_sessions_scope",
        "validation_sessions",
        ["validation_scope"],
        unique=False,
    )
    op.create_index(
        "ix_validation_sessions_status", "validation_sessions", ["status"], unique=False
    )
    op.create_index(
        "ix_validation_sessions_status_created",
        "validation_sessions",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_sessions_technologies",
        "validation_sessions",
        ["source_technology", "target_technology"],
        unique=False,
    )
    op.create_index(
        "ix_validation_sessions_updated_at",
        "validation_sessions",
        ["updated_at"],
        unique=False,
    )

    # Create validation_results table
    op.create_table(
        "validation_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("overall_status", sa.String(length=50), nullable=False),
        sa.Column("fidelity_score", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_representation", sa.JSON(), nullable=True),
        sa.Column("target_representation", sa.JSON(), nullable=True),
        sa.Column("execution_time", sa.Float(), nullable=True),
        sa.Column("result_metadata", sa.JSON(), nullable=True),
        sa.Column("result_type", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["validation_sessions.id"],
            name=op.f("fk_validation_results_session_id_validation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_results")),
    )

    # Create indexes for validation_results
    op.create_index(
        "ix_validation_results_created_at",
        "validation_results",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_results_fidelity_score",
        "validation_results",
        ["fidelity_score"],
        unique=False,
    )
    op.create_index(
        "ix_validation_results_overall_status",
        "validation_results",
        ["overall_status"],
        unique=False,
    )
    op.create_index(
        "ix_validation_results_result_type",
        "validation_results",
        ["result_type"],
        unique=False,
    )
    op.create_index(
        "ix_validation_results_session_id",
        "validation_results",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_validation_results_status_score",
        "validation_results",
        ["overall_status", "fidelity_score"],
        unique=False,
    )
    op.create_index(
        "ix_validation_results_type_created",
        "validation_results",
        ["result_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_results_updated_at",
        "validation_results",
        ["updated_at"],
        unique=False,
    )

    # Create validation_discrepancies table
    op.create_table(
        "validation_discrepancies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=True),
        sa.Column("discrepancy_type", sa.String(length=100), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("CRITICAL", "WARNING", "INFO", name="severitylevel"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_element", sa.String(length=500), nullable=True),
        sa.Column("target_element", sa.String(length=500), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("component_type", sa.String(length=50), nullable=True),
        sa.Column("validation_context", sa.JSON(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["validation_results.id"],
            name=op.f("fk_validation_discrepancies_result_id_validation_results"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["validation_sessions.id"],
            name=op.f("fk_validation_discrepancies_session_id_validation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_discrepancies")),
    )

    # Create indexes for validation_discrepancies
    op.create_index(
        "ix_discrepancies_component_resolved",
        "validation_discrepancies",
        ["component_type", "is_resolved"],
        unique=False,
    )
    op.create_index(
        "ix_discrepancies_confidence",
        "validation_discrepancies",
        ["confidence"],
        unique=False,
    )
    op.create_index(
        "ix_discrepancies_severity_type",
        "validation_discrepancies",
        ["severity", "discrepancy_type"],
        unique=False,
    )
    op.create_index(
        "ix_validation_discrepancies_component_type",
        "validation_discrepancies",
        ["component_type"],
        unique=False,
    )
    op.create_index(
        "ix_validation_discrepancies_confidence",
        "validation_discrepancies",
        ["confidence"],
        unique=False,
    )
    op.create_index(
        "ix_validation_discrepancies_created_at",
        "validation_discrepancies",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_discrepancies_discrepancy_type",
        "validation_discrepancies",
        ["discrepancy_type"],
        unique=False,
    )
    op.create_index(
        "ix_validation_discrepancies_is_resolved",
        "validation_discrepancies",
        ["is_resolved"],
        unique=False,
    )
    op.create_index(
        "ix_validation_discrepancies_result_id",
        "validation_discrepancies",
        ["result_id"],
        unique=False,
    )
    op.create_index(
        "ix_validation_discrepancies_session_id",
        "validation_discrepancies",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_validation_discrepancies_severity",
        "validation_discrepancies",
        ["severity"],
        unique=False,
    )
    op.create_index(
        "ix_validation_discrepancies_updated_at",
        "validation_discrepancies",
        ["updated_at"],
        unique=False,
    )

    # Create validation_metrics table
    op.create_table(
        "validation_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("metric_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_period", sa.String(length=20), nullable=False),
        sa.Column("total_sessions", sa.Integer(), nullable=True),
        sa.Column("completed_sessions", sa.Integer(), nullable=True),
        sa.Column("failed_sessions", sa.Integer(), nullable=True),
        sa.Column("approved_count", sa.Integer(), nullable=True),
        sa.Column("approved_with_warnings_count", sa.Integer(), nullable=True),
        sa.Column("rejected_count", sa.Integer(), nullable=True),
        sa.Column("avg_execution_time", sa.Float(), nullable=True),
        sa.Column("max_execution_time", sa.Float(), nullable=True),
        sa.Column("min_execution_time", sa.Float(), nullable=True),
        sa.Column("avg_fidelity_score", sa.Float(), nullable=True),
        sa.Column("max_fidelity_score", sa.Float(), nullable=True),
        sa.Column("min_fidelity_score", sa.Float(), nullable=True),
        sa.Column("technology_breakdown", sa.JSON(), nullable=True),
        sa.Column("scope_breakdown", sa.JSON(), nullable=True),
        sa.Column("total_discrepancies", sa.Integer(), nullable=True),
        sa.Column("critical_discrepancies", sa.Integer(), nullable=True),
        sa.Column("warning_discrepancies", sa.Integer(), nullable=True),
        sa.Column("info_discrepancies", sa.Integer(), nullable=True),
        sa.Column("additional_metrics", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_metrics")),
        sa.UniqueConstraint(
            "metric_date",
            "metric_period",
            name=op.f("uq_validation_metrics_metric_date"),
        ),
    )

    # Create indexes for validation_metrics
    op.create_index(
        "ix_metrics_date_period",
        "validation_metrics",
        ["metric_date", "metric_period"],
        unique=False,
    )
    op.create_index(
        "ix_validation_metrics_created_at",
        "validation_metrics",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_metrics_metric_date",
        "validation_metrics",
        ["metric_date"],
        unique=False,
    )
    op.create_index(
        "ix_validation_metrics_metric_period",
        "validation_metrics",
        ["metric_period"],
        unique=False,
    )
    op.create_index(
        "ix_validation_metrics_updated_at",
        "validation_metrics",
        ["updated_at"],
        unique=False,
    )

    # Create behavioral_test_results table
    op.create_table(
        "behavioral_test_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("scenario_name", sa.String(length=255), nullable=False),
        sa.Column("scenario_description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("target_url", sa.String(length=1000), nullable=False),
        sa.Column("execution_status", sa.String(length=50), nullable=False),
        sa.Column("source_result", sa.JSON(), nullable=True),
        sa.Column("target_result", sa.JSON(), nullable=True),
        sa.Column("comparison_result", sa.JSON(), nullable=True),
        sa.Column("source_screenshots", sa.JSON(), nullable=True),
        sa.Column("target_screenshots", sa.JSON(), nullable=True),
        sa.Column("interaction_log", sa.JSON(), nullable=True),
        sa.Column("source_load_time", sa.Float(), nullable=True),
        sa.Column("target_load_time", sa.Float(), nullable=True),
        sa.Column("execution_duration", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_stack_trace", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["validation_sessions.id"],
            name=op.f("fk_behavioral_test_results_session_id_validation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_behavioral_test_results")),
    )

    # Create indexes for behavioral_test_results
    op.create_index(
        "ix_behavioral_test_results_created_at",
        "behavioral_test_results",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_behavioral_test_results_execution_status",
        "behavioral_test_results",
        ["execution_status"],
        unique=False,
    )
    op.create_index(
        "ix_behavioral_test_results_scenario_name",
        "behavioral_test_results",
        ["scenario_name"],
        unique=False,
    )
    op.create_index(
        "ix_behavioral_test_results_session_id",
        "behavioral_test_results",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_behavioral_test_results_updated_at",
        "behavioral_test_results",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_behavioral_tests_session_created",
        "behavioral_test_results",
        ["session_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_behavioral_tests_status_scenario",
        "behavioral_test_results",
        ["execution_status", "scenario_name"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("behavioral_test_results")
    op.drop_table("validation_metrics")
    op.drop_table("validation_discrepancies")
    op.drop_table("validation_results")
    op.drop_table("validation_sessions")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS severitylevel")
    op.execute("DROP TYPE IF EXISTS inputtype")
    op.execute("DROP TYPE IF EXISTS validationscope")
    op.execute("DROP TYPE IF EXISTS technologytype")
