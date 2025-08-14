import os, csv, shutil, tempfile
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.config import LOG_DIR
from app.utils.parse import time_parse as _time_parse

bp = Blueprint("admin", __name__)

@bp.route("/admin", methods=["GET"])
def admin():
    try:
        files = sorted(f for f in os.listdir(LOG_DIR) if f.endswith(".csv"))
        return render_template("admin.html", files=files)
    except Exception as e:
        flash(f"ファイル一覧の取得に失敗: {e}", "danger")
        return render_template("admin.html", files=[]), 500

@bp.route("/admin/data")
def admin_data():
    filename = request.args.get("filename")
    if not filename: return jsonify({"error":"filename is required"}), 400
    target = os.path.join(LOG_DIR, filename)
    if not os.path.exists(target): return jsonify({"error":"file not found"}), 404
    try:
        with open(target, newline="") as f:
            rows = list(csv.reader(f))
        if not rows: return jsonify({"header": [], "rows": [], "min_ts": None, "max_ts": None})
        header, data_rows = rows[0], rows[1:]
        ts_vals = []
        for r in data_rows:
            try: ts_vals.append(datetime.fromisoformat(r[0]))
            except Exception: pass
        min_ts = min(ts_vals).isoformat() if ts_vals else None
        max_ts = max(ts_vals).isoformat() if ts_vals else None
        return jsonify({"header": header, "rows": data_rows, "min_ts": min_ts, "max_ts": max_ts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/admin/delete", methods=["POST"])
def delete_range():
    filename = request.form.get("filename")
    start_s = request.form.get("start")
    end_s   = request.form.get("end")
    do_backup = request.form.get("backup") == "1"
    if not filename or not start_s or not end_s:
        flash("必須項目が未入力です。", "warning"); return redirect(url_for("admin.admin"))

    try:
        start_dt = _time_parse(start_s)
        end_dt   = _time_parse(end_s)
        if end_dt < start_dt: raise ValueError("終了時刻が開始時刻より前です。")
    except Exception as e:
        flash(f"時刻の形式が不正です: {e}", "danger"); return redirect(url_for("admin.admin"))

    target = os.path.join(LOG_DIR, filename)
    if not os.path.exists(target):
        flash("対象ファイルが存在しません。", "danger"); return redirect(url_for("admin.admin"))

    kept = dropped = 0
    try:
        with open(target, newline="") as f:
            rows = list(csv.reader(f))
        if not rows:
            flash("対象ファイルは空でした。", "info"); return redirect(url_for("admin.admin"))
        header, filtered = rows[0], [rows[0]]
        for row in rows[1:]:
            ts_s = row[0] if row else ""
            try: ts = datetime.fromisoformat(ts_s)
            except Exception:
                filtered.append(row); kept += 1; continue
            if start_dt <= ts <= end_dt: dropped += 1
            else: filtered.append(row); kept += 1

        if do_backup:
            bak = f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            shutil.copy2(target, os.path.join(LOG_DIR, bak))

        fd, tmp = tempfile.mkstemp(prefix="tmp_", suffix=".csv", dir=LOG_DIR)
        os.close(fd)
        with open(tmp, "w", newline="") as wf:
            csv.writer(wf).writerows(filtered)
        os.replace(tmp, target)
        flash(f"削除完了: {dropped} 行を削除、{kept} 行を保持（{filename}）。", "success")
    except Exception as e:
        flash(f"削除処理でエラー: {e}", "danger")

    return redirect(url_for("admin.admin"))

@bp.route("/admin/delete-rows", methods=["POST"])
def delete_rows():
    data = request.get_json(force=True, silent=True) or {}
    filename = data.get("filename"); indices = data.get("indices", [])
    if not filename or not isinstance(indices, list):
        return jsonify({"error": "filename and indices are required"}), 400
    target = os.path.join(LOG_DIR, filename)
    if not os.path.exists(target): return jsonify({"error":"file not found"}), 404
    try:
        with open(target, newline="") as f:
            rows = list(csv.reader(f))
        if not rows: return jsonify({"deleted": 0, "kept": 0})
        header, body = rows[0], rows[1:]
        to_delete = set(int(i) for i in indices if isinstance(i, int) or str(i).isdigit())
        filtered = [header]; kept = deleted = 0
        for idx, r in enumerate(body):
            if idx in to_delete: deleted += 1
            else: filtered.append(r); kept += 1
        bak = f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        shutil.copy2(target, os.path.join(LOG_DIR, bak))
        fd, tmp = tempfile.mkstemp(prefix="tmp_", suffix=".csv", dir=LOG_DIR)
        os.close(fd)
        with open(tmp, "w", newline="") as wf:
            csv.writer(wf).writerows(filtered)
        os.replace(tmp, target)
        return jsonify({"deleted": deleted, "kept": kept})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
