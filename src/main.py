from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database.core import Base, engine, verify_database_connections
from .entities.user import User
from .entities.conversation import Conversation
from .api import register_routes
from .logging import configure_logging, LogLevels

configure_logging(LogLevels.info)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    verify_database_connections()
    # Apaga as tabelas existentes
    # Base.metadata.drop_all(bind=engine) 
    # Cria as tabelas automaticamente
    Base.metadata.create_all(bind=engine)

register_routes(app)