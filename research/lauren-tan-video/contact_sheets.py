from pathlib import Path
from PIL import Image, ImageDraw
import re

root = Path('/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g')
files = sorted((root / 'frames').glob('sample-*.jpg'))
for start in range(0, len(files), 20):
    batch = files[start:start+20]
    sheet = Image.new('RGB', (1280, ((len(batch)+1)//2)*384), 'white')
    draw = ImageDraw.Draw(sheet)
    for j, path in enumerate(batch):
        frame = Image.open(path)
        x, y = (j % 2)*640, (j//2)*384
        sheet.paste(frame, (x,y+24))
        seconds = (start+j)*10+5
        draw.text((x+8,y+4), f'{seconds//60:02}:{seconds%60:02} | {path.name}', fill='black')
    sheet.save(root / f'contact-{start//20+1:02}.jpg', quality=90)

times = [float(x) for x in re.findall(r'pts_time:([\d.]+)', (root/'scene-log.txt').read_text())]
files = sorted((root/'frames').glob('scene-*.jpg'))
for start in range(0, len(files), 20):
    batch=files[start:start+20]
    sheet=Image.new('RGB',(1280,((len(batch)+1)//2)*384),'white')
    draw=ImageDraw.Draw(sheet)
    for j,path in enumerate(batch):
        frame=Image.open(path).resize((640,360))
        x,y=(j%2)*640,(j//2)*384
        sheet.paste(frame,(x,y+24))
        sec=times[start+j]
        draw.text((x+8,y+4),f'{int(sec)//60:02}:{sec%60:04.1f} | {path.name}',fill='black')
    sheet.save(root/f'scenes-{start//20+1:02}.jpg',quality=90)
