import os
import glob
import subprocess

os.chdir(r'C:\Users\AVICON\Desktop\Studia')

exts = ['*.mkv', '*.avi', '*.mp4']
files = [f for ext in exts for f in glob.glob(os.path.join(r'./*/*/', ext))]

for in_f in files:
    out_f = in_f.replace('ł', 'l').replace('\\Wyklady\\', '-')
    print(f'{in_f} -> {out_f}')
    subprocess.call(f'ffmpeg -i {in_f} -ac 1 -vsync vfr -vf mpdecimate,scale=iw/2:ih/2 {out_f}', shell=True)

