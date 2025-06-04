import subprocess
import re
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import time

CHANNELS_24 = list(range(1, 14))
CHANNELS_5 = [36, 40, 44, 48, 149, 153, 157, 161, 165]
ALL_CHANNELS = sorted(set(CHANNELS_24 + CHANNELS_5))

scanning = False
channel_details = {}

def parse_netsh_output():
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            encoding="cp866",  # Русская кодировка
            errors="ignore"
        )
    except subprocess.CalledProcessError:
        return {}, {}

    usage = {}
    details = {}

    networks = output.split("SSID ")
    for net in networks[1:]:
        ssid_match = re.search(r":\s*(.+)", net.splitlines()[0])
        ssid = ssid_match.group(1).strip() if ssid_match else "Unknown"
        channel_matches = re.findall(r"(?:Канал|Channel)\s*:\s*(\d+)", net)
        for ch_str in channel_matches:
            ch = int(ch_str)
            usage[ch] = usage.get(ch, 0) + 1
            if ch not in details:
                details[ch] = []
            if ssid not in details[ch]:
                details[ch].append(ssid)
    return usage, details

def plot_usage(channel_usage, details, band_filter):
    if band_filter == "2.4":
        channels = CHANNELS_24
    elif band_filter == "5":
        channels = CHANNELS_5
    else:
        channels = ALL_CHANNELS

    usage = [channel_usage.get(ch, 0) for ch in channels]
    max_usage = max(usage) if usage else 1
    usage_percent = [int((u / max_usage) * 100) if max_usage > 0 else 0 for u in usage]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar([str(c) for c in channels], usage_percent, color='skyblue')
    ax.set_title("Загруженность Wi-Fi каналов")
    ax.set_ylabel("Загруженность (%)")
    ax.set_xlabel("Каналы")
    ax.set_ylim(0, 100)
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)

    for bar, percent, ch in zip(bars, usage_percent, channels):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{percent}%\n({channel_usage.get(ch, 0)})", ha='center', va='bottom')

    return fig

def update_scan():
    global channel_details
    usage, details = parse_netsh_output()
    channel_details = details
    fig = plot_usage(usage, details, band_var.get())

    for widget in plot_frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    text_output.delete(1.0, tk.END)
    for ch in sorted(details):
        if (band_var.get() == "2.4" and ch not in CHANNELS_24) or \
           (band_var.get() == "5" and ch not in CHANNELS_5):
            continue
        ssids = ", ".join(details[ch])
        text_output.insert(tk.END, f"Канал {ch} — {len(details[ch])} точек: {ssids}\n")

def scan_loop():
    global scanning
    scan_duration = int(duration_entry.get())
    interval = int(interval_entry.get())
    start_time = time.time()

    def loop_step():
        nonlocal start_time
        if not scanning or (time.time() - start_time >= scan_duration):
            return
        update_scan()
        root.after(interval * 1000, loop_step)

    root.after(0, loop_step)

def start_scan():
    global scanning
    if scanning:
        return
    scanning = True
    scan_loop()

def stop_scan():
    global scanning
    scanning = False

# ---------------- GUI ------------------

root = tk.Tk()
root.title("Wi-FiChannelScanner")

# Верхняя панель
control_frame = ttk.Frame(root, padding=10)
control_frame.pack(fill=tk.X)

ttk.Label(control_frame, text="Диапазон:").pack(side=tk.LEFT)
band_var = tk.StringVar(value="all")
ttk.OptionMenu(control_frame, band_var, "all", "2.4", "5", "all").pack(side=tk.LEFT, padx=5)

ttk.Label(control_frame, text="Сканировать секунд:").pack(side=tk.LEFT)
duration_entry = ttk.Entry(control_frame, width=5)
duration_entry.insert(0, "30")
duration_entry.pack(side=tk.LEFT)

ttk.Label(control_frame, text="Интервал обновления (сек):").pack(side=tk.LEFT)
interval_entry = ttk.Entry(control_frame, width=5)
interval_entry.insert(0, "5")
interval_entry.pack(side=tk.LEFT)

ttk.Button(control_frame, text="Старт", command=start_scan).pack(side=tk.LEFT, padx=10)
ttk.Button(control_frame, text="Стоп", command=stop_scan).pack(side=tk.LEFT)

# График
plot_frame = ttk.Frame(root)
plot_frame.pack(fill=tk.BOTH, expand=True)

# Текстовый вывод
text_output = tk.Text(root, height=10, wrap=tk.WORD)
text_output.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

root.mainloop()
