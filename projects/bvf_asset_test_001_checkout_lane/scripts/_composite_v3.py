"""Composite review board for V3 from main render."""
from PIL import Image, ImageDraw
import sys, os
main_path = sys.argv[1]
upl_dir = sys.argv[2]
main = Image.open(main_path)
W, H = main.size
DW = W // 2
board = Image.new("RGB", (W + DW + 30, H + 50), (28, 28, 28))
draw = ImageDraw.Draw(board)
board.paste(main, (10, 10))
draw.text((16, H + 18), "F001 Lookdev V3 — Full Frame", fill=(230, 230, 230))
c1 = main.crop((0, 0, W, H // 2)).resize((DW, H // 2), Image.LANCZOS)
board.paste(c1, (W + 20, 10))
draw.text((W + 26, H // 2 + 14), "Counter + Employee + Products", fill=(210, 210, 210))
c2 = main.crop((0, H // 2, W, H)).resize((DW, H // 2), Image.LANCZOS)
board.paste(c2, (W + 20, H // 2 + 20))
draw.text((W + 26, H + 14), "Queue + Ground Contact + Direction", fill=(210, 210, 210))
out = os.path.join(upl_dir, "review_board_lookdev_v3.png")
board.save(out, "PNG")
print(f"Review board: {out} ({board.size[0]}x{board.size[1]})")
