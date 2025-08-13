from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from app.config import SOFTAP_IP, CTL_UDP_PORT, CTRL_PORT
from app.services.provisioning import (
    DESIRED, provision_state, save_desired_to_csv, send_desired_to_softap
)

bp = Blueprint("provisioning", __name__)

@bp.route("/provisioning")
def provisioning():
    rows = []
    for mac, st in provision_state.items():
        lr = st.get("last_report", {})
        rows.append({
            "mac": mac,
            "ssid": lr.get("ssid","-"),
            "uaddr": lr.get("udpAddr","-"),
            "udpPort": lr.get("udpPort","-"),
            "soil": lr.get("soil","-"),
            "pump_ms": lr.get("pump_ms","-"),
            "init_ms": lr.get("init_ms","-"),
            "dsw_ms": lr.get("dsw_ms","-"),
            "sleep_s": lr.get("sleep_s","-"),
            "last_report_time": datetime.fromtimestamp(st.get("last_report_time")).strftime("%Y-%m-%d %H:%M:%S") if st.get("last_report_time") else "-",
            "last_push_time":   datetime.fromtimestamp(st.get("last_push_time")).strftime("%Y-%m-%d %H:%M:%S") if st.get("last_push_time") else "-",
            "push_ok": st.get("push_ok"),
            "diff": st.get("diff", {}),
        })
    rows.sort(key=lambda r: r["last_report_time"] or 0, reverse=True)
    return render_template("provisioning.html", rows=rows, desired=DESIRED, CTL_UDP_PORT=CTL_UDP_PORT, ap_ip=SOFTAP_IP)

@bp.route("/api/provisioning")
def api_provisioning():
    return jsonify({"desired": DESIRED, "devices": provision_state, "CTL_UDP_PORT": CTL_UDP_PORT, "ap_ip": SOFTAP_IP})

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
        flash(f"SoftAP {ap_ip}:{CTRL_PORT} に送信しました。", "success")
    else:
        flash(f"SoftAP {ap_ip}:{CTRL_PORT} への送信に失敗しました。", "danger")
    return redirect(url_for("provisioning.provisioning"))
