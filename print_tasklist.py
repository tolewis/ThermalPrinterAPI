#!/usr/bin/env python3
"""Print a tight, highly readable Harper open-task list on 4x6 labels."""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict

from PIL import Image, ImageDraw, ImageFont
from config import TSPL_HEADER

HARPER_DAILY = "/home/tlewis/Documents/projects/30 Harper/10 Daily/2026/03-Mar"
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

FONT_TITLE = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 30)
FONT_SECTION = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 30)
FONT_TASK = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 28)
FONT_META = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 14)

PRINT_W = 864
PRINT_H = 1218
LAND_W = PRINT_H
LAND_H = PRINT_W
MARGIN_X = 42
MARGIN_Y = 54
CONTENT_W = LAND_W - (MARGIN_X * 2)
CONTENT_H = LAND_H - (MARGIN_Y * 2)
CATEGORY_ORDER = ['Admin', 'Meeting Hall', 'WHO', 'Fitness', 'Laundry', 'Other']
SKIP_PATTERNS = ['execute the 9:45', 'attend the 2:00', 'capture key outcomes']
STOP = {'i','to','and','or','the','a','an','of','for','in','on','at','by','with','from','into','over','under','&','-','_','re','be','is','are','was','were','it','this','that'}

@dataclass
class TaskRecord:
    key: str
    text: str
    category: str
    first_seen: str
    last_seen_open: str = ''
    open_dates: List[str] = field(default_factory=list)


def date_sort_key(fname: str):
    return datetime.strptime(fname.replace('.md', ''), '%d-%m-%Y')


def get_working_days(base_dir: str, n: int = 5) -> List[str]:
    files = sorted([f for f in os.listdir(base_dir) if f.endswith('.md')], key=date_sort_key, reverse=True)
    working = []
    for f in files:
        if date_sort_key(f).weekday() < 5:
            working.append(f)
        if len(working) >= n:
            break
    return sorted(working, key=date_sort_key)


def short_date(fname: str) -> str:
    return date_sort_key(fname).strftime('%-m/%d')


def clean_task_text(text: str) -> str:
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    return re.sub(r'\s+', ' ', text).strip()


def task_key(text: str) -> str:
    t = clean_task_text(text).lower()
    replacements = {
        'build and communicate formal countdown schedule': 'formal countdown schedules',
        'formal countdown schedules': 'formal countdown schedules',
        'admin delay notification to mj': 'admin delay notification',
        'admin delay notification': 'admin delay notification',
        'laundry building co language': 'laundry building co',
        'laundry building co': 'laundry building co',
        'fitness building repair timing': 'fitness repair plan',
        'fitness building repair plan': 'fitness repair plan',
        'fitness building insurance discussion': 'fitness insurance discussion',
        'who punchlist walk': 'who punchlist walk',
        'track salto co': 'track salto co',
        'verify midsouth shed 2 flush completed today; shed 1 (3/23) completed': 'midsouth shed flushes',
        'verify midsouth geo shed flushes': 'midsouth shed flushes',
    }
    for old, new in replacements.items():
        if old in t:
            t = new
            break
    t = re.sub(r'\([^)]*\)', ' ', t)
    t = re.sub(r'[^a-z0-9 ]', ' ', t)
    words = [w for w in t.split() if w not in {'the', 'a', 'an', 'to', 'and', 'for', 'of', 're', 'with'}]
    return ' '.join(words[:8])


def categorize(text: str) -> str:
    lt = text.lower()
    for cat in CATEGORY_ORDER[:-1]:
        if cat.lower() in lt:
            return cat
    return 'Other'


def parse_open_tasks(path: str):
    open_tasks = []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if line.startswith('- [ ]'):
                task = clean_task_text(line[5:].strip())
                if not any(p in task.lower() for p in SKIP_PATTERNS):
                    open_tasks.append(task)
    return open_tasks


def build_open_records(base_dir: str, files: List[str]) -> Dict[str, TaskRecord]:
    records: Dict[str, TaskRecord] = {}
    latest_file = files[-1]
    latest_open_keys = set()

    for fname in files:
        path = os.path.join(base_dir, fname)
        d = short_date(fname)
        tasks = parse_open_tasks(path)
        if fname == latest_file:
            latest_open_keys = {task_key(t) for t in tasks}
        for task in tasks:
            key = task_key(task)
            if key not in records:
                records[key] = TaskRecord(key=key, text=task, category=categorize(task), first_seen=d, last_seen_open=d, open_dates=[d])
            else:
                records[key].text = task
                records[key].category = categorize(task)
                records[key].last_seen_open = d
                records[key].open_dates.append(d)

    return {k: v for k, v in records.items() if k in latest_open_keys}


def summarize_task(text: str) -> str:
    parts = re.split(r'[^A-Za-z0-9]+', text)
    words = [w for w in parts if w and w.lower() not in STOP]
    return ' '.join(words[:6])


def build_rows(records: Dict[str, TaskRecord]):
    grouped = {cat: [] for cat in CATEGORY_ORDER}
    for rec in records.values():
        grouped[rec.category].append(rec)
    rows = []
    for cat in CATEGORY_ORDER:
        items = grouped.get(cat, [])
        if not items:
            continue
        items.sort(key=lambda r: summarize_task(r.text).lower())
        rows.append(('section', cat))
        for rec in items:
            rows.append(('task', rec))
    return rows


def row_height(kind):
    return 40 if kind == 'section' else 36


def paginate_rows(rows):
    pages, current = [], []
    used = 86
    limit = CONTENT_H - 18
    for row in rows:
        needed = row_height(row[0])
        if current and used + needed > limit:
            pages.append(current)
            current = []
            used = 86
        current.append(row)
        used += needed
    if current:
        pages.append(current)
    return pages


def render_page(page_rows, page_num, total_pages, total_open):
    img = Image.new('1', (LAND_W, LAND_H), 1)
    draw = ImageDraw.Draw(img)
    x = MARGIN_X
    y = MARGIN_Y

    draw.text((x, y), 'MULBERRY OPEN TASKS', font=FONT_TITLE, fill=0)
    meta = f'{total_open} items   {page_num}/{total_pages}'
    mb = draw.textbbox((0,0), meta, font=FONT_META)
    draw.text((LAND_W - MARGIN_X - (mb[2]-mb[0]), y + 10), meta, font=FONT_META, fill=0)
    y += 42
    draw.line((x, y, LAND_W - MARGIN_X, y), fill=0, width=2)
    y += 12

    for row in page_rows:
        if row[0] == 'section':
            draw.text((x, y), row[1].upper(), font=FONT_SECTION, fill=0)
            y += 40
            continue
        rec = row[1]
        summary = summarize_task(rec.text)
        draw.ellipse((x + 2, y + 8, x + 18, y + 24), outline=0, width=3)
        draw.text((x + 30, y), summary, font=FONT_TASK, fill=0)
        y += 36

    return img.rotate(-90, expand=True)


def image_to_tspl(img: Image.Image) -> bytes:
    if img.mode != '1':
        img = img.convert('1')
    w, h = img.size
    width_bytes = w // 8
    header = TSPL_HEADER + f'BITMAP 0,0,{width_bytes},{h},0,'.encode()
    bitmap_data = bytearray()
    for row in range(h):
        for byte_idx in range(width_bytes):
            byte_val = 0
            for bit in range(8):
                x = byte_idx * 8 + bit
                if x < w and img.getpixel((x, row)) != 0:
                    byte_val |= (1 << (7 - bit))
            bitmap_data.append(byte_val)
    return header + bytes(bitmap_data) + b'\r\nPRINT 1,1\r\n'


def print_pages(images: List[Image.Image]):
    import subprocess, tempfile
    for idx, img in enumerate(images, 1):
        data = image_to_tspl(img)
        with tempfile.NamedTemporaryFile(suffix=f'-p{idx}.bin', delete=False) as f:
            f.write(data)
            local_bin = f.name
        subprocess.run(f"sshpass -p 'Tesik$89' scp {local_bin} tlewis@192.168.0.128:/tmp/open-page{idx}.bin", shell=True, check=True, capture_output=True, timeout=20)
    remote_cmds = ['rmmod usblp 2>/dev/null || true', 'sleep 1', 'modprobe usblp', 'sleep 2']
    for idx in range(1, len(images)+1):
        remote_cmds.append(f'dd if=/tmp/open-page{idx}.bin of=/dev/usb/lp0 bs=64 2>&1')
        if idx != len(images):
            remote_cmds.append('sleep 3')
    remote_script = '; '.join(remote_cmds)
    subprocess.run(f"sshpass -p 'Tesik$89' ssh tlewis@192.168.0.128 'echo \"Tesik\\$89\" | sudo -S bash -c \"{remote_script}\"'", shell=True, check=True, timeout=90)


if __name__ == '__main__':
    files = get_working_days(HARPER_DAILY, 5)
    records = build_open_records(HARPER_DAILY, files)
    rows = build_rows(records)
    pages = paginate_rows(rows)
    images = []
    for i, page_rows in enumerate(pages, 1):
        img = render_page(page_rows, i, len(pages), len(records))
        img.save(f'/tmp/open_tasks_page_{i}.png')
        images.append(img)
    print(f'Files: {files}')
    print(f'Open tasks: {len(records)} | Pages: {len(pages)}')
    print_pages(images)
    print('Printed open-task labels.')
