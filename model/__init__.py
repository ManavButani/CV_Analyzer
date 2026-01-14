from core.database import Base, engine
from . import user
from . import llm_provider
from . import screening_request

Base.metadata.create_all(bind=engine)
