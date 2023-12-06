from pyrogram import Client

import feedparser

import wget

import os
import sys

from collections import namedtuple

import eyed3
from eyed3.core import Date as eyed3Date

import ffmpeg

from mutagen.mp3 import MP3

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

import urllib.request

import time
import datetime

from pydub import AudioSegment

YtEntry = namedtuple("YtEntry", "videoId title");

chat_target = "kkk_old"
youtube_channel_id=sys.argv[1:][1]
rss_url=sys.argv[1:][2]
artist_name="Константин Кадавр"
ffmpeg_exec = sys.argv[1:][6]
API_ID=int(sys.argv[1:][4])
API_HASH=sys.argv[1:][5]
app = Client("my_account", API_ID, API_HASH)

MY_FORMAT = '%d.%m.%Y';

def dur_str_to_secs(t):
    list = t.split(':');
    if (len(list) == 3):
        h, m, s = map(int, list);
        return h * 3600 + m * 60 + s;
    else:
        m, s = map(int, list);
        return m * 60 + s;

def trim_audio(filename, cut_start_str):
    temp_name = 'AudioSegment_temp_' + filename;
    os.rename(filename, temp_name);
    song = AudioSegment.from_mp3(temp_name);
    ms = dur_str_to_secs(cut_start_str) * 1000;
    song[ms:].export(filename, format="mp3");

def remove_silence(filename, output):
    # Trim all silence encountered from beginning to end where there is more than 1 second of silence in audio:
    # silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-90dB
    silence_args = 'stop_periods=-1:stop_duration=3:stop_threshold=-90dB';
    (
        ffmpeg
        .input(filename)
        .output(output, af=f'silenceremove={silence_args}')
        .run()
    )

    return output;

def duration_seconds(filename):
    audio = MP3(filename);
    audio_info = audio.info;
    return int(audio_info.length);

def read_last_messages():
    captions = list();
    with app:
        counter = 0;
        for message in app.get_chat_history(chat_target):
            counter = counter + 1;
            if counter > 100:
                break;
            if (message.caption is not None and len(message.caption) > 0):
                captions.append(message.caption);
    return captions;

def find_not_uploaded(last_captions):
    yt_entries = list();
    d = feedparser.parse(f'https://www.youtube.com/feeds/videos.xml?channel_id={youtube_channel_id}')
    for entry in d['entries']:
        yt_entry = YtEntry(videoId=entry['yt_videoid'], title=entry['title']);

        ignore_entry = False;
        for caption in last_captions:
            if yt_entry.videoId in caption:
                print(f'Ignore video: {yt_entry.title}');
                ignore_entry = True;
                break;
        if ignore_entry:
            continue;

        yt_entries.append(yt_entry);
        print(yt_entry.videoId);
    return yt_entries

def download_single(videoId):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{videoId}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download(videoId)
        return f'{videoId}.mp3'

def download_single_vk(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'vk.mp4',
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download(url)
        return 'vk.mp4'

def download_last_tagged_audio():
    filename = "tagged_audio.mp3";
    if os.path.isfile(filename):
        return filename;
    d = feedparser.parse(rss_url)
    for itemLink in d['items'][0]['links']:
        if itemLink['href'].endswith('.mp3'):
            return wget.download(itemLink['href'], out=filename);

def extract_cover(filename):
    file_non_tagged = eyed3.load(filename);
    file_cover = os.path.splitext(filename)[0] + '.jpg';
    for img in file_non_tagged.tag.images:
        if img.mime_type not in eyed3.id3.frames.ImageFrame.URL_MIME_TYPE_VALUES:
            with open(file_cover, "wb") as fp:
                fp.write(img.image_data)
                return file_cover;

def run_ffmpeg(filename, cut_start_str, out):
    print(ffmpeg_exec);
    silence_args = 'stop_periods=-1:stop_duration=3:stop_threshold=-90dB';
    silence = f'-af "silenceremove={silence_args}"';
    cmd = f'{ffmpeg_exec} -i {filename} -b:a 128K -vn {silence} -ss {cut_start_str} {out}';
    os.system(cmd);

def download_tag_upload(url, title, date_str, season, episode, cut_start_str):
    def nice_title():
        episode_str = "{:03d}".format(episode);
        space = ' ' if (len(title) > 0) else '';
        return f'{title}{space}s0{season}e{episode_str}';
    title = nice_title();

    nice_name = f'{artist_name} — {title}.mp3';
    temp_name = 'out.mp3';
    if type(url) is list and len(url) == 2:
        u1 = url[0];
        u2 = url[1];
        f1 = download_single_vk(u1) if ('vk.com' in u1) else download_single(u1);
        f2 = download_single_vk(u2) if ('vk.com' in u2) else download_single(u2);
        run_ffmpeg(f1, cut_start_str, 'out1.mp3');
        run_ffmpeg(f2, '00:00', 'out2.mp3');
        os.system(f'{ffmpeg_exec} -f concat -i list_to_concat.txt -c copy {temp_name}');
    elif type(url) is list and len(url) == 3:
        u1 = url[0];
        u2 = url[1];
        u3 = url[2];
        f1 = download_single_vk(u1) if ('vk.com' in u1) else download_single(u1);
        f2 = download_single_vk(u2) if ('vk.com' in u2) else download_single(u2);
        f3 = download_single_vk(u3) if ('vk.com' in u3) else download_single(u3);
        run_ffmpeg(f1, cut_start_str, 'out1.mp3');
        run_ffmpeg(f2, '00:00', 'out2.mp3');
        run_ffmpeg(f3, '00:00', 'out3.mp3');
        os.system(f'{ffmpeg_exec} -f concat -i list_to_concat_three.txt -c copy {temp_name}');
    elif type(url) is list and len(url) == 4:
        u1 = url[0];
        u2 = url[1];
        u3 = url[2];
        u4 = url[3];
        f1 = download_single_vk(u1) if ('vk.com' in u1) else download_single(u1);
        f2 = download_single_vk(u2) if ('vk.com' in u2) else download_single(u2);
        f3 = download_single_vk(u3) if ('vk.com' in u3) else download_single(u3);
        f4 = download_single_vk(u4) if ('vk.com' in u4) else download_single(u4);
        run_ffmpeg(f1, cut_start_str, 'out1.mp3');
        run_ffmpeg(f2, '00:00', 'out2.mp3');
        run_ffmpeg(f3, '00:00', 'out3.mp3');
        run_ffmpeg(f4, '00:00', 'out4.mp3');
        os.system(f'{ffmpeg_exec} -f concat -i list_to_concat_four.txt -c copy {temp_name}');
    else:
        file_name = download_single_vk(url) if ('vk.com' in url) else download_single(url);
        run_ffmpeg(file_name, cut_start_str, temp_name);
    # trim_audio(file_name, cut_start_str);
    # temp_name = remove_silence(file_name, "temp" + file_name);

    timestamp = time.mktime(time.strptime(date_str, MY_FORMAT))
    os.utime(temp_name, (int(timestamp), int(timestamp)))
    os.rename(temp_name, file_name);

    total_in_season = 0;
    if (season == 2):
        total_in_season = 71

    file_non_tagged = eyed3.load(file_name);
    # file_non_tagged.tag = eyed3.load(download_last_tagged_audio()).tag;
    file_non_tagged.tag._setDiscNum(season);
    file_non_tagged.tag._setTrackNum((episode, total_in_season));
    file_non_tagged.tag._setTitle(title);
    file_non_tagged.tag._setArtist(artist_name);
    file_non_tagged.tag._setGenre('Podcast');
    file_non_tagged.tag._setAlbum('Подкаст Константина Кадавра');
    file_non_tagged.tag._setRecordingDate(
        eyed3Date(
            year=datetime.datetime.strptime(date_str, MY_FORMAT).year,
            month=datetime.datetime.strptime(date_str, MY_FORMAT).month,
            day=datetime.datetime.strptime(date_str, MY_FORMAT).day));

    response = urllib.request.urlopen("https://i1.sndcdn.com/avatars-000389125830-pz2jps-t500x500.jpg");
    imagedata = response.read();
    file_non_tagged.tag.images.set(3, imagedata, "image/jpeg", u"cover");

    file_non_tagged.tag.save();

    cover_file_name = extract_cover(file_name);
    time_secs = duration_seconds(file_name);

    print("Uploading...");
    print(f'audio file = {nice_name}');
    print(f'duration = {time_secs}');
    print(f'performer = {file_non_tagged.tag.artist}');
    print(f'title = {file_non_tagged.tag.title}');
    print(f'cover_file_name = {cover_file_name}');

    os.rename(file_name, nice_name);

    with app:
        app.send_audio(
            chat_id=chat_target,
            audio=nice_name,
            caption=f'{date_str}.',
            duration=time_secs,
            performer=file_non_tagged.tag.artist,
            title=file_non_tagged.tag.title,
            thumb=cover_file_name);

def check_is_video_good(videoId):
    with YoutubeDL({ 'quiet': True }) as ydl:
        try:
            result = ydl.extract_info(
                url=videoId,
                download=False,
                extra_info={ 'live_status' : True });
            if result['is_live']:
                return False;
            if result['was_live']:
                return True;
        except DownloadError:
          return False;
        except:
          return False;
    return False;

episode_counter = 1;
download_tag_upload(
    # 'https://vk.com/video-72495291_456239592', # Test.
    'https://vk.com/video-72495291_456239518',
    'Сценарий к фильму',
    '13.12.2016',
    2,
    episode_counter,
    '02:15');
episode_counter = episode_counter + 1;

download_tag_upload(
    ['https://vk.com/video-72495291_456239538', 'https://vk.com/video-72495291_456239539'],
    'Щячло снова на экране',
    '17.12.2016',
    2,
    2,
    '03:10');
episode_counter = episode_counter + 1;

download_tag_upload(
    ['https://vk.com/video-72495291_456239565', 'https://vk.com/video-72495291_456239564'],
    'Паром дом дом',
    '18.12.2016',
    2,
    episode_counter,
    '02:30');
episode_counter = episode_counter + 1;

download_tag_upload(
    'https://vk.com/video-72495291_456239569',
    'Каикакака (КиККК)',
    '19.12.2016',
    2,
    episode_counter,
    '03:30');
episode_counter = episode_counter + 1;

download_tag_upload(
    'https://vk.com/video-72495291_456239577',
    'Харкотина на еботине',
    '22.12.2016',
    2,
    episode_counter,
    '04:10');
episode_counter = episode_counter + 1;

download_tag_upload(
    [
        'https://vk.com/video-72495291_456239603',
        'https://vk.com/video-72495291_456239601',
        'https://vk.com/video-72495291_456239606'
    ],
    'Курдючный жмых',
    '10.01.2017',
    2,
    episode_counter,
    '02:40');
episode_counter = episode_counter + 1;

download_tag_upload(
    ['https://vk.com/video-72495291_456239605', 'https://vk.com/video-72495291_456239604'],
    'Лилу Даллас Мульти Пасс',
    '11.01.2017',
    2,
    episode_counter,
    '01:56');
episode_counter = episode_counter + 1;

download_tag_upload(
    [
        'https://vk.com/video-72495291_456239610',
        'https://vk.com/video-72495291_456239609',
        'https://vk.com/video-72495291_456239608',
        'https://vk.com/video-72495291_456239607'
    ],
    '(Кузьма) Ускорение горизонтального падения',
    '12.01.2017',
    2,
    episode_counter,
    '01:27');
episode_counter = episode_counter + 1;

download_tag_upload(
    [
        'https://vk.com/video-72495291_456239613',
        'https://vk.com/video-72495291_456239612',
        'https://vk.com/video-72495291_456239611'
    ],
    'Последний довод бегемотика',
    '13.01.2017',
    2,
    episode_counter,
    '08:40');
episode_counter = episode_counter + 1;

download_tag_upload(
    'https://vk.com/video-72495291_456239618',
    'Бертольдт Брехун',
    '15.01.2017',
    2,
    episode_counter,
    '02:10');
episode_counter = episode_counter + 1;

# yt_entries = find_not_uploaded(read_last_messages());
# for yt_entry in reversed(yt_entries):
#     if check_is_video_good(yt_entry.videoId):
#         download_tag_upload(yt_entry);
