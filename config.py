"""Application configuration objects.

Why: centralizing environment settings keeps app creation predictable and
avoids hardcoding configuration in multiple places. Secrets and connection
strings come from environment variables (or a local, git-ignored `.env` file);
see `.env.example` for the expected keys.
"""

import os

from dotenv import load_dotenv

# Why: lets `python app.py` pick up a local `.env` file. Variables already set
# in the real environment take precedence over values in the file.
load_dotenv()


class Config:
    """Base shared settings used by all runtime environments."""

    # Why: credentials must never live in source control; read the full
    # SQLAlchemy URI from the environment instead.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    # Why: disabling this avoids unnecessary overhead from change tracking.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Why: signs and verifies JWT tokens. No fallback here, so any environment
    # other than development must provide it explicitly.
    SECRET_KEY = os.environ.get("SECRET_KEY")


class DevelopmentConfig(Config):
    """Local development settings."""

    # Why: detailed tracebacks help while building and debugging routes.
    DEBUG = True
    # Why: a throwaway fallback keeps local development running without extra
    # setup. Tokens signed with it are not safe outside your machine.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")


class TestingConfig:
    """Placeholder for test-specific overrides."""

    pass


class ProductionConfig(Config):
    """Production settings: DATABASE_URL and SECRET_KEY are required."""

    DEBUG = False


config = {
    "DevelopmentConfig": DevelopmentConfig,
    "ProductionConfig": ProductionConfig,
}

# Settings the app cannot start without, mapped to the env var that sets them.
REQUIRED_SETTINGS = {
    "SQLALCHEMY_DATABASE_URI": "DATABASE_URL",
    "SECRET_KEY": "SECRET_KEY",
}
