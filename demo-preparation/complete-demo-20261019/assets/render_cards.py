from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
FONT = Path(r"C:\Windows\Fonts\arial.ttf")
BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")
BG = (248, 248, 246)
INK = (25, 26, 27)
MUTED = (100, 102, 106)
ORANGE = (242, 161, 11)
PALE = (255, 240, 216)
BORDER = (226, 227, 223)


def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), size)


def spaced(draw, xy, text, typeface, fill, spacing=3):
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=typeface, fill=fill)
        x += draw.textlength(char, font=typeface) + spacing


def logo(draw, x, y):
    draw.rounded_rectangle((x, y, x + 58, y + 58), 15, fill=PALE)
    draw.line((x + 17, y + 15, x + 17, y + 43), fill=ORANGE, width=4)
    draw.line((x + 17, y + 22, x + 42, y + 22), fill=ORANGE, width=4)
    draw.line((x + 17, y + 36, x + 42, y + 36), fill=ORANGE, width=4)
    draw.line((x + 37, y + 22, x + 44, y + 29, x + 37, y + 36), fill=ORANGE, width=4, joint="curve")
    draw.ellipse((x + 13, y + 11, x + 21, y + 19), fill=ORANGE)
    draw.ellipse((x + 13, y + 39, x + 21, y + 47), fill=ORANGE)


def intro():
    im = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(im)
    d.ellipse((1180, -180, 1900, 540), fill=PALE)
    d.line((0, 872, 1920, 872), fill=(231, 231, 226), width=2)
    logo(d, 240, 332)
    d.text((324, 344), "CODEMEMORY", font=font(26, True), fill=(37, 37, 37))
    d.rounded_rectangle((240, 474, 326, 481), 4, fill=ORANGE)
    d.text((240, 526), "Your coding history,", font=font(92, True), fill=INK)
    d.text((240, 631), "remembered.", font=font(92, True), fill=INK)
    d.text((245, 746), "Connect your LeetCode history to what you learn next.", font=font(30), fill=MUTED)
    spaced(d, (240, 946), "A PRODUCT WALKTHROUGH", font(19), (119, 122, 125), 3)
    im.save(OUT / "intro.png")


def outro():
    im = Image.new("RGB", (1920, 1080), BG)
    d = ImageDraw.Draw(im)
    d.ellipse((-40, 660, 800, 1500), fill=PALE)
    logo(d, 240, 210)
    d.text((324, 222), "CODEMEMORY", font=font(26, True), fill=(37, 37, 37))
    d.text((240, 356), "Connect. Import. Revisit.", font=font(70, True), fill=INK)
    d.text((244, 456), "Make past coding work easier to find and learn from.", font=font(30), fill=MUTED)
    cards = [(240, "01", "Connect a profile"), (728, "02", "Import history"), (1216, "03", "Learn from it")]
    for x, number, label in cards:
        d.rounded_rectangle((x, 640, x + 390, 790), 18, fill=(255, 255, 255), outline=BORDER, width=2)
        spaced(d, (x + 32, 665), number, font(18), (133, 135, 138), 2)
        d.text((x + 32, 714), label, font=font(30, True), fill=(34, 36, 38))
    for x in (638, 1126):
        d.line((x, 715, x + 45, 715), fill=ORANGE, width=3)
        d.line((x + 33, 704, x + 45, 715, x + 33, 726), fill=ORANGE, width=3, joint="curve")
    spaced(d, (240, 946), "CODEMEMORY · PRODUCT DEMO", font(19), (119, 122, 125), 3)
    im.save(OUT / "outro.png")


if __name__ == "__main__":
    intro()
    outro()
