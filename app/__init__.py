"""Flask application factory.

Why: the factory pattern keeps setup reusable for different environments and
prevents side effects when modules are imported.
"""

from flask import Flask
from config import config, REQUIRED_SETTINGS
from app.extensions import db, ma, limiter, cache


def create_app(config_name="DevelopmentConfig"):
    """Create and configure the Flask app instance.

    Why: wrapping setup in a function allows tests and scripts to create isolated
    app instances with different configuration targets.
    """

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Why: fail at startup with a clear message instead of on the first request
    # (or, worse, signing tokens with an empty key).
    missing = [env for key, env in REQUIRED_SETTINGS.items() if not app.config.get(key)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s) for {config_name}: "
            f"{', '.join(missing)}. Copy .env.example to .env and fill them in."
        )

    # Why: initializing extensions here binds them to this specific app instance.
    db.init_app(app)
    ma.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)

    # Why: importing models ensures SQLAlchemy knows all tables before create_all.
    from app import models

    # Why: blueprints split the API by domain and keep route files focused.
    from app.blueprints.customers import customers_bp
    from app.blueprints.mechanics import mechanics_bp
    from app.blueprints.vehicles import vehicles_bp
    from app.blueprints.service_tickets import service_tickets_bp
    from app.blueprints.inventory import inventory_bp

    app.register_blueprint(customers_bp)
    app.register_blueprint(mechanics_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(service_tickets_bp)
    app.register_blueprint(inventory_bp)

    # Why: guarantees tables exist when running locally without migrations.
    with app.app_context():
        db.create_all()

    return app
