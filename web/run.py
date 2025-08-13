# -*- coding: utf-8 -*-
import eventlet
eventlet.monkey_patch()  # ← 必ず最初

from app import create_app
from app.extensions import socketio
from app.services.sensor import start_sensor_threads
from app.services.provisioning import start_provisioning_listener, load_desired_from_csv

app = create_app()

if __name__ == "__main__":
    load_desired_from_csv()               # Desired CSVのロード（元処理踏襲）
    start_sensor_threads()                # UDPリスナ & emit_loop 起動
    start_provisioning_listener()         # CFGリスナ起動
    socketio.run(app, host="0.0.0.0", port=5000)
