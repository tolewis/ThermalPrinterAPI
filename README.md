# PrinterAPI

Print utility for the validated printers in Tim's environment: the iDPRT SP410 4x6 thermal label printer via Raspberry Pi print server and the Dell 1135n network laser printer via the server's CUPS queue.

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


## First-Time Setup Workflow
For first installs, printer identification, driver/transport selection, and initial calibration, use:

- `FIRST_TIME_SETUP.md`

That runbook standardizes:
- printer identification
- transport selection
- first-install queue setup
- mandatory smoke-test page workflow
- calibration feedback loop

## Supported Printers
- **SP410** — 4x6 thermal label path via the Raspberry Pi USB print server
- **Dell 1135n** — plain-paper network printer path via the server CUPS queue `Dell1135n_unhook`

## Dell 1135n Notes
- Queue on server: `Dell1135n_unhook`
- Device URI: `socket://192.168.0.155:9100`
- Driver: `drv:///splix-samsung.drv/scx4623f.ppd`
- Linux mapping: behaves like a rebadged Samsung SCX-4623f
- Pagination lesson: do not trust raw text line-count estimates for one-page jobs; the smoke test overflowed to 2 pages with 16 lines on page 2

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


## Validated Layout Pattern — Monitor Reminder Cards (2026-03-27)

For 4x6 cards meant to be **stuck to a monitor** and read at a glance:

- Design for **dominance**, not density.
- **Landscape-first composition** worked better than timid portrait text blocks.
- Use **fewer words**, stronger headers, and materially larger type.
- Fill most of the page first; then apply a **small uniform downscale** to clear the printer's physical margins.
- Treat the first print as a transport/proof pass, not as final design truth.
- Require a **real photo / human eyes** before calling the layout done.

What worked in practice:
- Card 1: weekly schedule with day-by-day blocks + short rules footer
- Card 2: directional reminder card with 6-8 hard one-liners
- Final successful pattern: v2 fixed composition, v3 slightly shrank the approved layout to fit the stock cleanly
