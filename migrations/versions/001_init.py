"""Initial database schema for AutoTest

Revision ID: 001_init
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("status", sa.String(32), server_default="created"),
        sa.Column("platforms", sa.JSON(), nullable=True),
        sa.Column("entries", sa.JSON(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("project_id", sa.String(32), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("type", sa.String(32), server_default="prd"),
        sa.Column("description", sa.String(500), server_default=""),
        sa.Column("version", sa.String(32), server_default=""),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("rule_count", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("project_id", sa.String(32), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("quality_grade", sa.String(4), server_default="C"),
        sa.Column("quality_score", sa.JSON(), nullable=True),
        sa.Column("total_rules", sa.Integer(), server_default="0"),
        sa.Column("confirmed_rules", sa.Integer(), server_default="0"),
        sa.Column("conflicts_count", sa.Integer(), server_default="0"),
        sa.Column("human_reviewed", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "business_rules",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("kb_id", sa.String(32), sa.ForeignKey("knowledge_bases.id"), nullable=False),
        sa.Column("category", sa.String(32), server_default="rule"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_doc_id", sa.String(32), server_default=""),
        sa.Column("source_strategy", sa.String(32), server_default=""),
        sa.Column("confidence", sa.Float(), server_default="0.0"),
        sa.Column("status", sa.String(16), server_default="candidate"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "scenarios",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("project_id", sa.String(32), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("business_line", sa.String(128), server_default=""),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("type", sa.String(32), server_default="positive"),
        sa.Column("role", sa.String(64), server_default=""),
        sa.Column("status", sa.String(16), server_default="draft"),
        sa.Column("coverage", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "test_cases",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("scenario_id", sa.String(32), sa.ForeignKey("scenarios.id"), nullable=False),
        sa.Column("project_id", sa.String(32), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("expected_results", sa.JSON(), nullable=True),
        sa.Column("preconditions", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("project_id", sa.String(32), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), server_default=""),
        sa.Column("status", sa.String(32), server_default="queued"),
        sa.Column("platforms", sa.JSON(), nullable=True),
        sa.Column("progress", sa.JSON(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("total_cases", sa.Integer(), server_default="0"),
        sa.Column("passed_count", sa.Integer(), server_default="0"),
        sa.Column("failed_count", sa.Integer(), server_default="0"),
        sa.Column("uncertain_count", sa.Integer(), server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "step_records",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("case_id", sa.String(32), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(16), server_default="web"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("duration_ms", sa.Integer(), server_default="0"),
        sa.Column("screenshots", sa.JSON(), nullable=True),
        sa.Column("console_snapshot", sa.JSON(), nullable=True),
        sa.Column("network_snapshot", sa.JSON(), nullable=True),
        sa.Column("page_state", sa.JSON(), nullable=True),
        sa.Column("verifications", sa.JSON(), nullable=True),
        sa.Column("cross_dimension_report", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "defects",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("step_record_id", sa.String(32), server_default=""),
        sa.Column("type", sa.String(32), server_default="api_error"),
        sa.Column("severity", sa.String(16), server_default="medium"),
        sa.Column("title", sa.String(500), server_default=""),
        sa.Column("step_context", sa.JSON(), nullable=True),
        sa.Column("screenshots", sa.JSON(), nullable=True),
        sa.Column("console_logs", sa.JSON(), nullable=True),
        sa.Column("api_calls", sa.JSON(), nullable=True),
        sa.Column("page_state", sa.JSON(), nullable=True),
        sa.Column("ai_analysis", sa.JSON(), nullable=True),
        sa.Column("fix_suggestion", sa.JSON(), nullable=True),
        sa.Column("cross_dimension_analysis", sa.JSON(), nullable=True),
        sa.Column("is_false_positive", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("defects")
    op.drop_table("step_records")
    op.drop_table("runs")
    op.drop_table("test_cases")
    op.drop_table("scenarios")
    op.drop_table("business_rules")
    op.drop_table("knowledge_bases")
    op.drop_table("documents")
    op.drop_table("projects")
