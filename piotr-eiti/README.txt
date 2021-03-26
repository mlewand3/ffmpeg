For input NAN 2021-02-25_15-00-56.mkv file

00 295561 KB input file
01 147581 KB just re encoded with ffmpeg with default settings
02  94653 KB additional downsampled by factor of 1
03  68744 KB additional converted audio to mono channel
04  35710 KB additional flags variable framerate and mpdecimate: https://video.stackexchange.com/a/25003
05  36591 KB additional tune for stillimage preset used
06  35760 KB new tune for animation preset used
07  35748 KB removed tune, psy-rd=2 used
08  35872 KB removed psy-rd, hqdn3d used

I do not use H265, because I prefer H264 for:
- compatibility
- faster decode/encode for older devices
- IMO less artifacts

frames-mono.png shows that there are a lot of I-Frames which are not needed
See the source for reconstruction:
https://github.com/jina-jyl/jupyter/blob/master/video-stream-analysis-demo.ipynb

Finally:

ffmpeg.exe -i .\2021-02-25_15-00-56.mkv -ac 1 -vsync vfr -vf mpdecimate,scale=iw/2:ih/2 .\2021-02-25_15-00-56-final.mp4


For all 36 files:
12.0 GB -> 1.8 GB

