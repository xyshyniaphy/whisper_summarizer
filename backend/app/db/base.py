# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.transcription import Transcription  # noqa
from app.models.summary import Summary  # noqa
