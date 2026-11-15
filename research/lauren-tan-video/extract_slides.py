from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json, subprocess

root=Path('/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g')
slides=[
 (25,'Title'),(36,'Our craft and their slop'),(45,'Personal PR volume'),
 (60,'Quality and quantity'),(85,'Trust enables scale'),(95,'Low trust loop'),
 (110,'High trust loop'),(125,'The poteto pyramid'),(185,'Code is memory'),
 (215,'Codebase as a garden'),(245,'Organic architecture'),(270,'Copying workarounds'),
 (295,'Read the code sometimes'),(310,'Dune framework'),(345,'Nuance and API design'),
 (395,'Directory structure as context'),(425,'Unsolicited markdown'),(460,'Quick fixes and timers'),
 (510,'Comments are liabilities'),(560,'Corrections become checks'),(590,'Verification matters'),
 (620,'Runtime feature map'),(645,'Feature map and CLI'),(670,'TLA+ and Lean'),
 (700,'UI property based testing'),(715,'Subtle bugs and manual verification'),
 (730,'Verification token spend'),(755,'Testing across the lifecycle'),(785,'Statechart'),
 (805,'Results transition'),(820,'Team PR volume'),(830,'Desktop releases'),
 (840,'Contributor distribution'),(860,'Revert rate'),(890,'Performance measurements'),
 (920,'Foundations revisited'),(935,'Should I build a factory'),(955,'Improve the inner loop'),
 (965,'Automated triggers'),(975,'Grok Bot outer loop'),(995,'Release fuzzing report'),
 (1025,'Closing')]
(root/'slides').mkdir(exist_ok=True)
def extract(item):
    i,(seconds,title)=item
    filename=f'{i:02d}-{seconds:04d}.jpg'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(seconds),'-i',str(root/'O_zcc6Xl12g.mp4'),'-frames:v','1','-vf','crop=1472:828:432:15','-q:v','2','-y',str(root/'slides'/filename)],check=True)
    return {'number':i,'seconds':seconds,'timestamp':f'{seconds//60}:{seconds%60:02}','title':title,'image':filename}
with ThreadPoolExecutor(max_workers=4) as pool:
    manifest=list(pool.map(extract,enumerate(slides,1)))
(root/'slides.json').write_text(json.dumps(manifest,indent=2))
print(f'Extracted {len(manifest)} readable slides/builds to {root}/slides')
