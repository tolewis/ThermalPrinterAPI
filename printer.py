"""Core printer interface for iDPRT SP410 via Pi."""

import subprocess
import tempfile
from PIL import Image
from config import (
    PI_HOST, PI_PASS, PRINT_WIDTH_DOTS, PRINT_WIDTH_BYTES,
    LABEL_HEIGHT_DOTS, TSPL_HEADER
)


def image_to_tspl(img: Image.Image) -> bytes:
    """Convert a PIL 1-bit image to TSPL BITMAP binary.

    Polarity: this printer uses inverted polarity.
    In the PIL image: 0=black (ink), 255/1=white (no ink).
    For the TSPL BITMAP on this printer: 0=print dot, 1=no print.
    So we send PIL black pixels as 0 (print) and white as 1 (no print).
    """
    W, H = img.size
    assert W == PRINT_WIDTH_DOTS, f"Image width must be {PRINT_WIDTH_DOTS}, got {W}"
    assert H <= LABEL_HEIGHT_DOTS, f"Image height must be <= {LABEL_HEIGHT_DOTS}, got {H}"

    width_bytes = PRINT_WIDTH_BYTES

    bitmap_cmd = f"BITMAP 0,0,{width_bytes},{H},0,".encode()

    bitmap_data = bytearray()
    for row in range(H):
        for byte_idx in range(width_bytes):
            byte_val = 0
            for bit in range(8):
                x = byte_idx * 8 + bit
                if x < W:
                    pixel = img.getpixel((x, row))
                    # Inverted: white pixels (1) get bit set (no print)
                    # black pixels (0) get bit clear (print dot)
                    if pixel != 0:
                        byte_val |= (1 << (7 - bit))
            bitmap_data.append(byte_val)

    footer = b"\r\nPRINT 1,1\r\n"

    return TSPL_HEADER + bitmap_cmd + bytes(bitmap_data) + footer


def send_to_printer(data: bytes, dry_run: bool = False) -> bool:
    """Send raw TSPL binary to the SP410 via Pi.

    Returns True on success.
    """
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        f.write(data)
        tmp_path = f.name

    if dry_run:
        print(f"DRY RUN: would send {len(data)} bytes to printer")
        return True

    # SCP to Pi
    scp = subprocess.run(
        f"sshpass -p '{PI_PASS}' scp {tmp_path} {PI_HOST}:/tmp/label.bin",
        shell=True, capture_output=True, timeout=15
    )
    if scp.returncode != 0:
        print(f"SCP failed: {scp.stderr.decode()}")
        return False

    # Reset USB and send to printer
    result = subprocess.run(
        f"sshpass -p '{PI_PASS}' ssh {PI_HOST} '"
        f'echo "Tesik\\$89" | sudo -S bash -c "'
        f"rmmod usblp 2>/dev/null; sleep 1; modprobe usblp; sleep 2; "
        f'dd if=/tmp/label.bin of=/dev/usb/lp0 bs=64 2>&1"' + "'",
        shell=True, capture_output=True, text=True, timeout=30
    )

    if result.returncode == 0:
        print(f"Printed: {len(data)} bytes sent")
        return True
    else:
        print(f"Print failed: {result.stderr}")
        return False


def print_image(img: Image.Image, dry_run: bool = False) -> bool:
    """Render a PIL image and send to printer."""
    # Ensure correct size
    if img.mode != '1':
        img = img.convert('1')

    # Pad/crop to full label width
    if img.width != PRINT_WIDTH_DOTS:
        new_img = Image.new('1', (PRINT_WIDTH_DOTS, img.height), 1)
        new_img.paste(img, (0, 0))
        img = new_img

    data = image_to_tspl(img)
    return send_to_printer(data, dry_run=dry_run)
