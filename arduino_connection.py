import serial, time

ser = serial.Serial("/dev/tty.usbserial-A50285BI", 115200, timeout=1)
time.sleep(2)
ser.reset_input_buffer()

while True:
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    if not line:
        continue
    print(line)  # raw
    # parse "id,raw,percent"
    parts = [p.strip() for p in line.split(",")]
    if len(parts) == 3 and parts[0].lower() != "id":
        sid, raw_s, pct_s = parts
        try:
            raw = int(raw_s); pct = int(float(pct_s))
            print(f"Parsed -> id={sid} raw={raw} pct={pct}")
        except ValueError:
            pass  # ignore malformed lines
