import os, csv, json, socket, time, shutil, tempfile
from datetime import datetime
from threading import Thread
from typing import Dict, Any, Optional
from app.config import (
    PRV_SND_RCV_UPORT, PRV_SND_RCV_UPORT, SOFTAP_IP, SEND_TIMEOUT,
    DESIRED_DEFAULTS, DESIRED_CSV, DESIRED_FIELDS, LOG_DIR
)
from app.utils.parse import raw_text_parse

DESIRED: Dict[str, Any] = dict(DESIRED_DEFAULTS)   # 実体
provision_state: Dict[str, Dict[str, Any]] = {}

def send_desired_to_softap(ap_ip: str = SOFTAP_IP) -> bool:
    payload = {
        "ssid": DESIRED["ssid"], "pass": DESIRED["pass"],
        "uaddr": DESIRED["uaddr"], "uport": DESIRED["uport"],
        "soil": DESIRED["soil"], "pump_ms": DESIRED["pump_ms"],
        "init_ms": DESIRED["init_ms"], "dsw_ms": DESIRED["dsw_ms"],
        "sleep_s": DESIRED["sleep_s"],
    }
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(SEND_TIMEOUT)
        s.sendto(json.dumps(payload).encode("utf-8"), (ap_ip, PRV_SND_RCV_UPORT))
        print(f"[PRV->AP] Sent to {ap_ip}:{PRV_SND_RCV_UPORT} payload={payload}")
        return True
    except Exception as e:
        print(f"[PRV->AP] Send failed: {e}")
        return False

def config_listener_and_push():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PRV_SND_RCV_UPORT))
    print(f"[PRV] Listening on {PRV_SND_RCV_UPORT} ...")
    while True:
        data, addr = sock.recvfrom(2048)
        now = time.time()
        try:
            d = json.loads(data.decode("utf-8").strip())
            mac = d.get("mac", SOFTAP_IP)
            provision_state.setdefault(mac, {})
            provision_state[mac]["last_report"] = d
            provision_state[mac]["last_report_time"] = now
            print(f"[PRV] Announce from {mac} @ {addr}: {d}")

            ap_ip = d.get("ap_ip", SOFTAP_IP)
            ok = send_desired_to_softap(ap_ip)
            provision_state[mac]["push_ok"] = bool(ok)
            print(f"[PRV] Push to SoftAP {ap_ip}:{PRV_SND_RCV_UPORT} -> {'OK' if ok else 'NG'}")
        except Exception as e:
            print(f"[PRV] Parse error Data: {data}")
            print(f"[PRV] Parse error: {e}")

def load_desired_from_csv(path: str = DESIRED_CSV):
    try:
        if not os.path.exists(path):
            return
        with open(path, newline="", encoding="utf-8") as f:
            for k, v in csv.reader(f):
                if k in DESIRED_FIELDS:
                    caster = DESIRED_FIELDS[k]
                    try:
                        DESIRED[k] = caster(v)
                    except Exception:
                        pass
        print(f"[DESIRED] loaded from {path}")
    except Exception as e:
        print(f"[DESIRED] load failed: {e}")

def save_desired_to_csv(path: str = DESIRED_CSV):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for k in DESIRED_FIELDS.keys():
                w.writerow([k, DESIRED.get(k, "")])
        print(f"[DESIRED] saved to {path}")
    except Exception as e:
        print(f"[DESIRED] save failed: {e}")

def start_provisioning_listener():
    Thread(target=config_listener_and_push, daemon=True).start()
