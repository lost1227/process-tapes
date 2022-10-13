import argparse
from pathlib import Path
from datetime import datetime
import subprocess
import os

parser = argparse.ArgumentParser()

parser.add_argument('input_file')
parser.add_argument('destination')
parser.add_argument('--intermediate-dir', default='./intermediates')

args = parser.parse_args()

def set_title(title):
    subprocess.run(f'title {title}', shell=True)

input_file = Path(args.input_file).resolve()
if not input_file.is_file():
    print(f'No such file: "{input_file}"')
    exit(1)

int_dir = Path(args.intermediate_dir)
if not int_dir.is_dir():
    int_dir.mkdir()

int_file = int_dir / input_file.with_suffix('.mp4').name
if int_file.exists():
    int_file.unlink()

record_date = input_file.stem.split('.')[-2]
record_date = datetime.strptime(record_date, '%y-%m-%d_%H-%M')

set_title(f"TRANSCODE - {input_file.name}")

# TRANSCODE
cmd = [
    'ffmpeg',
    '-i', str(input_file),
    '-c:v', 'libx264',
    '-preset', 'slow',
    '-crf', '18',
    '-c:a', 'aac',
    '-b:a', '128k',
    '-metadata', f'date={record_date.strftime("%Y-%m-%d")}',
    str(int_file)
]
subprocess.run(cmd).check_returncode()

# SET TIME
os.utime(str(int_file), (record_date.timestamp(), record_date.timestamp()))

set_title(f"UPLOAD - {int_file.name}")
# Copy to remote
cmd = [
    "robocopy",
    str(int_dir),
    args.destination,
    "/mov",
    "/compress",
    int_file.name
]
completion = subprocess.run(cmd)
if completion.returncode >= 8:
    raise subprocess.CalledProcessError(completion.returncode, cmd)

assert not int_file.exists()
