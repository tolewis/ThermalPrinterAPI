"""SP410 Thermal Printer Configuration."""

# --- Pi Print Server ---
PI_HOST = "tlewis@192.168.0.128"
PI_PASS = "Tesik$89"

# --- Printer Hardware ---
# iDPRT SP410, 203 DPI, 864 dot print head
PRINT_WIDTH_DOTS = 864
PRINT_WIDTH_BYTES = PRINT_WIDTH_DOTS // 8  # 108
DPI = 203

# --- Label Dimensions (4x6 with gaps) ---
LABEL_WIDTH_MM = 101.6   # 4 inches
LABEL_HEIGHT_MM = 152.4  # 6 inches
GAP_MM = 3               # gap between labels
LABEL_HEIGHT_DOTS = 1218  # 6 inches * 203 DPI

# --- Print Area (accounting for label offset + margins) ---
# Label starts 2.5mm from y=0, plus 2.5mm margin = 5mm top margin
# Content bleeds right at x, so add right margin
MARGIN_TOP_DOTS = int(5.0 / 25.4 * DPI)     # ~40 dots (5mm)
MARGIN_BOTTOM_DOTS = int(5.0 / 25.4 * DPI)  # ~40 dots (5mm)
MARGIN_LEFT_DOTS = int(3.0 / 25.4 * DPI)    # ~24 dots (3mm) - already ~5mm physical offset
MARGIN_RIGHT_DOTS = int(8.0 / 25.4 * DPI)   # ~64 dots (8mm) - prevent right bleed

# Printable area
CONTENT_X = MARGIN_LEFT_DOTS
CONTENT_Y = MARGIN_TOP_DOTS
CONTENT_W = PRINT_WIDTH_DOTS - MARGIN_LEFT_DOTS - MARGIN_RIGHT_DOTS
CONTENT_H = LABEL_HEIGHT_DOTS - MARGIN_TOP_DOTS - MARGIN_BOTTOM_DOTS

# --- TSPL Command Template ---
TSPL_HEADER = (
    f"SIZE {LABEL_WIDTH_MM} mm,{LABEL_HEIGHT_MM} mm\r\n"
    f"GAP {GAP_MM} mm,0 mm\r\n"
    "SPEED 4\r\n"
    "DENSITY 10\r\n"
    "DIRECTION 1\r\n"
    "OFFSET 0\r\n"
    "SHIFT 0\r\n"
    "CLS\r\n"
).encode()
