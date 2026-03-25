#!/usr/bin/env python3
"""Print Harper Mulberry open tasks on a 4x6 label."""

import os
import re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from config import (
    PRINT_WIDTH_DOTS, LABEL_HEIGHT_DOTS,
    CONTENT_X, CONTENT_Y, CONTENT_W, CONTENT_H,
    MARGIN_LEFT_DOTS, MARGIN_RIGHT_DOTS, MARGIN_TOP_DOTS, MARGIN_BOTTOM_DOTS
)
from printer import print_image

# --- Config ---
HARPER_DAILY = "/home/tlewis/Documents/projects/30 Harper/10 Daily/2026/03-Mar"

# --- Fonts ---
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT_TITLE = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 26)
FONT_DATE = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 14)
FONT_SECTION = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 14)
FONT_TASK = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 12)
FONT_SMALL = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 10)


def get_working_days(base_dir, n=5):
    """Get last n working day filenames from Harper daily logs."""
    files = sorted(os.listdir(base_dir), reverse=True)
    working = []
    for f in files:
        if not f.endswith('.md'):
            continue
        try:
            d = datetime.strptime(f.replace('.md', ''), '%d-%m-%Y')
            if d.weekday() < 5:
                working.append(f)
            if len(working) >= n:
                break
        except ValueError:
            continue
    return working


def extract_open_tasks(base_dir, files):
    """Extract unique unclosed tasks from daily logs."""
    tasks = []
    seen = set()

    skip_patterns = [
        'execute the 9:45', 'attend the 2:00', 'walk tomorrow',
        'capture key outcomes'
    ]

    for fname in files:
        path = os.path.join(base_dir, fname)
        try:
            d = datetime.strptime(fname.replace('.md', ''), '%d-%m-%Y')
            short_date = d.strftime('%-m/%d')
        except ValueError:
            short_date = fname[:5]

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line.startswith('- [ ]'):
                    continue

                task = line[5:].strip()
                task = re.sub(r'\*\*([^*]+)\*\*', r'\1', task)

                if any(s in task.lower() for s in skip_patterns):
                    continue

                key = re.sub(r'[^a-z0-9]', '', task[:35].lower())
                if key not in seen:
                    seen.add(key)
                    tasks.append((short_date, task))

    return tasks


def categorize(tasks):
    """Group tasks by building/topic."""
    cats = {
        'Admin': [], 'Meeting Hall': [], 'WHO': [],
        'Fitness': [], 'Laundry': [], 'Other': []
    }
    for date, task in tasks:
        placed = False
        for cat in ['Admin', 'Meeting Hall', 'WHO', 'Fitness', 'Laundry']:
            if cat.lower() in task.lower():
                cats[cat].append((date, task))
                placed = True
                break
        if not placed:
            cats['Other'].append((date, task))
    return {k: v for k, v in cats.items() if v}


def wrap_text(text, font, max_width, draw):
    """Word-wrap text to fit within max_width pixels."""
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
    return lines


def render_tasklist(categories, total_tasks):
    """Render task list onto a full 4x6 label."""
    img = Image.new('1', (PRINT_WIDTH_DOTS, LABEL_HEIGHT_DOTS), 1)  # white
    draw = ImageDraw.Draw(img)

    x = CONTENT_X
    max_w = CONTENT_W
    y = CONTENT_Y

    # Title
    draw.text((x, y), "MULBERRY — OPEN TASKS", font=FONT_TITLE, fill=0)
    y += 32

    # Date line
    now = datetime.now()
    draw.text((x, y), now.strftime("%A, %B %-d, %Y  %-I:%M %p"), font=FONT_DATE, fill=0)
    y += 20

    # Divider
    draw.line([(x, y), (x + max_w, y)], fill=0, width=2)
    y += 8

    # Content area bounds
    y_max = CONTENT_Y + CONTENT_H - 30

    for cat_name, cat_tasks in categories.items():
        if y > y_max:
            draw.text((x, y), "... more tasks not shown", font=FONT_SMALL, fill=0)
            break

        # Category header
        draw.text((x, y), f"▸ {cat_name} ({len(cat_tasks)})", font=FONT_SECTION, fill=0)
        y += 18

        for date, task in cat_tasks:
            if y > y_max:
                break

            task_lines = wrap_text(f"☐ {task}", FONT_TASK, max_w - 50, draw)

            for i, line in enumerate(task_lines):
                if y > y_max:
                    break
                if i == 0:
                    draw.text((x + 4, y), line, font=FONT_TASK, fill=0)
                    # Date in right margin
                    dbbox = draw.textbbox((0, 0), date, font=FONT_SMALL)
                    dw = dbbox[2] - dbbox[0]
                    draw.text((x + max_w - dw, y + 2), date, font=FONT_SMALL, fill=0)
                else:
                    draw.text((x + 20, y), line, font=FONT_TASK, fill=0)
                y += 15
        y += 4

    # Footer
    fy = CONTENT_Y + CONTENT_H
    draw.line([(x, fy), (x + max_w, fy)], fill=0, width=1)
    draw.text((x, fy + 3), f"{total_tasks} open tasks — last 5 working days", font=FONT_SMALL, fill=0)
    draw.text((x + max_w - 140, fy + 3), "Harper GC — Mulberry", font=FONT_SMALL, fill=0)

    return img


if __name__ == '__main__':
    print("Extracting open tasks...")
    files = get_working_days(HARPER_DAILY)
    print(f"Files: {files}")

    tasks = extract_open_tasks(HARPER_DAILY, files)
    print(f"Found {len(tasks)} unique open tasks")

    categories = categorize(tasks)
    for cat, items in categories.items():
        print(f"  {cat}: {len(items)}")

    print("Rendering label...")
    img = render_tasklist(categories, len(tasks))
    img.save('/tmp/tasklist_preview.png')
    print("Preview saved to /tmp/tasklist_preview.png")

    print("Sending to printer...")
    print_image(img)
