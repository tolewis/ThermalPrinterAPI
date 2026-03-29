# PrinterAPI — First-Time Setup & Test Workflow

Use this workflow whenever an agent needs to identify a printer, choose the right transport/driver path, install it for the first time, and run a controlled print test.

---

## Goal

For any printer, establish four things in order:
1. **Identity** — exact model / firmware / connection type
2. **Transport** — USB raw, IPP, LPR, socket/9100, shared Windows queue, etc.
3. **Install path** — the cleanest known queue/driver route for the host you are on
4. **Smoke test** — one intentionally simple page that verifies borders, margins, spacing, line breaks, and orientation before real work

Do **not** skip the smoke test.

---

## 1) Identify the printer

### A. If printer is on Linux and/or attached locally

```bash
lsusb
lpstat -p -d
lpinfo -v
ip neigh
```

Useful clues:
- USB VID/PID
- model string from `lpinfo -v` or `lpstat`
- presence of `/dev/usb/lp0` for raw USB printers
- open network services on likely IPs: 631, 515, 9100, 80

Network probe example:

```bash
for p in 80 443 515 631 9100; do
  (echo > /dev/tcp/PRINTER_IP/$p) >/dev/null 2>&1 && echo "OPEN $p" || echo "CLOSED $p"
done
```

### B. If printer is already working on Windows

Use the working Windows queue as the source of truth first.

```powershell
Get-Printer | Select Name,DriverName,PortName,Shared,ShareName,Type,PrinterStatus
Get-PrinterPort -Name '<PORTNAME>' | Format-List *
Get-PnpDevice | ? FriendlyName -match 'printer|canon|dell|idprt|brother|hp|epson'
```

Capture:
- queue name
- driver name
- port type / host address
- whether it is shared

### C. If model identity is fuzzy

Check the printer web UI if available:
- `http://PRINTER_IP/`

Look for:
- exact model name
- supported page description languages (PCL, PostScript, SPL, TSPL, ZPL, ESC/POS, etc.)
- firmware version

---

## 2) Choose the transport path

Use the simplest reliable path that matches the printer.

### Preferred order
1. **Known-good vendor/protocol path already proven in the environment**
2. **IPP / IPP Everywhere** if truly supported and known-good
3. **Raw socket (9100)** for many network laser printers
4. **LPR (515)** if the printer clearly expects it
5. **Raw USB device writes** for special-purpose printers like thermal label units
6. **Shared Windows printer path** only if direct network/device install is not available

### Special cases
- **Thermal label printers** often need raw command streams or bitmap rendering rather than generic text/driver printing.
- **Older Dell/Samsung-class laser printers** may require SPL/SPLIX rather than generic PostScript.
- If the printer explicitly lacks PostScript, **do not guess a PS driver**.

---

## 3) Install path decision tree

### A. Thermal / raw-command printer
Use when:
- raw USB path is visible (`/dev/usb/lp0`)
- generic text/driver path fails
- command language is TSPL/ZPL/ESC/POS/etc.

Approach:
- render content as bitmap if native text commands are unreliable
- send to device using raw write path
- calibrate one variable at a time

### B. Network plain-paper printer
Use when:
- printer has stable IP
- port 9100 / 631 / 515 is open
- CUPS can maintain a queue

Approach:
- choose the cleanest driver/protocol match
- create a queue in CUPS
- run a one-page smoke test before any real print job

### C. Windows-known printer, Linux unknown
Use when:
- printer already works on Windows
- Linux install path is unclear

Approach:
- pull Windows queue + port details first
- map equivalent Linux driver/model if needed
- prefer direct network install over depending on Windows sharing

---

## 4) Mandatory initial smoke test

Every new printer setup must pass a controlled smoke test before real jobs.

### Test goals
The first test page should verify:
- top/bottom/left/right margins
- whether the printer clips borders
- line spacing and paragraph spacing
- orientation
- line break handling
- page overflow / pagination behavior
- whether the selected driver/protocol is actually correct

### Test design rules
- Keep it to **one page** on paper printers, **one label** on label printers
- Use **big obvious header text**
- Include a **thin border** near the safe margins
- Include **short lines** and **long wrapped lines**
- Include **numbered line samples**
- Include at least one **alignment/ruler section**
- For paper printers, leave **extra safety margin** on the first test
- For label printers, favor a bold near-full-page test card over dense content

### Minimum content for the first test page
Use this structure:

1. Header
2. Printer/model/queue name
3. Date/time
4. Border test note
5. A short paragraph
6. A long wrapped paragraph
7. 5–10 numbered lines
8. Footer: “Report top/bottom/left/right clipping + line spacing + page count”

### Human verification questions
After printing, ask only these:
1. Did it print on **one page / one label**?
2. Any clipping on **top / bottom / left / right**?
3. Is line spacing **too tight / too loose / okay**?
4. Did long lines wrap cleanly?
5. Is orientation correct?
6. What single adjustment is most needed next?

Then change **one variable** and re-test.

---

## 5) Calibration loop

When the first page is close but not right:
1. Pick **one** issue only
2. Change **one** variable only
3. Reprint
4. Ask for visual feedback
5. Repeat

Variables to tune:
- page margins
- top buffer
- orientation
- font size
- line spacing
- printable width / height
- truncation rules
- page geometry / render size

Never change multiple variables at once if the goal is calibration.

---

## 6) Known-good local printer paths

### iDPRT SP410
- Type: 4x6 thermal label printer
- Path: Raspberry Pi raw USB write
- Device: `/dev/usb/lp0`
- Method: bitmap render + TSPL `BITMAP`
- Notes:
  - TSPL `TEXT` was not reliable on this unit
  - bitmap workflow is the validated path
  - physical print/photo verification matters more than theoretical page math

### Dell 1135n Laser MFP
- Type: network laser printer
- Host/IP: `192.168.0.155`
- Server queue: `Dell1135n_unhook`
- URI: `socket://192.168.0.155:9100`
- Linux driver: `drv:///splix-samsung.drv/scx4623f.ppd`
- Notes:
  - behaves like a rebadged Samsung SCX-4623f
  - PostScript is not installed; do not default to generic PS
  - initial “one-page” text smoke test overflowed to 2 pages with 16 lines on page 2, so future first tests should use conservative margins / deliberate page geometry

---

## 7) What to document after setup

After a printer is working, record:
- exact model
- connection type
- IP / USB path / URI
- working queue name
- working driver/model
- known-bad paths tried
- first successful smoke test result
- calibration findings
- final recommended workflow

Update both:
- this repo / README when the knowledge is reusable
- the agent printer skill so future agents route correctly

---

## 8) Success condition

A printer is not “set up” just because a queue exists.

It is only “set up” when:
- the queue/device is reachable
- a smoke test prints
- a human verifies margins/spacing/orientation are usable
- the winning path is documented for the next agent
