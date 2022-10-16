import subprocess
import sys
import time
import argparse
import shutil
from datetime import datetime
import os

from pathlib import Path

NUM_WORKERS = 4
POLL_DELAY = 1
DEST_PATH = R"\\192.168.1.204\Public\Shared Videos"

parser = argparse.ArgumentParser()
parser.add_argument('input_dir')
parser.add_argument('--intermediate-dir', default='')
parser.add_argument('--done-dir', default='')

args = parser.parse_args()

input_dir = Path(args.input_dir)
if not input_dir.is_dir():
    print('Invalid input_dir!')
    exit(1)

if args.intermediate_dir:
    int_dir = Path(args.intermediate_dir)
else:
    int_dir = Path.cwd() / 'intermediates'

if args.done_dir:
    done_dir = Path(args.done_dir)
else:
    done_dir = Path.cwd() / 'done'

if int_dir.is_dir():
    shutil.rmtree(int_dir)
int_dir.mkdir()

if done_dir.is_dir():
    print("Done dir already exists!!")
    exit(1)
done_dir.mkdir()

files = list(input_dir.glob("*/*.avi"))

print(f"\x1b[92mCopy originals\x1b[37m")
cmd = [
    "robocopy",
    str(input_dir),
    DEST_PATH + '\\tapes_avi',
    "/j", "/s",
    "/mt:8",
    "/nc",
    "/compress"
]
completion = subprocess.run(cmd)
if completion.returncode >= 8:
    raise subprocess.CalledProcessError(completion.returncode, cmd)

for i, file in enumerate(files):
    print(f"\x1b[92m({i:03d}/{len(files):03d})\x1b[37m: {file.name}")
    subdir = file.parent
    if subdir != input_dir:
        assert subdir.parent == input_dir
        int_subdir = int_dir / subdir.name
        if not int_subdir.exists():
            int_subdir.mkdir()

        done_subdir = done_dir / subdir.name
        if not done_subdir.exists():
            done_subdir.mkdir()

        int_file = int_subdir / (file.stem + '.mp4')
        done_file = done_subdir / file.name
    else:
        int_file = int_dir / (file.stem + '.mp4')

    if int_file.exists():
        raise ValueError('Conflicting intermediate files!')

    record_date = file.name.split('.')[-3]
    record_date = datetime.strptime(record_date, '%y-%m-%d_%H-%M-%S')

    # TRANSCODE
    cmd = [
        'ffmpeg',
        '-v', 'warning',
        '-stats',
        '-i', str(file),
        '-filter:v', 'yadif=mode=1',
        '-pix_fmt', 'yuv420p',
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

    # UPLOAD
    cmd = [
        "robocopy",
        str(int_dir),
        DEST_PATH,
        "/j", "/s",
        "/nc",
        "/mov",
        "/compress"
    ]
    completion = subprocess.run(cmd)
    if completion.returncode >= 8:
        raise subprocess.CalledProcessError(completion.returncode, cmd)

    assert not int_file.exists()

    # MOVE
    assert not done_file.exists()
    file.rename(done_file)


