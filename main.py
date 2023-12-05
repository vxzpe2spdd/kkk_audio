from pyrogram import Client

import feedparser

import wget

import os
import sys

from collections import namedtuple

import eyed3

import ffprobe3
import ffmpeg

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

YtEntry = namedtuple("YtEntry", "videoId title");

chat_target = sys.argv[1:][0]
youtube_channel_id=sys.argv[1:][1]
rss_url=sys.argv[1:][2]
artist_name=sys.argv[1:][3]
API_ID=int(sys.argv[1:][4])
API_HASH=sys.argv[1:][5]
app = Client("my_account", API_ID, API_HASH)

def remove_silence(filename, output):
    silence_args = '1:5:-45dB';
    bundle = (
        ffmpeg
        .input(filename)
        .output(output, af=f'silenceremove={silence_args}')
    )

    ffmpeg.run(bundle);
    return output;

def duration_seconds(filename):
    result = int(0);
    for stream in ffprobe3.probe(filename).streams:
        seconds = stream.duration_secs();
        if (seconds > 0):
            result = int(seconds);
            break;
    return result;

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

def download_tag_upload(yt_entry):
    nice_name = f'{artist_name} — {yt_entry.title}.mp3';
    file_name = download_single(yt_entry.videoId);
    temp_name = remove_silence(file_name, "temp" + file_name);
    os.rename(temp_name, file_name);

    file_non_tagged = eyed3.load(file_name);
    file_non_tagged.tag = eyed3.load(download_last_tagged_audio()).tag;
    file_non_tagged.tag._setTrackNum((0, 0));
    file_non_tagged.tag.title = yt_entry.title;
    file_non_tagged.tag.save();

    cover_file_name = extract_cover(file_name);
    time_secs = duration_seconds(file_name);

    print("Uploading...");
    print(f'audio file = {nice_name}');
    print('caption = '+f'youtu.be/{yt_entry.videoId}');
    print(f'duration = {time_secs}');
    print(f'performer = {file_non_tagged.tag.artist}');
    print(f'title = {file_non_tagged.tag.title}');
    print(f'cover_file_name = {cover_file_name}');

    os.rename(file_name, nice_name);

    with app:
        app.send_audio(
            chat_id=chat_target,
            audio=nice_name,
            caption=f'youtu.be/{yt_entry.videoId}',
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

yt_entries = find_not_uploaded(read_last_messages());
for yt_entry in reversed(yt_entries):
    if check_is_video_good(yt_entry.videoId):
        download_tag_upload(yt_entry);
