import argparse
from pathlib import Path
import json
import subprocess
from PIL import Image
import imagehash
import io
import os
from datetime import datetime
from tqdm import tqdm
from functools import cached_property
import shutil

# https://stackoverflow.com/questions/52736154/how-to-check-similarity-of-two-images-that-have-different-pixelization

MIN_LENGTH = 20
HAMMING_DISTANCE=20

hash_method = imagehash.phash

concat = Path.cwd() / 'concat.txt'

parser = argparse.ArgumentParser()
parser.add_argument("search_dir")
parser.add_argument("--out-dir", default="")
parser.add_argument("--dry-run", action='store_true')
parser.add_argument("--mv", action='store_true')

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

def extract_image(video: Path, when: float) -> Image:
    result = subprocess.check_output([
        'ffmpeg',
        '-i', str(video),
        '-ss', str(when),
        '-vframes', '1',
        '-c:v', 'png',
        '-f', 'image2pipe',
        '-'
    ], stderr=subprocess.DEVNULL)

    return Image.open(io.BytesIO(result))

class InputFile:
    def __init__(self, path: Path):
        self.path = path
        self.duration = float(ffprobe(path)[0]['duration'])
        self.ripped_time = datetime.fromtimestamp(os.path.getmtime(path))
        self.recorded_time = datetime.strptime(path.name.split('.')[-3], '%y-%m-%d_%H-%M-%S')

    @cached_property
    def start_img_hash(self):
        image = extract_image(self.path, 0)
        return hash_method(image)

    @cached_property
    def end_img_hash(self):
        image = extract_image(self.path, max(self.duration-0.0334, 0))
        return hash_method(image)


indir = Path(args.search_dir)
if not indir.is_dir():
    print("Invalid search_dir")
    exit(1)

if args.out_dir:
    outdir = Path(args.out_dir)
else:
    outdir = indir / 'out'

if not outdir.is_dir():
    if outdir.is_file():
        print("Invalid out_dir")
        exit(1)

    outdir.mkdir()

files = [InputFile(f) for f in tqdm(list(indir.glob("*.avi")), desc='Find sources')]
files.sort(key=lambda f: f.ripped_time)

joins = []
curr_join = []

def print_join(join):
    for i, item in enumerate(join):
        if i == 0:
            print(f"ROOT {item.path.name} ({item.duration}s)")
        elif i == len(join)-1:
            print(f"  '- {item.path.name} ({item.duration}s)")
        else:
            print(f"  |- {item.path.name} ({item.duration}s)")

for idx, curr in enumerate(tqdm(files, desc='Calculate joins')):
    if len(curr_join) > 0 and curr_join[-1] == curr:
        continue

    if idx > 0:
        prev = files[idx-1]

        if curr.duration > MIN_LENGTH and prev.duration > MIN_LENGTH:
            if len(curr_join) > 0:
                joins.append(curr_join)
                curr_join = []

        distance = abs(prev.end_img_hash - curr.start_img_hash)
        if distance < HAMMING_DISTANCE:
            if len(curr_join) == 0:
                curr_join = [prev]
            curr_join.append(curr)
            continue

    if len(curr_join) > 0:
        joins.append(curr_join)
        curr_join = []

    if idx < len(files)-1:
        next = files[idx+1]

        distance = abs(curr.end_img_hash - next.start_img_hash)
        if distance < HAMMING_DISTANCE:
            curr_join = [curr, next]
            continue

    joins.append([curr])

if len(curr_join) > 0:
    joins.append(curr_join)

for i, join in enumerate(joins):
    print(f"\x1b[92m({i:03d}/{len(joins):03d})\x1b[37m")
    print_join(join)
    if args.dry_run:
        print()
        continue

    if len(join) == 1:
        outfile = outdir / join[0].path.name
        assert not outfile.exists()
        if args.mv:
            join[0].path.rename(outfile)
        else:
            shutil.copyfile(join[0].path, outfile)
    else:
        outfile = None
        for item in join:
            if item.duration >= MIN_LENGTH:
                outfile = outdir / item.path.name
                break
        if outfile is None:
            outfile = outdir / join[0].path.name
            print(f"Unsure outfile: {outfile}\n")
        with concat.open('w') as cf:
            for item in join:
                cf.write(f"file '{item.path.resolve()}'\n")
        subprocess.check_call([
            'ffmpeg',
            '-v', 'warning',
            '-stats',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat.resolve()),
            '-c', 'copy',
            str(outfile)
        ])
        concat.unlink()

    print()

in_index = indir / 'index.txt'
out_index = outdir / 'index.txt'
if in_index.is_file():
    shutil.copyfile(in_index, out_index)

print("Done!")
