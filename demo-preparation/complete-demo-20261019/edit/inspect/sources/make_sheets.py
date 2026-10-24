from PIL import Image, ImageDraw
from pathlib import Path
p=Path('demo-preparation/complete-demo-20261019/edit/inspect/sources')
files=sorted(p.glob('*.png'),key=lambda x:(x.stem.split('-')[0],int(x.stem.split('-')[1])))
for group in ('dash','auth','hist'):
    fs=[f for f in files if f.stem.startswith(group+'-')]
    out=Image.new('RGB',(1000,((len(fs)+1)//2)*300),'#ddd')
    for i,f in enumerate(fs):
        im=Image.open(f).convert('RGB'); im.thumbnail((480,270)); tile=Image.new('RGB',(500,300),'white'); tile.paste(im,((500-im.width)//2,20)); ImageDraw.Draw(tile).text((8,4),f.stem,fill='black'); out.paste(tile,((i%2)*500,(i//2)*300))
    out.save(p/(group+'-sheet.jpg'))
