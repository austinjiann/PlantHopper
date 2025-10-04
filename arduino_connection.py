import serial, time

PORT = "/dev/tty.usbserial-A50285BI"
BAUD = 115200

def parse_kv_line(line: str):
    """
    Parse lines like:
      cmd:MOISTURE;id:sensor_1;percent:61.2
    Returns a dict, e.g. {"cmd":"MOISTURE","id":"sensor_1","percent":"61.2"}
    """
    parts = [p.strip() for p in line.split(";") if p.strip()]
    kv = {}
    for p in parts:
        if ":" in p:
            k, v = p.split(":", 1)
            kv[k.strip().lower()] = v.strip()
    return kv

if __name__ == "__main__":
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()

    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            continue

        # Always show the raw line for debugging
        print(line)

        kv = parse_kv_line(line)
        if not kv:
            continue

        # Only handle moisture messages
        if kv.get("cmd", "").upper() != "MOISTURE":
            continue

        sid = kv.get("id", "")
        pct_s = kv.get("percent", "")

        if not sid or not pct_s:
            # Missing expected fields—skip
            continue

        try:
            pct = float(pct_s)
            pct_int = int(round(pct))
            print(f"Parsed -> id={sid} percent={pct:.1f}% ({pct_int}%)")
        except ValueError:
            # percent not a number—skip
            continue
