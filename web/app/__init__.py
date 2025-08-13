from flask import Flask
from .extensions import socketio

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "dev-secret"  # 本番は環境変数で上書き
    # Blueprint登録
    from .routes.main import bp as main_bp
    from .routes.admin import bp as admin_bp
    from .routes.provisioning import bp as prov_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(prov_bp)

    socketio.init_app(app)
    return app
