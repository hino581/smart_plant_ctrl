import os, csv, json, socket, time, shutil, tempfile
from datetime import datetime
from threading import Thread
from typing import Dict, Any
from app.config import (
    CFG_UDP_PORT, CTL_UDP_PORT, SOFTAP_IP, SEND_TIMEOUT,
    DESIRED_DEFAULTS, DESIRED_CSV, DESIRED_FIELDS, LOG_DIR
)

DESIRED: Dict[str, Any] = dict(DESIRED_DEFAULTS)   # 実体
provision_state: Dict[str, Dict[str, Any]] = {}

def send_desired_to_softap(ap_ip: str = SOFTAP_IP) -> bool:
    payload = {
        "key": DESIRED["key"], "ssid": DESIRED["ssid"], "pass": DESIRED["pass"],
        "uaddr": DESIRED["uaddr"], "uport": DESIRED["uport"],
        "soil": DESIRED["soil"], "pump_ms": DESIRED["pump_ms"],
        "init_ms": DESIRED["init_ms"], "dsw_ms": DESIRED["dsw_ms"],
        "sleep_s": DESIRED["sleep_s"],
    }
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(SEND_TIMEOUT)
        s.sendto(json.dumps(payload).encode("utf-8"), (ap_ip, CTL_UDP_PORT))
        print(f"[CFG->AP] Sent desired to {ap_ip}:{CTL_UDP_PORT}")
        return True
    except Exception as e:
        print(f"[CFG->AP] Send failed: {e}")
        return False

def config_listener_and_push():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", CFG_UDP_PORT))
    print(f"[CFG] Listening on {CFG_UDP_PORT} ...")
    while True:
        data, addr = sock.recvfrom(2048)
        now = time.time()
        try:
            d = json.loads(data.decode("utf-8").strip())
            mac = addr[0]  # 送信元IPを暫定MACキーに
            st = provision_state.setdefault(mac, {})
            st["last_report"] = d
            st["last_report_time"] = now
            print(f"[CFG] Announce from {mac} @ {addr}: {d}")

            ap_ip = d.get("ap_ip", SOFTAP_IP)
            ok = send_desired_to_softap(ap_ip)
            st["last_push_time"] = now
            st["push_ok"] = bool(ok)
            print(f"[CFG] Push to SoftAP {ap_ip}:{CTL_UDP_PORT} -> {'OK' if ok else 'NG'}")
        except Exception as e:
            print(f"[CFG] Parse error: {e}")

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
