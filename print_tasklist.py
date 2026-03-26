#!/usr/bin/env python3
"""Print Harper Mulberry task status list on 4x6 labels.

Rules:
- Open circle marker = task remains active
- Strikethrough line = task is over/closed/past
- Source = last 5 working day Harper daily logs
- Layout = landscape, paginated across labels
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import PRINT_WIDTH_DOTS, LABEL_HEIGHT_DOTS, TSPL_HEADER, PRINT_WIDTH_BYTES
from printer import send_to_printer

HARPER_DAILY = "/home/tlewis/Documents/projects/30 Harper/10 Daily/2026/03-Mar"
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

# Larger, readable fonts for 2-page landscape output
FONT_TITLE = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 34)
FONT_META = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 18)
FONT_SECTION = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 20)
FONT_TASK = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 16)
FONT_TASK_BOLD = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 16)
FONT_SMALL = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 12)

# Landscape composition canvas (rotated before print)
LAND_W = LABEL_HEIGHT_DOTS  # 1218
LAND_H = PRINT_WIDTH_DOTS   # 864
MARGIN_X = 36
MARGIN_Y = 34
CONTENT_W = LAND_W - (MARGIN_X * 2)
CONTENT_H = LAND_H - (MARGIN_Y * 2)

SKIP_PATTERNS = [
    'execute the 9:45',
    'attend the 2:00',
    'capture key outcomes / action items from the rich kelly meeting',
]

TIME_BOUND_HINTS = [
    'today', 'tomorrow', 'walk', 'meeting', 'confirm attendees', 'prep',
    '10 am', '2:00', '3/25', '3/24', '3/23', 'eod', 'submitted', 'disclosed'
]

CATEGORY_ORDER = ['Admin', 'Meeting Hall', 'WHO', 'Fitness', 'Laundry', 'Other']


@dataclass
class TaskRecord:
    key: str
    text: str
    category: str
    first_seen: str
    last_seen_open: str = ''
    open_dates: List[str] = field(default_factory=list)
    closed_dates: List[str] = field(default_factory=list)
    status: str = 'open'  # open | over


# ---------- parsing ----------
def date_sort_key(fname: str):
    return datetime.strptime(fname.replace('.md', ''), '%d-%m-%Y')


def get_working_days(base_dir: str, n: int = 5) -> List[str]:
    files = sorted(
        [f for f in os.listdir(base_dir) if f.endswith('.md')],
        key=date_sort_key,
        reverse=True,
    )
    working = []
    for f in files:
        d = date_sort_key(f)
        if d.weekday() < 5:
            working.append(f)
        if len(working) >= n:
            break
    return sorted(working, key=date_sort_key)  # oldest -> newest for state tracking


def short_date(fname: str) -> str:
    return date_sort_key(fname).strftime('%-m/%d')


def clean_task_text(text: str) -> str:
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def task_key(text: str) -> str:
    t = clean_task_text(text).lower()
    # normalize some common variants so carried-forward tasks collapse together better
    replacements = {
        'build and communicate formal countdown schedule': 'formal countdown schedules',
        'formal countdown schedules': 'formal countdown schedules',
        'admin delay notification to mj': 'admin delay notification',
        'admin delay notification': 'admin delay notification',
        'laundry building co language': 'laundry building co',
        'laundry building co': 'laundry building co',
        'fitness building repair timing': 'fitness building repair plan',
        'fitness building repair plan': 'fitness building repair plan',
        'fitness building insurance discussion': 'fitness building insurance discussion',
        'who punchlist walk': 'who punchlist walk',
        'track salto co': 'track salto co',
        'verify midsouth shed 2 flush completed today; shed 1 (3/23) completed': 'verify midsouth geo shed flushes completed',
        'verify midsouth geo shed flushes': 'verify midsouth geo shed flushes completed',
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


def parse_daily_file(path: str) -> Tuple[List[str], List[str], List[str]]:
    open_tasks, closed_tasks, context_lines = [], [], []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            low = line.lower()

            if line.startswith('- [ ]'):
                task = clean_task_text(line[5:].strip())
                if not any(p in task.lower() for p in SKIP_PATTERNS):
                    open_tasks.append(task)
            elif line.startswith('- [x]') or line.startswith('- [X]'):
                closed_tasks.append(clean_task_text(line[5:].strip()))
            elif any(word in low for word in ['completed', 'closed', 'resolved', 'disclosed', 'coordinated', 'responded', 'finalized', 'sent']):
                context_lines.append(clean_task_text(line))
    return open_tasks, closed_tasks, context_lines


def build_task_records(base_dir: str, files: List[str]) -> Dict[str, TaskRecord]:
    records: Dict[str, TaskRecord] = {}
    latest_file = files[-1]

    for fname in files:
        path = os.path.join(base_dir, fname)
        d = short_date(fname)
        open_tasks, closed_tasks, context = parse_daily_file(path)

        for task in open_tasks:
            key = task_key(task)
            if key not in records:
                records[key] = TaskRecord(
                    key=key,
                    text=task,
                    category=categorize(task),
                    first_seen=d,
                    last_seen_open=d,
                    open_dates=[d],
                )
            else:
                # keep newest phrasing when task is carried forward
                records[key].text = task
                records[key].category = categorize(task)
                records[key].last_seen_open = d
                records[key].open_dates.append(d)

        for task in closed_tasks:
            key = task_key(task)
            if key in records:
                records[key].closed_dates.append(d)
            else:
                records[key] = TaskRecord(
                    key=key,
                    text=task,
                    category=categorize(task),
                    first_seen=d,
                    closed_dates=[d],
                    status='over',
                )

        # heuristic closure from context lines when a matching concept appears as done/resolved
        for line in context:
            ctx_key = task_key(line)
            for rec in records.values():
                if rec.status == 'over':
                    continue
                if rec.key and (rec.key in ctx_key or ctx_key in rec.key):
                    rec.closed_dates.append(d)

    latest_open_keys = set()
    latest_open, _, _ = parse_daily_file(os.path.join(base_dir, latest_file))
    for task in latest_open:
        latest_open_keys.add(task_key(task))

    # Final status classification
    for rec in records.values():
        if rec.key in latest_open_keys:
            rec.status = 'open'
            continue
        if rec.closed_dates:
            rec.status = 'over'
            continue
        # if it stopped being carried forward before the latest day, treat as over
        if rec.last_seen_open and rec.last_seen_open != short_date(latest_file):
            rec.status = 'over'
            continue
        # time-bound tasks from older days are over unless still carried
        if any(h in rec.text.lower() for h in TIME_BOUND_HINTS):
            rec.status = 'over'
            continue
        rec.status = 'open'

    return records


# ---------- rendering ----------
def wrap_text(draw, text, font, max_width):
    words = text.split(' ')
    lines = []
    current = ''
    for word in words:
        test = (current + ' ' + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or ['']


def row_height(draw, rec: TaskRecord) -> int:
    lines = wrap_text(draw, rec.text, FONT_TASK, CONTENT_W - 78)
    return 8 + (len(lines) * 22)


def build_rows(records: Dict[str, TaskRecord]):
    grouped = {cat: [] for cat in CATEGORY_ORDER}
    for rec in records.values():
        grouped[rec.category].append(rec)

    rows = []
    for cat in CATEGORY_ORDER:
        items = grouped.get(cat, [])
        if not items:
            continue
        items.sort(key=lambda r: (r.status != 'open', r.text.lower()))  # open first
        rows.append(('section', cat, len(items)))
        for rec in items:
            rows.append(('task', rec))
    return rows


def paginate_rows(rows):
    probe = Image.new('1', (LAND_W, LAND_H), 1)
    draw = ImageDraw.Draw(probe)

    pages = []
    current = []
    used = 92  # header area
    for row in rows:
        if row[0] == 'section':
            needed = 28
        else:
            needed = row_height(draw, row[1])
        if current and used + needed > (CONTENT_H - 28):
            pages.append(current)
            current = []
            used = 92
        current.append(row)
        used += needed
    if current:
        pages.append(current)
    return pages


def draw_status_marker(draw, x, y, status):
    if status == 'open':
        draw.ellipse((x, y + 4, x + 12, y + 16), outline=0, width=2)
    else:
        draw.line((x, y + 10, x + 14, y + 10), fill=0, width=3)


def render_page(page_rows, page_num, total_pages, open_count, over_count):
    img = Image.new('1', (LAND_W, LAND_H), 1)
    draw = ImageDraw.Draw(img)

    x = MARGIN_X
    y = MARGIN_Y

    # Header
    draw.text((x, y), 'MULBERRY — TASK STATUS', font=FONT_TITLE, fill=0)
    page_text = f'Page {page_num}/{total_pages}'
    pb = draw.textbbox((0, 0), page_text, font=FONT_META)
    draw.text((LAND_W - MARGIN_X - (pb[2] - pb[0]), y + 8), page_text, font=FONT_META, fill=0)
    y += 40

    now = datetime.now().strftime('%A, %B %-d, %Y  %-I:%M %p')
    draw.text((x, y), now, font=FONT_META, fill=0)
    legend = '○ remains   — over'
    lb = draw.textbbox((0, 0), legend, font=FONT_META)
    draw.text((LAND_W - MARGIN_X - (lb[2] - lb[0]), y), legend, font=FONT_META, fill=0)
    y += 26
    draw.line((x, y, LAND_W - MARGIN_X, y), fill=0, width=2)
    y += 10

    for row in page_rows:
        if row[0] == 'section':
            _, cat, count = row
            draw.text((x, y), f'▸ {cat} ({count})', font=FONT_SECTION, fill=0)
            y += 24
            continue

        rec = row[1]
        marker_x = x + 2
        text_x = x + 24
        date_x = LAND_W - MARGIN_X - 36

        lines = wrap_text(draw, rec.text, FONT_TASK, CONTENT_W - 78)
        draw_status_marker(draw, marker_x, y, rec.status)

        text_top = y
        for i, line in enumerate(lines):
            draw.text((text_x, y), line, font=FONT_TASK, fill=0)
            y += 22

        # date tag
        date_tag = rec.last_seen_open or rec.first_seen
        db = draw.textbbox((0, 0), date_tag, font=FONT_SMALL)
        draw.text((date_x - (db[2] - db[0]), text_top + 2), date_tag, font=FONT_SMALL, fill=0)

        # strikethrough if over
        if rec.status == 'over':
            mid_y = text_top + 10
            draw.line((text_x, mid_y, text_x + min(CONTENT_W - 72, 920), mid_y), fill=0, width=2)

        y += 4

    footer_y = LAND_H - MARGIN_Y + 2
    draw.line((x, footer_y - 8, LAND_W - MARGIN_X, footer_y - 8), fill=0, width=1)
    footer = f'Open: {open_count}   Over: {over_count}   Source: last 5 working days'
    draw.text((x, footer_y), footer, font=FONT_SMALL, fill=0)
    draw.text((LAND_W - MARGIN_X - 138, footer_y), 'Harper GC — Mulberry', font=FONT_SMALL, fill=0)

    # Rotate for actual print orientation
    return img.rotate(-90, expand=True)


# ---------- printer ----------
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
    import subprocess
    import tempfile

    for idx, img in enumerate(images, 1):
        data = image_to_tspl(img)
        with tempfile.NamedTemporaryFile(suffix=f'-p{idx}.bin', delete=False) as f:
            f.write(data)
            local_bin = f.name
        subprocess.run(
            f"sshpass -p 'Tesik$89' scp {local_bin} tlewis@192.168.0.128:/tmp/taskstatus-page{idx}.bin",
            shell=True, check=True, capture_output=True, timeout=20,
        )

    remote_cmds = [
        'rmmod usblp 2>/dev/null || true',
        'sleep 1',
        'modprobe usblp',
        'sleep 2',
    ]
    for idx in range(1, len(images) + 1):
        remote_cmds.append(f'dd if=/tmp/taskstatus-page{idx}.bin of=/dev/usb/lp0 bs=64 2>&1')
        if idx != len(images):
            remote_cmds.append('sleep 3')
    remote_script = '; '.join(remote_cmds)

    subprocess.run(
        f"sshpass -p 'Tesik$89' ssh tlewis@192.168.0.128 'echo \"Tesik\\$89\" | sudo -S bash -c \"{remote_script}\"'",
        shell=True, check=True, timeout=90,
    )


if __name__ == '__main__':
    files = get_working_days(HARPER_DAILY, 5)
    records = build_task_records(HARPER_DAILY, files)
    rows = build_rows(records)
    pages = paginate_rows(rows)

    open_count = sum(1 for r in records.values() if r.status == 'open')
    over_count = sum(1 for r in records.values() if r.status == 'over')

    images = []
    for i, page_rows in enumerate(pages, 1):
        img = render_page(page_rows, i, len(pages), open_count, over_count)
        img.save(f'/tmp/taskstatus_page_{i}.png')
        images.append(img)

    print(f'Files: {files}')
    print(f'Tasks: {len(records)} total | {open_count} open | {over_count} over | {len(pages)} pages')
    print_pages(images)
    print('Printed task status labels.')
