import os, csv, time, socket
from datetime import datetime
from threading import Thread
from typing import Dict
from app.extensions import socketio
from app.config import UDP_IP, SENSOR_SND_UPORT, DISCONNECT_TIMEOUT, LOG_DIR, CSV_HEADER

latest_data: Dict[str, float] = {}
last_udp_time = time.time()

def udp_listener():
    global latest_data, last_udp_time
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, SENSOR_SND_UPORT))
    print(f"[SEN] Listening on {SENSOR_SND_UPORT}...")
    while True:
        data, _ = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()
        last_udp_time = time.time()
        try:
            parts = dict(item.split("=") for item in msg.split(","))
            latest_data = {
                k: float(v)
                for k, v in parts.items()
                if v.replace(".", "", 1).replace("-", "", 1).isdigit()
            }
        except Exception as e:
            print(f"[SEN] Parse error Data: {data}")
            print(f"[SEN] Parse error: {e}")

def emit_loop():
    disconnected = False
    last_date = None
    last_saved = None
    os.makedirs(LOG_DIR, exist_ok=True)

    while True:
        now = time.time()
        now_str = datetime.now().strftime("%Y-%m-%d")
        csv_path = os.path.join(LOG_DIR, f"data_{now_str}.csv")

        if last_date != now_str:
            if not os.path.exists(csv_path):
                with open(csv_path, "w", newline="") as f:
                    csv.writer(f).writerow(CSV_HEADER)
            last_date = now_str

        if now - last_udp_time > DISCONNECT_TIMEOUT:
            if not disconnected:
                socketio.emit("connection_lost")
                disconnected = True
        else:
            if disconnected:
                socketio.emit("connection_restored")
                disconnected = False

            if latest_data:
                socketio.emit("sensor_data", latest_data)
                if latest_data != last_saved:
                    row = [datetime.now().isoformat()] + [latest_data.get(k, "") for k in CSV_HEADER[1:]]
                    try:
                        with open(csv_path, "a", newline="") as f:
                            csv.writer(f).writerow(row)
                        last_saved = latest_data.copy()
                    except Exception as e:
                        print(f"[CSV] Write failed: {e}")
        time.sleep(3)

def start_sensor_threads():
    Thread(target=udp_listener, daemon=True).start()
    Thread(target=emit_loop, daemon=True).start()
