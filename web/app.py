# -*- coding: utf-8
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, abort, jsonify, request, redirect, url_for, flash
from flask_socketio import SocketIO
import socket
import threading
import time
import csv
from datetime import datetime
import os
import shutil
import tempfile

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
socketio = SocketIO(app)

UDP_IP = "0.0.0.0"
UDP_PORT = 12345
latest_data = {}
last_udp_time = time.time()

DISCONNECT_TIMEOUT = 600 + 20
CSV_HEADER = ["timestamp", "Temp", "Hum", "Pres", "Light", "Soil", "Bus", "Current", "Power"]
LOG_DIR = "log"
os.makedirs(LOG_DIR, exist_ok=True)

def udp_listener():
    global latest_data, last_udp_time
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"[UDP] Listening on {UDP_PORT}...")
    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode("utf-8").strip()
        last_udp_time = time.time()
        try:
            parts = dict(item.split("=") for item in msg.split(","))
            latest_data = {k: float(v) for k, v in parts.items() if v.replace('.', '', 1).replace('-', '', 1).isdigit()}
        except Exception as e:
            print(f"[UDP] Parse error: {e}")

def emit_loop():
    disconnected = False
    last_date = None
    last_saved = None
    while True:
        now = time.time()
        now_str = datetime.now().strftime("%Y-%m-%d")
        csv_filename = f"data_{now_str}.csv"
        csv_path = os.path.join(LOG_DIR, csv_filename)

        if last_date != now_str:
            if not os.path.exists(csv_path):
                with open(csv_path, "w", newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(CSV_HEADER)
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
                    timestamp = datetime.now().isoformat()
                    row = [timestamp] + [latest_data.get(k, "") for k in CSV_HEADER[1:]]
                    try:
                        with open(csv_path, "a", newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow(row)
                        last_saved = latest_data.copy()
                    except Exception as e:
                        print(f"[CSV] Write failed: {e}")
        time.sleep(3)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/logs")
def list_logs():
    try:
        files = sorted(f for f in os.listdir(LOG_DIR) if f.endswith(".csv"))
        return render_template("logs.html", files=files)
    except Exception as e:
        return f"Error listing logs: {e}", 500

@app.route("/logs/<filename>")
def view_log(filename):
    filepath = os.path.join(LOG_DIR, filename)
    if not os.path.exists(filepath):
        abort(404)
    try:
        with open(filepath, newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        return render_template("view_log.html", filename=filename, rows=rows)
    except Exception as e:
        return f"Error reading {filename}: {e}", 500

@app.route("/latest-data")
def get_latest_data():
    try:
        now_str = datetime.now().strftime("%Y-%m-%d")
        csv_filename = f"data_{now_str}.csv"
        csv_path = os.path.join(LOG_DIR, csv_filename)
        if not os.path.exists(csv_path):
            return jsonify([])
        with open(csv_path, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)[-30:]
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/all-data")
def all_data():
    try:
        now_str = datetime.now().strftime("%Y-%m-%d")
        csv_filename = f"data_{now_str}.csv"
        csv_path = os.path.join(LOG_DIR, csv_filename)
        if not os.path.exists(csv_path):
            return jsonify([])
        with open(csv_path, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===== 管理画面 =====
@app.route("/admin", methods=["GET"])
def admin():
    try:
        files = sorted(f for f in os.listdir(LOG_DIR) if f.endswith(".csv"))
        return render_template("admin.html", files=files)
    except Exception as e:
        flash(f"ファイル一覧の取得に失敗: {e}", "danger")
        return render_template("admin.html", files=[]), 500

def _parse_iso(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M")
        except Exception as e:
            raise ValueError(f"時刻の解析に失敗しました: {ts}") from e

@app.route("/admin/data")
def admin_data():
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"error": "filename is required"}), 400
    target = os.path.join(LOG_DIR, filename)
    if not os.path.exists(target):
        return jsonify({"error": "file not found"}), 404

    try:
        with open(target, newline='') as f:
            rdr = csv.reader(f)
            rows = list(rdr)
        if not rows:
            return jsonify({"header": [], "rows": [], "min_ts": None, "max_ts": None})

        header = rows[0]
        data_rows = rows[1:]
        # min/max ts
        ts_values = []
        for r in data_rows:
            try:
                ts_values.append(datetime.fromisoformat(r[0]))
            except Exception:
                pass
        min_ts = min(ts_values).isoformat() if ts_values else None
        max_ts = max(ts_values).isoformat() if ts_values else None

        return jsonify({
            "header": header,
            "rows": data_rows,
            "min_ts": min_ts,
            "max_ts": max_ts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/delete", methods=["POST"])
def delete_range():
    filename = request.form.get("filename")
    start_s = request.form.get("start")
    end_s = request.form.get("end")
    do_backup = request.form.get("backup") == "1"

    if not filename or not start_s or not end_s:
        flash("必須項目が未入力です。", "warning")
        return redirect(url_for("admin"))

    try:
        start_dt = _parse_iso(start_s)
        end_dt = _parse_iso(end_s)
        if end_dt < start_dt:
            raise ValueError("終了時刻が開始時刻より前です。")
    except Exception as e:
        flash(f"時刻の形式が不正です: {e}", "danger")
        return redirect(url_for("admin"))

    target = os.path.join(LOG_DIR, filename)
    if not os.path.exists(target):
        flash("対象ファイルが存在しません。", "danger")
        return redirect(url_for("admin"))

    kept, dropped = 0, 0
    try:
        with open(target, newline='') as f:
            rdr = csv.reader(f)
            rows = list(rdr)

        if not rows:
            flash("対象ファイルは空でした。", "info")
            return redirect(url_for("admin"))

        header = rows[0]
        filtered = [header]

        for row in rows[1:]:
            ts_s = row[0] if row else ""
            try:
                ts = datetime.fromisoformat(ts_s)
            except Exception:
                filtered.append(row); kept += 1; continue

            if start_dt <= ts <= end_dt:
                dropped += 1
            else:
                filtered.append(row); kept += 1

        if do_backup:
            bak_name = f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            shutil.copy2(target, os.path.join(LOG_DIR, bak_name))

        fd, tmp_path = tempfile.mkstemp(prefix="tmp_", suffix=".csv", dir=LOG_DIR)
        os.close(fd)
        with open(tmp_path, "w", newline='') as wf:
            w = csv.writer(wf)
            w.writerows(filtered)
        os.replace(tmp_path, target)

        flash(f"削除完了: {dropped} 行を削除、{kept} 行を保持（{filename}）。", "success")
    except Exception as e:
        flash(f"削除処理でエラー: {e}", "danger")

    return redirect(url_for("admin"))

@app.route("/admin/delete-rows", methods=["POST"])
def delete_rows():
    data = request.get_json(force=True, silent=True) or {}
    filename = data.get("filename")
    indices = data.get("indices", [])
    if not filename or not isinstance(indices, list):
        return jsonify({"error": "filename and indices are required"}), 400

    target = os.path.join(LOG_DIR, filename)
    if not os.path.exists(target):
        return jsonify({"error": "file not found"}), 404

    try:
        with open(target, newline='') as f:
            rows = list(csv.reader(f))
        if not rows:
            return jsonify({"deleted": 0, "kept": 0})

        header = rows[0]
        body = rows[1:]

        # Build set for faster lookup
        to_delete = set(int(i) for i in indices if isinstance(i, int) or str(i).isdigit())

        filtered = [header]
        kept = 0
        deleted = 0
        for idx, r in enumerate(body):
            if idx in to_delete:
                deleted += 1
            else:
                filtered.append(r); kept += 1

        # backup
        bak_name = f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        shutil.copy2(target, os.path.join(LOG_DIR, bak_name))

        fd, tmp_path = tempfile.mkstemp(prefix="tmp_", suffix=".csv", dir=LOG_DIR)
        os.close(fd)
        with open(tmp_path, "w", newline='') as wf:
            w = csv.writer(wf)
            w.writerows(filtered)
        os.replace(tmp_path, target)

        return jsonify({"deleted": deleted, "kept": kept})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    threading.Thread(target=udp_listener, daemon=True).start()
    threading.Thread(target=emit_loop, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000)
