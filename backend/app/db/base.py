# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.transcription import Transcription  # noqa
from app.models.summary import Summary  # noqa
from app.models.gemini_request_log import GeminiRequestLog  # noqa
from app.models.chat_message import ChatMessage  # noqa
from app.models.share_link import ShareLink  # noqa
