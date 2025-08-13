import os, csv
from datetime import datetime
from flask import Blueprint, render_template, jsonify, abort
from app.config import LOG_DIR

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/logs")
def list_logs():
    try:
        files = sorted(f for f in os.listdir(LOG_DIR) if f.endswith(".csv"))
        return render_template("logs.html", files=files)
    except Exception as e:
        return f"Error listing logs: {e}", 500

@bp.route("/logs/<filename>")
def view_log(filename):
    path = os.path.join(LOG_DIR, filename)
    if not os.path.exists(path): abort(404)
    try:
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        return render_template("view_log.html", filename=filename, rows=rows)
    except Exception as e:
        return f"Error reading {filename}: {e}", 500

@bp.route("/latest-data")
def latest_data():
    try:
        now_str = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(LOG_DIR, f"data_{now_str}.csv")
        if not os.path.exists(path): return jsonify([])
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))[-30:]
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/all-data")
def all_data():
    try:
        now_str = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(LOG_DIR, f"data_{now_str}.csv")
        if not os.path.exists(path): return jsonify([])
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
