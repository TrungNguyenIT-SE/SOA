"""Initial notification inbox/delivery schema."""
from alembic import op
from app.worker import Base
revision="0001_notification";down_revision=None;branch_labels=None;depends_on=None
def upgrade(): Base.metadata.create_all(bind=op.get_bind())
def downgrade(): Base.metadata.drop_all(bind=op.get_bind())
