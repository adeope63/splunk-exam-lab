"""Initial immutable local database schema."""
from alembic import op
import sqlalchemy as sa
revision='0001'
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('challenge_attempts',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('challenge_id', sa.String(), primary_key=False, nullable=False),
        sa.Column('answer', sa.Text(), primary_key=False, nullable=False),
        sa.Column('correct', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('created_at', sa.Float(), primary_key=False, nullable=False),
    )
    op.create_table('domains',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), primary_key=False, nullable=False),
        sa.Column('weight', sa.Integer(), primary_key=False, nullable=False),
    )
    op.create_table('exams',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('mode', sa.String(), primary_key=False, nullable=False),
        sa.Column('started_at', sa.Float(), primary_key=False, nullable=False),
        sa.Column('deadline', sa.Float(), primary_key=False, nullable=True),
        sa.Column('submitted_at', sa.Float(), primary_key=False, nullable=True),
        sa.Column('status', sa.String(), primary_key=False, nullable=False),
        sa.Column('feedback', sa.String(), primary_key=False, nullable=False),
        sa.Column('score', sa.Float(), primary_key=False, nullable=True),
        sa.Column('current_index', sa.Integer(), primary_key=False, nullable=False),
    )
    op.create_index('ix_exams_status', 'exams', ['status'], unique=False)
    op.create_table('revision',
        sa.Column('question_id', sa.String(), primary_key=True, nullable=False),
        sa.Column('bookmarked', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('note', sa.Text(), primary_key=False, nullable=False),
    )
    op.create_table('settings',
        sa.Column('key', sa.String(), primary_key=True, nullable=False),
        sa.Column('value', sa.JSON(), primary_key=False, nullable=False),
    )
    op.create_table('exam_items',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('exam_id', sa.String(), sa.ForeignKey('exams.id', ondelete='CASCADE'), primary_key=False, nullable=False),
        sa.Column('position', sa.Integer(), primary_key=False, nullable=False),
        sa.Column('question_id', sa.String(), primary_key=False, nullable=False),
        sa.Column('snapshot', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('selected', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('flagged', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('checked', sa.Boolean(), primary_key=False, nullable=False),
        sa.Column('correct', sa.Boolean(), primary_key=False, nullable=True),
    )
    op.create_index('ix_exam_items_exam_id', 'exam_items', ['exam_id'], unique=False)
    op.create_index('ix_exam_items_question_id', 'exam_items', ['question_id'], unique=False)
    op.create_table('objectives',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('domain_id', sa.Integer(), sa.ForeignKey('domains.id', ondelete=None), primary_key=False, nullable=False),
        sa.Column('name', sa.String(), primary_key=False, nullable=False),
    )
    op.create_index('ix_objectives_domain_id', 'objectives', ['domain_id'], unique=False)
    op.create_table('questions',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('objective_id', sa.String(), sa.ForeignKey('objectives.id', ondelete=None), primary_key=False, nullable=False),
        sa.Column('content', sa.JSON(), primary_key=False, nullable=False),
        sa.Column('fingerprint', sa.String(), primary_key=False, nullable=False, unique=True),
        sa.Column('active', sa.Boolean(), primary_key=False, nullable=False),
    )
    op.create_index('ix_questions_objective_id', 'questions', ['objective_id'], unique=False)
def downgrade():
    op.drop_table('questions')
    op.drop_table('objectives')
    op.drop_table('exam_items')
    op.drop_table('settings')
    op.drop_table('revision')
    op.drop_table('exams')
    op.drop_table('domains')
    op.drop_table('challenge_attempts')
