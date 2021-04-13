import sys
import os
import re
import time
import typing
import shutil
import logging
import datetime as dt
from dateutil.parser import parse
import subprocess
from logging.config import dictConfig
from PIL import Image
from PIL.ExifTags import TAGS
from videoprops import get_video_properties, get_audio_properties

"""See more: https://docs.python-guide.org/writing/logging/"""
logging_config = dict(
    version=1,
    formatters={
        'sf': {'format': '%(asctime)s [%(levelname)-7.7s] %(message)s'},
        'ff': {'format': '%(asctime)s [%(levelname)-7.7s] %(message)s'}
    },
    handlers={
        'sh': {'class': 'logging.StreamHandler',
               'formatter': 'sf',
               'level': logging.DEBUG},
        'fh': {'class': 'logging.handlers.RotatingFileHandler',
               'encoding': 'utf-8',
               'filename': 'reorganize-media.log',
               'maxBytes': 5 * 1024 * 1024,
               'backupCount': 10,
               'formatter': 'ff',
               'level': logging.DEBUG}
    },
    root={
        'handlers': ['sh', 'fh'],
        'level': logging.DEBUG,
    },
)

dictConfig(logging_config)
log = logging.getLogger(__name__)

override = None  # '20180630'


def print_msg(msg: str, explanation: str = '') -> None:
    """Helper function to log information"""
    additional = f' [{explanation}]' if explanation else ''
    log.info(f'{" "*len("[  4d/  4d]")} {msg:25s}{additional}')


def optimize_jpg(file_path: str) -> None:
    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(file_path)
    img = Image.open(file_path)
    exif = img.info['exif']
    high_quality = 1
    if img.size[0] * img.size[1] > 2 * 1024 * 1024 * high_quality or size > 1000 * 1500 * high_quality:
        new_img_size = (img.size[0]//2, img.size[1]//2)
        new_img = img.resize(new_img_size, resample=Image.LANCZOS)
        new_img.save(filepath, exif=exif)
        #(mode, ino, dev, nlink, uid, gid, new_size, atime, mtime, ctime) = os.stat(file_path)
        log.info(f'             Resize [{img.size}] {size/1024:.1f}KB -> [{new_img.size}] {new_size/1024:.1f}KB')
    else:
        print_msg('Size OK', f'[{img.size}] {size/1024:.1f}KB')
    img.close()


def rename_jpg(filepath: str) -> str:
    img = Image.open(filepath)
    exif_data = img._getexif()
    datetaken = None
    if exif_data is None:
        log.warning(f'No EXIF Data in: {filepath}')
        return
    for k, v in exif_data.items():
        if k in TAGS:
            if TAGS[k] == "DateTimeOriginal":
                datetaken = v
                break
    img.close()

    if datetaken is None:
        log.warning(f'No DataTime EXIF Token in:{filepath}')
    else:
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        additional = ''  # extract_additional(filename)  # onlytest
        filetime = datetaken.replace(':', '').replace(' ', '_')
        new_filepath = os.path.join(directory, filetime + additional + '.jpg')
        if filepath != new_filepath:
            log.info(f'Rename {filename} -> {new_filepath}')
            try:
                os.rename(filepath, new_filepath)
            except Exception as ex:
                log.error('Cannot rename file. Probably duplicated datetime (including seconds)')
                os.rename(filepath, new_filepath.replace('.jpg', ' _1.jpg'))  # TODO: increase seconds number?
            return new_filepath
        else:
            print_msg('name OK')
    return filepath


def process_jpg_impl(filepath: str) -> None:
    new_filepath = rename_jpg(filepath)
    optimize_jpg(new_filepath)


def perform_renaming(old_file_name: str, new_file_name: str, current_directory: str) -> None:
    old_file_path = os.path.join(current_directory, old_file_name)
    new_file_path = os.path.join(current_directory, new_file_name)
    log.info(f'Rename {old_file_name} -> {new_file_name}')
    try:
        os.rename(old_file_path, new_file_path)
    except Exception as ex:
        log.error(f'Cannot rename: {ex}')


def rename_mp4(file_path: str) -> str:
    #(mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(filepath)
    base_name = os.path.basename(file_path)
    old_file_name, extension = os.path.splitext(base_name)
    current_directory = os.path.dirname(file_path)
    if old_file_name.startswith('VID_') or old_file_name.startswith('PXL_'):
        new_file_name = old_file_name[4:]
    else:
        new_file_name = old_file_name

    if re.match('[0-9]{8}_[0-9]{9}', new_file_name):
        new_file_name = new_file_name[:15]

    perform_renaming(old_file_name + extension, new_file_name + extension, current_directory)

    return os.path.join(current_directory, new_file_name + extension)


def set_meta_mp4(filepath: str) -> None:
    stinfo = os.stat(filepath)
    file_name = os.path.basename(filepath)
    actual_time = get_ntime(file_name)
    base_time = ''
    if not actual_time:
        actual_time = get_mtime(filepath)
        base_time = timestamp_to_name(actual_time)

    vid_props = get_video_properties(filepath)
    try:
        aud_props = get_audio_properties(filepath)
        channels = aud_props["channels"]
    except RuntimeError as ex:
        log.warning(ex)
        channels = 0
    #print(vid_props['tags']['creation_time'])
    bitrate = int(vid_props["bit_rate"]) // 1024
    log.debug(f'{bitrate=}kBs {channels=}')
    if bitrate > 400:
        flags = '-ac 1 -vcodec libx264 -vf "scale=iw/2:ih/2" -crf 25'
        t = 'compress'
    else:
        if channels == 0:
            flags = '-codec copy'
            t = 'copy'
        elif channels == 1:
            flags = '-codec copy'
            t = 'copy'
        elif channels == 2:
            flags = '-ac 1 -c:v copy'
            t = 'audio'
        else:
            raise RuntimeError(f'Strange channels count: {channels}')
    ctime = dt.datetime.fromtimestamp(actual_time)
    #if override:
    #    ctime.replace(year=2018, month=6, day=30)
    cmd = f'ffmpeg -i "{filepath}" -metadata creation_time="{ctime}" {flags} -y tmp.mp4'
    log.debug(' '*12 + f'Call: {cmd}')
    completed = subprocess.run(cmd, capture_output=True)
    if completed.returncode != 0:
        log.error(f'Problem retcode={completed.returncode} with: {cmd}')
    if t == 'compress':
        for line in completed.stderr.decode("utf-8").splitlines():
            log.debug(' '*12 + 'stderr>' + line)
        for line in completed.stdout.decode("utf-8").splitlines():
            log.debug(' '*12 + 'stdout>' + line)
    if base_time:
        directory = os.path.dirname(filepath)
        file_name = base_time + " " + file_name
        new_filepath = os.path.join(directory, file_name)
    else:
        new_filepath = filepath

    new_filepath = new_filepath.replace('.avi', '.mp4')
    # TODO: Add _crf25
    if not '_crf25' in new_filepath:
        new_filepath = new_filepath.replace('.mp4', '_crf25.mp4')
    
    #if override:
    #    new_filepath = override_filepath(new_filepath)
    shutil.move('tmp.mp4', new_filepath)
    # Keep accesstime, change modifiedtime
    os.utime(filepath, (stinfo.st_atime, actual_time))


def process_mp4_impl(filepath: str) -> None:
    if '_crf25' in filepath:
        print_msg('file OK', 'already converted')
        return
    else:
        print_msg('Will convert')
        new_filepath = rename_mp4(filepath)
        set_meta_mp4(filepath)


def process_jpg(filepath: str) -> None:
    try:
        process_jpg_impl(filepath)
    except Exception as ex:
        log.error(f'Exception during {filepath} : {ex}')


def process_mp4(filepath: str) -> None:
    try:
        process_mp4_impl(filepath)
    except Exception as ex:
        log.error(f'Exception during {filepath} : {ex}')


def get_ctime(filepath: str) -> int:
    """Get creation time of the file"""
    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(filepath)
    return ctime


def get_mtime(filepath: str) -> int:
    """Get modification time of the file"""
    (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(filepath)
    return mtime


def get_ntime(filepath: str) -> typing.Union[None, float]:
    """Get (file)name time of the file

    20201012_120030 -> float
    """
    filename = os.path.basename(filepath)
    filename_date = os.path.splitext(filename)[0]
    try:
        filename_date_obj = dt.datetime.strptime(filename_date[:15], '%Y%m%d_%H%M%S')
    except ValueError as er:
        log.warning(f'Cannot parse {filename_date} to datetime')
        log.warning(f'Trying fuzzy')
        try:
            filename_date_obj = parse(filename_date, fuzzy=True)
        except ValueError as er:
            log.warning(f'Even fuzzy matching does not work')
            return None
    return filename_date_obj.timestamp()


def timestamp_to_name(timestamp: float) -> str:
    dt_object = dt.datetime.fromtimestamp(timestamp)
    return dt_object.strftime('%Y%m%d_%H%M%S')


def extract_additional(filename: str) -> str:
    basename = os.path.splitext(filename)[0]
    return basename[15:]


def rename_basing_on_time(filepath: str, new_time) -> None:
    filename = os.path.basename(filepath)
    additional = '' #extract_additional(filename)
    ntime = get_ntime(filepath)
    if not ntime:        ntime = sys.maxsize
    if new_time < ntime:
        directory = os.path.dirname(filepath)
        extension = os.path.splitext(filename)[-1]
        new_filename = timestamp_to_name(new_time) + additional + extension
        new_filepath = os.path.join(directory, new_filename)
        log.info(f'Rename {filename} -> {new_filename}')
        os.rename(filepath, new_filepath)


def process_generic_impl(filepath: str) -> None:
    new_time = get_mtime(filepath)
    rename_basing_on_modification_time(filepath, new_time)


def process_generic(filepath: str) -> None:
    try:
        process_generic_impl(filepath)
    except Exception as ex:
        log.error(f'Exception during {filepath} : {ex}')


def process_none(filepath: str) -> None:
    filename = os.path.basename(filepath)
    print_msg('file OK', 'not JPEG or MP4 file')


def choose_process_function(filename: str) -> typing.Callable:
    name = filename.lower()
    if name.endswith('.jpg') or name.endswith('.jpeg'):
        return process_jpg
    elif name.endswith('.mp4') or name.endswith('.avi'):
        return process_mp4
    elif name.endswith('.gif'):
        return process_generic
    else:
        return process_none


pwd = os.getcwd()
log.debug(f'pwd: {pwd}')

if ffmpeg_exe := shutil.which('ffmpeg'):
    # TODO: also *.avi, *.mkv
    log.debug(f'ffmpeg executable found in: {ffmpeg_exe}')
    ffmpeg_cmd = """$newvid = $oldvid.DirectoryName +'\' + $oldvid.BaseName + '_crf' + $crf + '.mp4'
                    {ffmpeg_exe} -i $oldvid -ac 1 -vcodec libx264 -vf "scale=iw/2:ih/2" -crf 25 $newvid"""
else:
    log.error('No ffmpeg executable found')

# TODO: Implement arbitrary directory
directory_to_process = '.'

total = sum([len(files) for root, dirs, files in os.walk(directory_to_process)])
log.debug(f'Total files count: {total}')

idx = 0
for root, dirs, files in os.walk(directory_to_process, topdown=True):
    for filename in files:
        input_filepath = os.path.join(pwd, root, filename)
        idx += 1
        log.info(f'[{idx:4d}/{total:4d}] {filename:25s} ( {input_filepath} )')
        process_function = choose_process_function(filename)
        process_function(input_filepath)
