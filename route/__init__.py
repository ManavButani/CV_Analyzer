from core.app import app
from const.route import DS
from . import auth
from . import user
from . import resume_screening
from . import llm_provider
from . import screening_history

app.include_router(auth.router, prefix=f"{DS}/auth", tags=["auth"])

app.include_router(user.router, prefix=f"{DS}/user", tags=["user"])

app.include_router(resume_screening.router, prefix=f"{DS}/resume_screening", tags=["resume_screening"])

app.include_router(llm_provider.router, prefix=f"{DS}/llm_provider", tags=["llm_provider"])

app.include_router(screening_history.router, prefix=f"{DS}/screening_history", tags=["screening_history"])
