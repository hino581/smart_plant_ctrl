import os

UDP_IP = "0.0.0.0"
UDP_PORT = int(os.environ.get("SENSOR_UDP_PORT", "12345"))
DISCONNECT_TIMEOUT = 600 + 5
LOG_DIR = "log"
CSV_HEADER = ["timestamp","Temp","Hum","Pres","Light","Soil","Bus","Current","Power"]

CFG_UDP_PORT = int(os.environ.get("CFG_UDP_PORT", "12346"))
CTL_UDP_PORT = int(os.environ.get("CTL_UDP_PORT", "12346"))
SOFTAP_IP    = os.environ.get("SOFTAP_IP", "192.168.4.1")
SEND_TIMEOUT = float(os.environ.get("SEND_TIMEOUT", "1.5"))

# UI文言で使っていた未定義名の対策（表示だけの別名・挙動不変）
CTRL_PORT = CTL_UDP_PORT

# Desired 既定値
DESIRED_DEFAULTS = {
    "soil":    int(os.environ.get("DESIRED_SOIL", "650")),
    "pump_ms": int(os.environ.get("DESIRED_PUMP_MS", "5000")),
    "init_ms": int(os.environ.get("DESIRED_INIT_MS", "2000")),
    "dsw_ms":  int(os.environ.get("DESIRED_DSW_MS", "1000")),
    "sleep_s": int(os.environ.get("DESIRED_SLEEP_S", "600")),
    "ssid":    os.environ.get("DESIRED_SSID", "YourSSID"),
    "pass":    os.environ.get("DESIRED_PASS", "YourPASS"),
    "uaddr":   os.environ.get("DESIRED_UADDR", "192.168.0.10"),
    "uport":   int(os.environ.get("DESIRED_UPORT", "12345")),
    "key":     os.environ.get("DESIRED_PSK", "plant-psk"),
}

DESIRED_CSV = os.path.join(LOG_DIR, "desired_config.csv")
DESIRED_FIELDS = {
    "ssid": str, "pass": str, "uaddr": str, "uport": int,
    "soil": int, "pump_ms": int, "init_ms": int, "dsw_ms": int, "sleep_s": int, "key": str,
}
