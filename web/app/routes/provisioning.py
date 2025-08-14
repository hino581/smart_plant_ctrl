from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from app.config import SOFTAP_IP, PRV_SND_RCV_UPORT, PRV_SND_RCV_UPORT
from app.services.provisioning import (
    DESIRED, provision_state, save_desired_to_csv, send_desired_to_softap
)

bp = Blueprint("provisioning", __name__)

@bp.route("/provisioning")
def provisioning():
    mac_q = request.args.get("mac")
    target_mac = None
    latest_ts = -1
    for mac, st in provision_state.items():
        ts = st.get("last_report_time") or -1
        if mac_q and mac == mac_q:
            target_mac = mac
            break
        if ts > latest_ts:
            latest_ts = ts
            target_mac = mac

    dev = provision_state.get(target_mac, {}) if target_mac else {}
    lr = dev.get("last_report", {})
    last_report_time = dev.get("last_report_time")

    # 表示用
    device_view = {
        "mac": lr.get("mac", "-"),
        "ap_ssid": lr.get("ap_ssid", "-"),
        "ap_ip": lr.get("ap_ip", "-"),
        "ssid": lr.get("ssid", "-"),
        "pass": lr.get("pass", "-"),
        "uaddr": lr.get("uaddr", lr.get("udpAddr", "-")),
        "uport": lr.get("uport", lr.get("udpPort", "-")),
        "soil": lr.get("soil", "-"),
        "pump_ms": lr.get("pump_ms", "-"),
        "init_ms": lr.get("init_ms", "-"),
        "dsw_ms": lr.get("dsw_ms", "-"),
        "sleep_s": lr.get("sleep_s", "-"),
        "last_report_time": datetime.fromtimestamp(last_report_time).strftime("%Y-%m-%d %H:%M:%S") if last_report_time else "-",
    }

    # 端に一覧も出せるよう、簡単なソート済みリスト
    rows = []
    for mac, st in provision_state.items():
        t = st.get("last_report_time")
        rows.append({
            "mac": mac,
            "last_report_time": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S") if t else "-",
        })
    rows.sort(key=lambda r: r["last_report_time"], reverse=True)

    return render_template(
        "provisioning.html",
        desired=DESIRED,
        device=device_view,
        devices=rows,
        PRV_SND_RCV_UPORT=PRV_SND_RCV_UPORT
    )

@bp.route("/api/provisioning")
def api_provisioning():
    return jsonify({"desired": DESIRED, "devices": provision_state, "PRV_SND_RCV_UPORT": PRV_SND_RCV_UPORT, "ap_ip": SOFTAP_IP})

@bp.route("/provisioning/update", methods=["POST"])
def provisioning_update():
    try:
        form = request.form
        from app.config import DESIRED_FIELDS
        for k, caster in DESIRED_FIELDS.items():
            if k in form:
                raw = form.get(k, "")
                if caster is int and (raw is None or raw == ""):
                    continue
                try:
                    DESIRED[k] = caster(raw)
                except Exception:
                    flash(f"{k} の値が不正です: {raw}", "danger")
                    return redirect(url_for("provisioning.provisioning"))
        save_desired_to_csv()
        flash("Desired設定を保存しました（次回から自動プッシュ対象）。", "success")
    except Exception as e:
        flash(f"保存に失敗: {e}", "danger")
    return redirect(url_for("provisioning.provisioning"))

@bp.route("/provisioning/push", methods=["POST"])
def provisioning_push():
    ap_ip = request.form.get("ap_ip", SOFTAP_IP)
    ok = send_desired_to_softap(ap_ip)
    if ok:
        flash(f"SoftAP {ap_ip}:{PRV_SND_RCV_UPORT} に送信しました。", "success")
    else:
        flash(f"SoftAP {ap_ip}:{PRV_SND_RCV_UPORT} への送信に失敗しました。", "danger")
    return redirect(url_for("provisioning.provisioning"))

@bp.route("/provisioning/save-selected", methods=["POST"])
def provisioning_save_selected():
    form = request.form
    saved = {}

    def pick(key, caster=str):
        if form.get(f"send_{key}") == "1":
            val = form.get(key, "")
            if caster is int and val != "":
                try:
                    val = int(val)
                except Exception:
                    flash(f"{key} の数値が不正です: {val}", "warning")
                    return
            saved[key] = val

    pick("ssid", str)
    pick("pass", str)
    pick("uaddr", str)
    pick("uport", int)
    pick("soil", int)
    pick("pump_ms", int)
    pick("init_ms", int)
    pick("dsw_ms", int)
    pick("sleep_s", int)

    for k, v in saved.items():
        DESIRED[k] = v
    save_desired_to_csv()
    flash(f"選択した {len(saved)} 件を保存しました。", "success")
    return redirect(url_for("provisioning.provisioning"))