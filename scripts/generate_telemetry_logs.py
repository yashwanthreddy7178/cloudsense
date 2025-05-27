# generate_telemetry_logs.py

import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import os
from tqdm import tqdm

fake = Faker()
np.random.seed(42)

# Parameters
NUM_VMS = 500
DAYS = 7
INTERVAL_MINUTES = 5
LOGS_PER_DAY = int(24 * 60 / INTERVAL_MINUTES)
TOTAL_LOGS = NUM_VMS * LOGS_PER_DAY * DAYS

VM_TYPES = ["general_purpose", "compute_optimized", "memory_optimized"]

def generate_logs():
    data = []
    start_time = datetime.now() - timedelta(days=DAYS)

    print(f"Generating {TOTAL_LOGS:,} telemetry records...")

    for vm_id in tqdm(range(NUM_VMS)):
        vm_label = f"vm_{vm_id:04d}"
        vm_type = np.random.choice(VM_TYPES)

        time = start_time
        for _ in range(LOGS_PER_DAY * DAYS):
            cpu = np.clip(np.random.normal(0.5, 0.15), 0, 1)
            mem = np.clip(np.random.normal(0.5, 0.2), 0, 1)
            disk_io = int(np.random.exponential(100))
            net_io = int(np.random.exponential(300))
            processes = np.random.randint(50, 200)

            # Label: 1 = risk of exhaustion
            label = int(cpu > 0.9 or mem > 0.9 or processes > 180)

            data.append([
                time.isoformat(),
                vm_label,
                cpu,
                mem,
                disk_io,
                net_io,
                processes,
                vm_type,
                label
            ])

            time += timedelta(minutes=INTERVAL_MINUTES)

    df = pd.DataFrame(data, columns=[
        "timestamp", "vm_id", "cpu_util", "mem_util", "disk_io",
        "net_io", "active_processes", "vm_type", "label_exhausted"
    ])

    os.makedirs("data/raw_telemetry_logs", exist_ok=True)
    df.to_csv("data/raw_telemetry_logs/telemetry_logs.csv", index=False)
    print("✅ Saved to data/raw_telemetry_logs/telemetry_logs.csv")

if __name__ == "__main__":
    generate_logs()
