#!/usr/bin/env python3
"""Print arbitrary text on a 4x6 label."""

import argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from config import (
    PRINT_WIDTH_DOTS, LABEL_HEIGHT_DOTS,
    CONTENT_X, CONTENT_Y, CONTENT_W, CONTENT_H
)
from printer import print_image

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def render_text_label(title=None, body="", font_size=20):
    """Render text onto a 4x6 label."""
    img = Image.new('1', (PRINT_WIDTH_DOTS, LABEL_HEIGHT_DOTS), 1)
    draw = ImageDraw.Draw(img)

    x = CONTENT_X
    y = CONTENT_Y
    max_w = CONTENT_W

    if title:
        title_font = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", font_size + 8)
        draw.text((x, y), title, font=title_font, fill=0)
        y += font_size + 16
        draw.line([(x, y), (x + max_w, y)], fill=0, width=2)
        y += 8

    body_font = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", font_size)

    for line in body.split('\n'):
        # Word wrap
        words = line.split(' ')
        current = ''
        for word in words:
            test = (current + ' ' + word).strip()
            bbox = draw.textbbox((0, 0), test, font=body_font)
            if bbox[2] <= max_w:
                current = test
            else:
                if current:
                    draw.text((x, y), current, font=body_font, fill=0)
                    y += font_size + 4
                current = word
        if current:
            draw.text((x, y), current, font=body_font, fill=0)
            y += font_size + 4

    # Timestamp at bottom
    ts_font = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", 10)
    fy = CONTENT_Y + CONTENT_H
    now = datetime.now()
    draw.text((x, fy + 3), now.strftime("Printed %Y-%m-%d %H:%M"), font=ts_font, fill=0)

    return img


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Print text on 4x6 label')
    parser.add_argument('text', nargs='?', default='Hello World!', help='Text to print')
    parser.add_argument('--title', '-t', help='Title/header text')
    parser.add_argument('--body', '-b', help='Body text (overrides positional)')
    parser.add_argument('--font-size', '-s', type=int, default=20, help='Font size (default 20)')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Preview only, no print')
    args = parser.parse_args()

    body = args.body or args.text
    img = render_text_label(title=args.title, body=body, font_size=args.font_size)
    img.save('/tmp/label_preview.png')

    if args.dry_run:
        print("Preview saved to /tmp/label_preview.png (dry run, not printing)")
    else:
        print_image(img)
