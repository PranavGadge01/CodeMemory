from PIL import Image, ImageDraw
from pathlib import Path
p = Path('demo-preparation/complete-demo-20261019/edit/inspect')
fs = sorted(p.glob('frame-*.png'), key=lambda x: int(x.stem.split('-')[1]))
thumbs = []
for f in fs:
    im = Image.open(f).convert('RGB')
    im.thumbnail((480, 270))
    canvas = Image.new('RGB', (500, 300), 'white')
    canvas.paste(im, ((500-im.width)//2, 20))
    ImageDraw.Draw(canvas).text((8, 4), f.stem, fill='black')
    thumbs.append(canvas)
out = Image.new('RGB', (1000, 1800), '#ddd')
for i, im in enumerate(thumbs):
    out.paste(im, ((i % 2)*500, (i // 2)*300))
out.save(p / 'contact-sheet.jpg')
