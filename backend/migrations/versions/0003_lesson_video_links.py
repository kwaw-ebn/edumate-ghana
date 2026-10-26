"""Add optional teacher-selected online videos."""
from alembic import op
from app.db import Base
from app import models
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None

def upgrade():
    Base.metadata.tables['lesson_video_links'].create(op.get_bind(),checkfirst=True)

def downgrade():
    Base.metadata.tables['lesson_video_links'].drop(op.get_bind(),checkfirst=True)
