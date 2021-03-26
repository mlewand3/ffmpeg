$crf=25
$rescale="scale=iw/2:ih/2"

$oldvids = Get-ChildItem -Include *.mp4, *.avi, *.mkv -Recurse

foreach ($oldvid in $oldvids) {
    #$newvid = [io.path]::ChangeExtension($oldvid, '.mp4')
    $newvid = $oldvid.DirectoryName +'\' + $oldvid.BaseName + '_crf' + $crf + '.mp4'
    ffmpeg.exe -i $oldvid -ac 1 -vcodec libx264 -vf $rescale -crf $crf $newvid
}
