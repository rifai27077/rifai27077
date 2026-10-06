import html
import os
import sys
from PIL import Image, ImageEnhance

# Path foto input & file output SVG
SRC = "muka.PNG"  # ganti dengan path foto Anda
OUT = "rifai-ascii.svg"

# Parameter Resolusi ASCII
COLS = 180  # jumlah karakter horizontal (180 pas untuk detail mata)
ART_W_TARGET = 800
CELL_W = ART_W_TARGET / COLS
CELL_H = CELL_W * 15 / 8
ROWS = round(COLS * 8 / 15)

# Urutan karakter dari terang (spasi) ke gelap (@)
RAMP = " .`:-=+*cs#%@"

# Penyetelan Tone & Kontras Wajah
CONTRAST = 1.25  # menaikkan kontras agar garis mata/rambut tegas
BRIGHTNESS = 1.0
GAMMA = 1.15  # > 1 agar kulit wajah tetap bersih/tidak terlalu hitam
WHITE_FLOOR = 0.88  # bagian yang sangat terang/background dipaksa jadi spasi

PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"  # Warna background GitHub Dark
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"  # Warna teks ASCII monochrome
CURSOR = "#c9d1d9"

# Durasi animasi typing (total ~5.8 detik)
ROW_DUR = 5.8 / ROWS
STAGGER = ROW_DUR

# 1. Buka foto, ubah ke grayscale dan resize
im = Image.open(SRC).convert("L")
im = ImageEnhance.Brightness(im).enhance(BRIGHTNESS)
im = ImageEnhance.Contrast(im).enhance(CONTRAST)
im = im.resize((COLS, ROWS), Image.LANCZOS)
px = im.load()

# 2. Konversi piksel menjadi baris teks ASCII
rows_txt = []
for y in range(ROWS):
  chars = []
  for x in range(COLS):
    lum = px[x, y] / 255.0
    lum = pow(lum, GAMMA)
    if lum >= WHITE_FLOOR:
      chars.append(" ")
      continue
    idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
    idx = max(0, min(len(RAMP) - 1, idx))
    chars.append(RAMP[idx])
  rows_txt.append("".join(chars))

art_top = TITLEBAR_H + PAD * 0.35

# 3. Rakit SVG dengan animasi SMIL
parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}"'
    f' height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}"'
    ' font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
)
parts.append(
    '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1"'
    f' stop-color="{BG}"/></linearGradient></defs>'
)
parts.append(
    f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>'
)
parts.append(
    f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12"'
    f' fill="none" stroke="{FRAME}" stroke-width="1"/>'
)
parts.append(
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}"'
    f' stroke="{FRAME}"/>'
)

# Tombol window ala macOS (merah, kuning, hijau)
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
  parts.append(
      f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>'
  )
parts.append(
    f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}"'
    ' font-size="12" text-anchor="middle">rifai@github: ~$ ./portrait.sh</text>'
)

font_size = CELL_H * 0.86
for ry, line in enumerate(rows_txt):
  y = art_top + ry * CELL_H + CELL_H * 0.74
  row_y = art_top + ry * CELL_H
  delay = ry * STAGGER
  safe = html.escape(line)
  text = (
      f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}"'
      f' font-size="{font_size:.1f}" textLength="{ART_W}"'
      f' lengthAdjust="spacing">{safe}</text>'
  )

  # Reveal per baris
  parts.append(
      f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}"'
      ' width="0"><animate attributeName="width" from="0"'
      f' to="{ART_W}" begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s"'
      ' fill="freeze"/></rect></clipPath>'
  )
  parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')

  # Balok kursor yang bergerak
  parts.append(
      f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}"'
      f' fill="{CURSOR}" opacity="0"><animate attributeName="x" from="{PAD}"'
      f' to="{PAD+ART_W}" begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s"'
      ' fill="freeze"/><set attributeName="opacity" to="0.85"'
      f' begin="{delay:.3f}s"/><set attributeName="opacity" to="0"'
      f' begin="{delay+ROW_DUR:.3f}s"/></rect>'
  )

# Baris status bawah dengan kursor berkedip
status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y = status_line_y + 19
parts.append(
    f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}"'
    f' y2="{status_line_y:.1f}" stroke="{FRAME}"/>'
)
parts.append(
    f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}"'
    ' font-size="13">rifai@github:~$ whoami <tspan fill="{INK}">Ahmad'
    ' Rifai</tspan></text>'
)
status_chars = len("rifai@github:~$ whoami Ahmad Rifai ")
parts.append(
    f'<rect x="{PAD + status_chars * 13 * 0.6:.1f}" y="{status_y-12:.1f}"'
    f' width="8" height="14" fill="{INK}"><animate attributeName="opacity"'
    ' values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s"'
    ' repeatCount="indefinite"/></rect>'
)

parts.append("</svg>")
svg = "".join(parts)
with open(OUT, "w") as f:
  f.write(svg)
print("Selesai! File tersimpan di:", OUT)
