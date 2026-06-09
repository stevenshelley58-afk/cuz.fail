#!/usr/bin/env python3
"""
generate_site_plan.py — DraftCheck WA M1 Golden Fixture (Session B)

Generates data/fixtures/m1/site_plan.pdf: a single-dwelling site plan with
five Tier-1 check annotations showing three passes, one designed-in likely_fail,
and one designed-in needs_more_info outcome.

All dimensions are ILLUSTRATIVE TEST DATA — not authoritative R-Codes values.
Authoritative values must be bound from approved source versions at Stage 3/5.

Designed-in non-passes (per M1 fixture spec, MASTER_REBUILD_PLAN.md §9 Phase 5):
  #1 likely_fail:      left side setback 0.8m < 1.0m illustrative min
  #2 needs_more_info:  boundary wall ~9.5m? — scale unverified, not promotable
"""

import pathlib
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF (fitz) not found. Install with: pip install pymupdf")

# ---------------------------------------------------------------------------
# Output path (relative to repo root; caller must run from repo root)
# ---------------------------------------------------------------------------
OUTPUT = pathlib.Path("data/fixtures/m1/site_plan.pdf")

# ---------------------------------------------------------------------------
# Page setup — A4 landscape
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = 841.89, 595.28  # points (1 point = 1/72 inch)

# ---------------------------------------------------------------------------
# Scale: 1:200  →  1 metre real = 5 mm on paper = 5 × 72/25.4 points
# ---------------------------------------------------------------------------
M = 5.0 * 72.0 / 25.4  # ≈ 14.173 pt per metre

# ---------------------------------------------------------------------------
# Lot dimensions (metres)
# ---------------------------------------------------------------------------
LOT_W = 15.0   # east-west width
LOT_D = 32.0   # north-south depth

# ---------------------------------------------------------------------------
# Drawing origin: lot top-left corner = front (street/north) boundary, top of page
# ---------------------------------------------------------------------------
OX = 110.0  # lot left edge (points)
OY = 38.0   # lot top edge (points)

# Lot corners
LX0, LY0 = OX, OY                          # top-left (NW)
LX1, LY1 = OX + LOT_W * M, OY + LOT_D * M  # bottom-right (SE)

# ---------------------------------------------------------------------------
# Building footprint
#   Front setback: 7.0m  →  PASS (illustrative min 6.0m)
#   Left setback:  0.8m  →  LIKELY_FAIL (illustrative min 1.0m)  [designed-in #1]
#   Width: 12.0m, Depth: 14.0m
# ---------------------------------------------------------------------------
BLD_FS = 7.0   # front setback (pass)
BLD_LS = 0.8   # left side setback (fail — under illustrative 1.0m min)
BLD_W  = 12.0
BLD_D  = 14.0

BX0 = OX + BLD_LS * M
BY0 = OY + BLD_FS * M
BX1 = BX0 + BLD_W * M
BY1 = BY0 + BLD_D * M

# Right side setback: 15.0 - 0.8 - 12.0 = 2.2m
# Rear setback: 32.0 - 7.0 - 14.0 = 11.0m

# ---------------------------------------------------------------------------
# Garage: 3.0m wide × 5.5m deep, front-left of building
#   Garage ratio: 3.0/15.0 = 20%  →  PASS (illustrative max 50%)
# ---------------------------------------------------------------------------
GRG_W = 3.0
GRG_D = 5.5
GX0, GY0 = BX0, BY0
GX1 = GX0 + GRG_W * M
GY1 = GY0 + GRG_D * M

# ---------------------------------------------------------------------------
# Boundary wall: on left lot boundary, length ~9.5m  [designed-in #2]
#   Runs from front-setback level (~7.0m from front) for ~9.5m
#   Labeled with "~" and "?" to indicate uncalibrated/ambiguous measurement
# ---------------------------------------------------------------------------
BWX = OX  # on left lot boundary
BWY0 = OY + BLD_FS * M                   # 7.0m from front
BWY1 = OY + (BLD_FS + 9.5) * M          # ~9.5m lower

# ---------------------------------------------------------------------------
# Colours (RGB 0-1)
# ---------------------------------------------------------------------------
BLACK  = (0.0, 0.0, 0.0)
DGRAY  = (0.3, 0.3, 0.3)
LGRAY  = (0.75, 0.75, 0.75)
RED    = (0.78, 0.08, 0.08)
ORANGE = (0.88, 0.48, 0.02)
GREEN  = (0.08, 0.55, 0.12)
BLUE   = (0.12, 0.28, 0.68)
LTBLUE = (0.88, 0.92, 0.98)
LTGRN  = (0.90, 0.97, 0.90)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def draw_rect(page, x0, y0, x1, y1, stroke=BLACK, fill=None, width=1.0):
    r = fitz.Rect(x0, y0, x1, y1)
    page.draw_rect(r, color=stroke, fill=fill, width=width)


def draw_line(page, x0, y0, x1, y1, color=BLACK, width=1.0):
    page.draw_line((x0, y0), (x1, y1), color=color, width=width)


def txt(page, x, y, s, size=7.0, color=BLACK, bold=False):
    fname = "hebo" if bold else "helv"
    page.insert_text((x, y), s, fontname=fname, fontsize=size, color=color)


def hdim(page, x0, x1, y, label, color=GREEN, above=True, tick=5):
    """Horizontal dimension line with end ticks and centred label."""
    draw_line(page, x0, y, x1, y, color=color, width=0.6)
    draw_line(page, x0, y - tick, x0, y + tick, color=color, width=0.6)
    draw_line(page, x1, y - tick, x1, y + tick, color=color, width=0.6)
    ly = y - 8 if above else y + 10
    cx = (x0 + x1) / 2
    page.insert_text((cx - len(label) * 2.0, ly), label,
                     fontname="helv", fontsize=5.5, color=color)


def vdim(page, x, y0, y1, label, color=GREEN, right_side=True, tick=5):
    """Vertical dimension line with end ticks and label."""
    draw_line(page, x, y0, x, y1, color=color, width=0.6)
    draw_line(page, x - tick, y0, x + tick, y0, color=color, width=0.6)
    draw_line(page, x - tick, y1, x + tick, y1, color=color, width=0.6)
    cy = (y0 + y1) / 2
    lx = x + 4 if right_side else x - len(label) * 3.6 - 4
    page.insert_text((lx, cy + 3), label,
                     fontname="helv", fontsize=5.5, color=color)


# ---------------------------------------------------------------------------
# Main drawing function
# ---------------------------------------------------------------------------
def generate(output: pathlib.Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)

    # White background
    draw_rect(page, 0, 0, PAGE_W, PAGE_H, stroke=None, fill=(1.0, 1.0, 1.0))

    # ------------------------------------------------------------------ LOT
    draw_rect(page, LX0, LY0, LX1, LY1, stroke=BLACK, fill=None, width=1.5)
    txt(page, LX0 + 2, LY0 + 8, "NORTH / STREET BOUNDARY", size=5.5, color=DGRAY)

    # ------------------------------------------------------------------ BUILDING
    draw_rect(page, BX0, BY0, BX1, BY1, stroke=BLUE, fill=LTBLUE, width=1.2)
    bcx = (BX0 + BX1) / 2
    bcy = (BY0 + BY1) / 2
    txt(page, bcx - 20, bcy - 6, "BUILDING", size=7.5, color=BLUE, bold=True)
    txt(page, bcx - 25, bcy + 6, "12.0m × 14.0m (168 sqm)", size=6.0, color=BLUE)

    # ------------------------------------------------------------------ GARAGE
    draw_rect(page, GX0, GY0, GX1, GY1, stroke=BLUE, fill=(0.78, 0.85, 0.96), width=0.9)
    txt(page, GX0 + 2, GY0 + 11, "GARAGE", size=5.5, color=BLUE, bold=True)
    txt(page, GX0 + 2, GY0 + 21, "3.0m", size=5.5, color=BLUE)

    # ------------------------------------------------------------------ BOUNDARY WALL (designed-in #2)
    # Drawn as a thick orange line on the left lot boundary
    draw_line(page, BWX, BWY0, BWX, BWY1, color=ORANGE, width=4.0)
    # Leader from wall to label box on right side of lot
    lead_x = LX1 + 12
    lead_mid_y = (BWY0 + BWY1) / 2
    draw_line(page, BWX + 2, lead_mid_y, lead_x - 2, lead_mid_y,
              color=ORANGE, width=0.5)
    txt(page, lead_x, lead_mid_y - 22, "Boundary wall:", size=6.5, color=ORANGE, bold=True)
    txt(page, lead_x, lead_mid_y - 12, "~9.5 m?", size=7.5, color=ORANGE, bold=True)
    txt(page, lead_x, lead_mid_y - 1,  "[scale unverified —", size=6.0, color=ORANGE)
    txt(page, lead_x, lead_mid_y + 9,  " not promotable]", size=6.0, color=ORANGE)
    txt(page, lead_x, lead_mid_y + 20, "→ needs_more_info ★2", size=6.0, color=ORANGE, bold=True)

    # ------------------------------------------------------------------ DIMENSION: front setback (PASS)
    dim_x = OX - 22  # vertical dim line to the left of lot
    vdim(page, dim_x, LY0, BY0,
         "7.0 m", color=GREEN, right_side=False)
    txt(page, OX - 108, LY0 + 8, "Front setback:", size=6.0, color=GREEN, bold=True)
    txt(page, OX - 108, LY0 + 18, "7.0 m  (min 6.0 m)", size=5.5, color=GREEN)
    txt(page, OX - 108, LY0 + 28, "→ likely_pass  ✓", size=6.0, color=GREEN, bold=True)

    # ------------------------------------------------------------------ DIMENSION: left side setback (FAIL, designed-in #1)
    # Horizontal dim at the top of the building, between lot edge and building edge
    fail_dim_y = BY0 - 14
    hdim(page, OX, BX0, fail_dim_y,
         "0.8 m", color=RED, above=True)
    # Annotation below the dim line
    txt(page, OX + 1, fail_dim_y + 12,
        "Side setback: 0.8 m < 1.0 m illustrative min → likely_fail  ★1",
        size=5.5, color=RED, bold=True)

    # ------------------------------------------------------------------ DIMENSION: right side setback
    hdim(page, BX1, LX1, BY0 - 6, "2.2 m", color=DGRAY, above=True)

    # ------------------------------------------------------------------ OPEN SPACE annotation (PASS)
    osy = BY1 + 14
    draw_rect(page, LX0 + 2, osy, LX0 + 190, osy + 38,
              stroke=GREEN, fill=LTGRN, width=0.5)
    txt(page, LX0 + 5, osy + 10, "Open space (rear + sides):", size=6.5, color=GREEN, bold=True)
    txt(page, LX0 + 5, osy + 21, "≈ 312 sqm  /  ≈ 65% of 480 sqm lot", size=6.0, color=GREEN)
    txt(page, LX0 + 5, osy + 32, "illustrative min 45%  →  likely_pass  ✓", size=6.0, color=GREEN)

    # ------------------------------------------------------------------ GARAGE DOMINANCE note (PASS)
    gny = GY1 + 8
    txt(page, GX0, gny, "Garage: 3.0m / 15.0m frontage = 20%", size=5.5, color=GREEN)
    txt(page, GX0, gny + 9, "illustrative max 50%  →  likely_pass  ✓", size=5.5, color=GREEN)

    # ------------------------------------------------------------------ SITE COVER note (PASS)
    sc_x = BX1 + 8
    sc_y = BY0 + 4
    txt(page, sc_x, sc_y,      "Site cover:", size=6.5, color=GREEN, bold=True)
    txt(page, sc_x, sc_y + 11, "168 / 480 = 35%", size=6.0, color=GREEN)
    txt(page, sc_x, sc_y + 22, "max 50%", size=6.0, color=GREEN)
    txt(page, sc_x, sc_y + 33, "→ likely_pass  ✓", size=6.0, color=GREEN)

    # ------------------------------------------------------------------ SCALE BAR
    sb_x = BX1 + 8
    sb_y = BY1 - 20
    ten_m = 10 * M
    draw_line(page, sb_x, sb_y, sb_x + ten_m, sb_y, color=BLACK, width=1.0)
    draw_line(page, sb_x, sb_y - 4, sb_x, sb_y + 4, color=BLACK, width=1.0)
    draw_line(page, sb_x + ten_m, sb_y - 4, sb_x + ten_m, sb_y + 4, color=BLACK, width=1.0)
    txt(page, sb_x - 2, sb_y - 6, "0", size=5.5, color=BLACK)
    txt(page, sb_x + ten_m - 6, sb_y - 6, "10 m", size=5.5, color=BLACK)
    txt(page, sb_x, sb_y + 11, "Scale 1:200", size=5.5, color=DGRAY)

    # ------------------------------------------------------------------ NORTH ARROW
    na_x = BX1 + 18
    na_y = LY1 - 25
    draw_line(page, na_x + 8, na_y, na_x + 8, na_y - 18, color=BLACK, width=1.5)
    page.draw_line((na_x + 8, na_y - 18), (na_x + 5, na_y - 12),
                   color=BLACK, width=1.0)
    page.draw_line((na_x + 8, na_y - 18), (na_x + 11, na_y - 12),
                   color=BLACK, width=1.0)
    txt(page, na_x + 6, na_y - 22, "N", size=9, color=BLACK, bold=True)

    # ------------------------------------------------------------------ LOT LABEL
    txt(page, LX0 + 2, LY1 - 5, "Lot: 15.0m × 32.0m = 480 sqm", size=5.5, color=DGRAY)

    # ------------------------------------------------------------------ LEGEND
    lg_x = BX1 + 8
    lg_y = LY0 + 8
    txt(page, lg_x, lg_y, "Outcome legend:", size=6.5, color=BLACK, bold=True)
    txt(page, lg_x, lg_y + 11, "✓  likely_pass (illustrative)",  size=6.0, color=GREEN)
    txt(page, lg_x, lg_y + 21, "★1 likely_fail (under min)",    size=6.0, color=RED)
    txt(page, lg_x, lg_y + 31, "★2 needs_more_info (ambiguous)", size=6.0, color=ORANGE)

    # ------------------------------------------------------------------ TITLE BLOCK
    tb_y = PAGE_H - 68
    draw_rect(page, 6, tb_y, PAGE_W - 6, PAGE_H - 6,
              stroke=BLACK, fill=(0.96, 0.96, 0.96), width=0.8)

    txt(page, 14, tb_y + 13,
        "ILLUSTRATIVE TEST DATA — DraftCheck WA M1 Golden Fixture — Single Dwelling, City of Vincent Test Parcel",
        size=9.0, color=RED, bold=True)
    txt(page, 14, tb_y + 25,
        "All values are FICTIONAL and NOT authoritative R-Codes, LPS, or planning scheme values. "
        "For compliance engine testing only.",
        size=6.5, color=BLACK)
    txt(page, 14, tb_y + 36,
        "Approved R-Codes values must be bound from approved source_versions at Stage 3/5. "
        "Hardcoding any illustrative value is a defect (MASTER_REBUILD_PLAN.md §12).",
        size=6.5, color=BLACK)
    txt(page, 14, tb_y + 47,
        "Designed-in non-passes: "
        "★1 Left side setback 0.8m < 1.0m illustrative min → likely_fail   "
        "★2 Boundary wall ~9.5m? scale unverified → needs_more_info",
        size=6.5, color=ORANGE)
    txt(page, 14, tb_y + 58,
        "Generator: data/fixtures/m1/generate_site_plan.py  |  "
        f"Output: {OUTPUT}  |  "
        "CRS ref: GDA2020 (spatial fixtures)  |  Scale: 1:200  |  Paper: A4 landscape",
        size=5.5, color=DGRAY)

    # ------------------------------------------------------------------ SAVE
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output), garbage=4, deflate=True)
    doc.close()

    print(f"Saved: {output}")
    print()
    print("Encoded check outcomes:")
    print("  primary_street_setback : 7.0m  vs 6.0m illustrative min  -> likely_pass")
    print("  left_side_setback      : 0.8m  vs 1.0m illustrative min  -> likely_fail  *1 [designed-in fail]")
    print("  site_cover             : 35%   vs 50% illustrative max   -> likely_pass")
    print("  open_space             : 65%   vs 45% illustrative min   -> likely_pass")
    print("  garage_dominance       : 20%   vs 50% illustrative max   -> likely_pass")
    print("  boundary_wall_length   : ~9.5m? (scale unverified)        -> needs_more_info  *2 [designed-in ambiguous]")


if __name__ == "__main__":
    generate(OUTPUT)
