# ThermalPrinterAPI

Print utility for iDPRT SP410 thermal label printer via Raspberry Pi print server.

## Hardware
- **Printer:** iDPRT SP410 (4x6 thermal label printer, TSPL firmware 2.00.04.02)
- **Print Server:** Raspberry Pi 3B, Bookworm Lite 64-bit, kernel 6.12
- **Connection:** USB via `/dev/usb/lp0` (usblp driver)
- **Labels:** 4x6 inch with gaps

## How It Works
The SP410's TSPL TEXT commands don't work (internal fonts missing in this firmware). All printing is done by rendering text/graphics as bitmap images on the host, then sending via TSPL `BITMAP` command.

**Key printer settings:**
- `SIZE 101.6 mm,152.4 mm` (MUST use mm, not inches)
- `GAP 3 mm,0 mm` (for labels with gaps)
- 864 dots wide = 108 bytes/row
- Polarity: inverted from TSPL spec (0=print dot, 1=no print)
- `DIRECTION 1` for right-side up
- Transfer: `dd bs=64` to `/dev/usb/lp0`

## Usage

```bash
# Print Harper daily task list
python3 print_tasklist.py

# Print arbitrary text
python3 print_label.py "Your text here"

# Print with options
python3 print_label.py --title "HEADER" --body "Content here" --font-size 24
```

## Configuration

Edit `config.py` for printer/Pi settings.

## Requirements
- Python 3.8+
- Pillow (`pip install Pillow`)
- sshpass (for remote Pi access)
- Pi must be on network at configured IP with printer plugged in
