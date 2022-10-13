import subprocess
import sys
import threading
import queue
import signal
import time

from pathlib import Path

NUM_WORKERS = 4
POLL_DELAY = 1
DEST_PATH = R"\\192.168.1.204\Public\Shared Videos\tapes\mp4_split"

input_dir = Path.cwd() / "input"
worker_file = Path(__file__).parent / "worker.py"

assert worker_file.exists()

if not input_dir.exists():
    input_dir.mkdir()

interrupted = False

emergency_escape = 3

def signal_handler(sig, frame):
    global interrupted, emergency_escape
    print("Interrupting jobs...")
    interrupted = True

    emergency_escape -= 1

    if emergency_escape == 0:
        sys.exit(1)

signal.signal(signal.SIGINT, signal_handler)

jobs = queue.SimpleQueue()

def run_worker():
    while True:
        if not interrupted:
            try:
                inpath = jobs.get(block=True, timeout=POLL_DELAY)
            except queue.Empty:
                continue
        else:
            try:
                inpath = jobs.get_nowait()
            except queue.Empty:
                return

        subprocess.run([sys.executable, str(worker_file), str(inpath), DEST_PATH], creationflags=subprocess.CREATE_NEW_CONSOLE).check_returncode()

        inpath.unlink()


workers = [threading.Thread(target=run_worker, name=f"Worker {i}") for i in range(NUM_WORKERS)]
for worker in workers:
    worker.start()

known_files = set()

last_size = 0

while not interrupted:
    for file in input_dir.glob("**/*.avi"):
        if file.name not in known_files:
            print(f"Discovered {file.name}")
            jobs.put(file)
            known_files.add(file.name)

    size = jobs.qsize()
    if (size > 0 or last_size > 0) and size != last_size:
        print(f"Pending jobs: {size}")
        last_size = size

    time.sleep(POLL_DELAY)

for worker in workers:
    print(f"Waiting for {worker.name}...", end='')
    sys.stdout.flush()
    worker.join()
    print("Done")

