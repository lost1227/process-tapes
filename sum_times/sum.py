import argparse
from pathlib import Path
import json
import subprocess
from tqdm import tqdm

import math

MIN_LENGTH = 20
HAMMING_DISTANCE=20

concat = Path.cwd() / 'concat.txt'

parser = argparse.ArgumentParser()
parser.add_argument("search_dir")

args = parser.parse_args()

def ffprobe(file: Path):
    result = subprocess.check_output([
        'ffprobe',
        '-v', 'quiet',
        '-show_streams',
        '-of', 'json',
        str(file)
    ])

    return json.loads(result)['streams']

indir = Path(args.search_dir)
if not indir.is_dir():
    print("Invalid search_dir")
    exit(1)

sum = 0
for file in tqdm(list(indir.glob("*.avi"))):
    duration = float(ffprobe(file)[0]['duration'])
    sum += duration

milliseconds, time = math.modf(sum)
time = int(time)
seconds = time % 60
time = time // 60
minutes = time % 60
time = time // 60
hours = time

milliseconds_str = '{:.4f}'.format(milliseconds).lstrip('0')
print(f"{hours:02d}:{minutes:02d}:{seconds:02d}{milliseconds_str}")
