import os

from dotenv import load_dotenv

from sqlalchemy import create_engine


# =========================
# CARGAR VARIABLES
# =========================

load_dotenv()


# =========================
# VARIABLES ENTORNO
# =========================

DB_USER = os.getenv(
    "DB_USER"
)

DB_PASSWORD = os.getenv(
    "DB_PASSWORD"
)

DB_HOST = os.getenv(
    "DB_HOST"
)

DB_PORT = os.getenv(
    "DB_PORT"
)

DB_NAME = os.getenv(
    "DB_NAME"
)


# =========================
# URL DATABASE
# =========================

DATABASE_URL = (

    f"postgresql://"

    f"{DB_USER}:"

    f"{DB_PASSWORD}@"

    f"{DB_HOST}:"

    f"{DB_PORT}/"

    f"{DB_NAME}"
)


# =========================
# ENGINE
# =========================

engine = create_engine(
    DATABASE_URL
)