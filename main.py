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

def download_tag_upload(urls, title, date_str, season, episode, cut_start_str):
    def nice_title():
        if '2016' in date_str:
            episode_str = 'XX';
            episode = 0;
        else
            episode_str = "{:03d}".format(episode);
        space = ' ' if (len(title) > 0) else '';
        return f'{title}{space}s0{season}e{episode_str}';
    title = nice_title();

    nice_name = f'{artist_name} — {title}.mp3';
    temp_name = 'out.mp3';
    if type(urls) is list and len(urls) == 2:
        u1 = urls[0];
        u2 = urls[1];
        f1 = download_single_vk(u1) if ('vk.com' in u1) else download_single(u1);
        f2 = download_single_vk(u2) if ('vk.com' in u2) else download_single(u2);
        run_ffmpeg(f1, cut_start_str, 'out1.mp3');
        run_ffmpeg(f2, '00:00', 'out2.mp3');
        os.system(f'{ffmpeg_exec} -f concat -i list_to_concat.txt -c copy {temp_name}');
    elif type(urls) is list and len(urls) == 3:
        u1 = urls[0];
        u2 = urls[1];
        u3 = urls[2];
        f1 = download_single_vk(u1) if ('vk.com' in u1) else download_single(u1);
        f2 = download_single_vk(u2) if ('vk.com' in u2) else download_single(u2);
        f3 = download_single_vk(u3) if ('vk.com' in u3) else download_single(u3);
        run_ffmpeg(f1, cut_start_str, 'out1.mp3');
        run_ffmpeg(f2, '00:00', 'out2.mp3');
        run_ffmpeg(f3, '00:00', 'out3.mp3');
        os.system(f'{ffmpeg_exec} -f concat -i list_to_concat_three.txt -c copy {temp_name}');
    elif type(urls) is list and len(urls) == 4:
        u1 = urls[0];
        u2 = urls[1];
        u3 = urls[2];
        u4 = urls[3];
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
        u1 = urls[0];
        file_name = download_single_vk(u1) if ('vk.com' in u1) else download_single(u1);
        run_ffmpeg(file_name, cut_start_str, temp_name);
    # trim_audio(file_name, cut_start_str);
    # temp_name = remove_silence(file_name, "temp" + file_name);

    timestamp = time.mktime(time.strptime(date_str, MY_FORMAT))
    os.utime(temp_name, (int(timestamp), int(timestamp)))
    # os.rename(temp_name, file_name);

    total_in_season = 0;
    if (season == 2):
        total_in_season = 71;
    if '2016' in date_str:
        total_in_season = 0;

    file_non_tagged = eyed3.load(temp_name);
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

    cover_file_name = extract_cover(temp_name);
    time_secs = duration_seconds(temp_name);

    print("Uploading...");
    print(f'audio file = {nice_name}');
    print(f'duration = {time_secs}');
    print(f'performer = {file_non_tagged.tag.artist}');
    print(f'title = {file_non_tagged.tag.title}');
    print(f'cover_file_name = {cover_file_name}');

    os.rename(temp_name, nice_name);

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


def first_season(urls, title, date_str, cut_start_str):
    download_tag_upload(
        list(map((lambda s : 'https://vk.com/video-' + s), urls)),
        title,
        date_str,
        1,
        0,
        cut_start_str);

def second_season(urls, title, date_str, episode, cut_start_str):
    download_tag_upload(
        list(map((lambda s : 'https://vk.com/video-' + s), urls)),
        title,
        date_str,
        2,
        episode,
        cut_start_str);

first_season(
    # ['72495291_456239592'], # Test.
    ['72495291_456239518'],
    'Сценарий к фильму',
    '13.12.2016',
    '02:15');

first_season(
    ['72495291_456239538', '72495291_456239539'],
    'Щячло снова на экране',
    '17.12.2016',
    '03:10');

first_season(
    ['72495291_456239565', '72495291_456239564'],
    'Паром дом дом',
    '18.12.2016',
    '02:30');

first_season(
    ['72495291_456239569'],
    'Каикакака (КиККК)',
    '19.12.2016',
    '03:30');

first_season(
    ['72495291_456239577'],
    'Харкотина на еботине',
    '22.12.2016',
    '04:10');

second_season(
    ['72495291_456239597', '72495291_456239596', '72495291_456239595'],
    'Я тут мимо крокодил...',
    '05.01.2017', 1,
    '02:00');

second_season(
    ['72495291_456239603', '72495291_456239601', '72495291_456239606'],
    'Курдючный жмых',
    '10.01.2017', 2,
    '02:40');

second_season(
    ['72495291_456239605', '72495291_456239604'],
    'Лилу Даллас Мульти Пасс',
    '11.01.2017', 3,
    '01:56');

second_season(
    ['72495291_456239610', '72495291_456239609', '72495291_456239608', '72495291_456239607'],
    '(Кузьма) Ускорение горизонтального падения',
    '12.01.2017', 4,
    '01:27');

second_season(
    ['72495291_456239613', '72495291_456239612', '72495291_456239611'],
    'Последний довод бегемотика',
    '13.01.2017', 5,
    '08:40');

second_season(
    ['72495291_456239618'],
    'Бертольдт Брехун',
    '15.01.2017', 6,
    '02:10');

second_season(
    ['72495291_456239620', '72495291_456239619'],
    '(Кузьма) Вовремя',
    '16.01.2017', 7,
    '01:35');

second_season(
    ['72495291_456239623', '72495291_456239622', '72495291_456239621'],
    'Полюсы Хуато',
    '16.01.2017', 8,
    '02:42');

second_season(
    ['72495291_456239631', '72495291_456239630', '72495291_456239628'],
    'Рубаха парень и Штаны девушка',
    '18.01.2017', 9,
    '03:16');

second_season(
    ['72495291_456239635', '72495291_456239633', '72495291_456239632'],
    'Мистер Крабапл',
    '20.01.2017', 10,
    '01:51');

second_season(
    ['72495291_456239639', '72495291_456239638', '72495291_456239637'],
    'Итоги киногода 2016',
    '21.01.2017', 11,
    '03:16');

second_season(
    ['72495291_456239641', '72495291_456239640'],
    'Итоги киногода 2016 - 2',
    '22.01.2017', 12,
    '02:48');

second_season(
    ['72495291_456239643', '72495291_456239642'],
    'Квадрат бифуркации',
    '23.01.2017', 13,
    '05:46');

second_season(
    ['72495291_456239645', '72495291_456239644'],
    'Сердоболька',
    '24.01.2017', 14,
    '01:53');

second_season(
    ['72495291_456239647', '72495291_456239646'],
    'Среда',
    '25.01.2017', 15,
    '00:31');

second_season(
    ['72495291_456239655', '72495291_456239653'],
    'Путешествия с мёртвым индейцем',
    '26.01.2017', 16,
    '02:54');

second_season(
    ['72495291_456239651', '72495291_456239650'],
    'Трижды двадцать и десять',
    '27.01.2017', 17,
    '01:46');

second_season(
    ['72495291_456239660', '72495291_456239659'],
    'Флюгегехаймен',
    '29.01.2017', 18,
    '04:25');

second_season(
    ['72495291_456239664', '72495291_456239663'],
    'Вакуум высокой плотности',
    '30.01.2017', 19,
    '10:07');

second_season(
    ['72495291_456239667'],
    'Сол Беллоу - На память обо мне',
    '31.01.2017', 0,
    '02:45');

second_season(
    ['72495291_456239669', '72495291_456239668'],
    'Штурмбанфюррер ГеоГёссер пожаловал в резиденцию',
    '01.02.2017', 20,
    '09:00');

second_season(
    ['72495291_456239671'],
    'Дятл Перевалова',
    '02.02.2017', 21,
    '02:56');

second_season(
    ['72495291_456239675'],
    'Кирибатти',
    '07.02.2017', 22,
    '08:52');

second_season(
    ['72495291_456239678', '72495291_456239677'],
    'И немедленно вы...вих',
    '08.02.2017', 23,
    '01:55');

second_season(
    ['72495291_456239683', '72495291_456239682'],
    'УВNДЕВШNЕ ЭТО SОЙДYТ CУМА',
    '09.02.2017', 24,
    '05:55');

second_season(
    ['72495291_456239686', '72495291_456239685'],
    'Сол Беллоу - Севший в калошу',
    '10.02.2017', 0,
    '01:58');

second_season(
    ['72495291_456239687'],
    'Ебловатый и Дебелый снова в седле',
    '11.02.2017', 25,
    '04:32');

second_season(
    ['72495291_456239689', '72495291_456239688'],
    'Коллаборационистское правительство',
    '13.02.2017', 26,
    '06:01');

second_season(
    ['72495291_456239691', '72495291_456239690'],
    'Такое же название',
    '14.02.2017', 27,
    '03:15');

second_season(
    ['72495291_456239696'],
    'Юбилейный стрим',
    '16.02.2017', 28,
    '04:44');

second_season(
    ['72495291_456239704', '72495291_456239703'],
    'ВЖОП и СРАК',
    '19.02.2017', 29,
    '03:10');

second_season(
    ['72495291_456239707'],
    'Трубокур',
    '20.02.2017', 30,
    '00:01');

second_season(
    ['72495291_456239715', '72495291_456239714'],
    'Барокко рокко ко', # episode 30
    '21.02.2017', 31,
    '03:14');

second_season(
    ['72495291_456239717', '72495291_456239716'],
    'sha lava LAVA LAAVAAAAA!!!!!',
    '22.02.2017', 32,
    '07:13');

second_season(
    ['72495291_456239734'],
    'Второе кедровое воскурение',
    '24.02.2017', 33,
    '00:01');

second_season(
    ['72495291_456239736', '72495291_456239735'],
    'Толстожопое лобби',
    '25.02.2017', 34,
    '02:45');

second_season(
    ['72495291_456239739', '72495291_456239735'],
    'Наивно это и смешно, но так легко',
    '26.02.2017', 35,
    '02:10');

second_season(
    ['72495291_456239742', '72495291_456239741'],
    'Акведук, Теремок и Две Прищепки',
    '27.02.2017', 36,
    '01:20');

second_season(
    ['72495291_456239743'],
    'Ла-Ла Леунный свет',
    '27.02.2017', 37,
    '02:46');

second_season(
    ['72495291_456239746'],
    'Лазерная коррекция жопы',
    '28.02.2017', 38,
    '07:16');

second_season(
    ['72495291_456239749'],
    'Реструктуризация точек схлопывания',
    '02.03.2017', 39,
    '07:02');

second_season(
    ['72495291_456239752'],
    'Последняя трансляция...',
    '03.03.2017', 40,
    '06:10');

second_season(
    ['72495291_456239756'],
    'Лобко лобко',
    '04.03.2017', 41,
    '05:58');

second_season(
    ['72495291_456239763'],
    'Что за стрим?',
    '05.03.2017', 42,
    '12:03');

second_season(
    ['72495291_456239767'],
    'Приглашаются Венеруны',
    '06.03.2017', 43,
    '17:55');

second_season(
    ['72495291_456239770'],
    'Ж-Корвалол и его друзья Пестициды',
    '07.03.2017', 44,
    '08:50');

second_season(
    ['72495291_456239771'],
    'Ромовая баба, пепсиколовый мужик',
    '08.03.2017', 45,
    '06:50');

second_season(
    ['72495291_456239775'],
    'Ещё один день в раю',
    '09.03.2017', 46,
    '03:44');

second_season(
    ['72495291_456239778'],
    'Атеисты седьмого дня',
    '10.03.2017', 47,
    '03:04');

second_season(
    ['72495291_456239785'],
    'Сильвупле, печёночник',
    '12.03.2017', 48,
    '09:27');

second_season(
    ['72495291_456239792'],
    'Эрик и Мария Ремарки представляют вашему вниманию Кульбиты',
    '15.03.2017', 49,
    '10:53');

second_season(
    ['72495291_456239798'],
    'Программа по защите свидетелей Иегова',
    '16.03.2017', 50,
    '07:27');

second_season(
    ['72495291_456239806'],
    '(Дарья Зарыковская) Париж, париж Ибонжур',
    '18.03.2017', 51,
    '01:37');

second_season(
    ['72495291_456239819', '72495291_456239818'],
    'Перекись населения',
    '24.03.2017', 52,
    '06:37');

second_season(
    ['72495291_456239824'],
    'Музы Кабатуева',
    '25.03.2017', 53,
    '05:00');

second_season(
    ['72495291_456239825'],
    'Педрильный клуб любителей пощекотать очко',
    '26.03.2017', 54,
    '04:50');

second_season(
    ['72495291_456239831'],
    'Кесарево Свечение Чистого Разума',
    '28.03.2017', 55,
    '06:30');

second_season(
    ['72495291_456239837'],
    'Иж Юпитер и Sega Saturn', # epi 56
    '29.03.2017', 56,
    '02:08');

second_season(
    ['72495291_456239840'],
    'Элитный стрим для солидных господ',
    '30.03.2017', 57,
    '01:21');

second_season(
    ['72495291_456239845'],
    'Донч ю ноу ам локо Локо ЛОКО ЛОКОМОТИВ!!!',
    '31.03.2017', 58,
    '00:01');

second_season(
    ['72495291_456239851'],
    '(Хованский) Стрим ли вовремя? Зачем и почему?',
    '02.04.2017', 59,
    '03:33');

second_season(
    ['72495291_456239852'],
    'Чехов: Я не цитировал БигРашнБосса... но это не точно',
    '03.04.2017', 60,
    '01:20');

second_season(
    ['72495291_456239855'],
    'Лимпомор',
    '04.04.2017', 61,
    '05:30');

second_season(
    ['72495291_456239858'],
    'Первый и Второй Том... и джери',
    '06.04.2017', 62,
    '07:24');

second_season(
    ['72495291_456239860', '72495291_456239859'],
    'Уаппарата',
    '07.04.2017', 63,
    '10:20');

second_season(
    ['72495291_456239866'],
    'Акция-Акция "Бесплатная Лактация"',
    '08.04.2017', 64,
    '08:15');

second_season(
    ['72495291_456239867'],
    'Лапидарный бидалага',
    '09.04.2017', 65,
    '04:28');

second_season(
    ['72495291_456239869'],
    'Конец сезона',
    '10.04.2017', 66,
    '03:30');

second_season(
    ['72495291_456239870'],
    '(Хованский) Лобздрище и Циркулярный читают мануал',
    '11.04.2017', 67,
    '03:40');

second_season(
    ['72495291_456239871'],
    'Ноль Шесть Восемь',
    '12.04.2017', 68,
    '05:25');

second_season(
    ['72495291_456239873'],
    '(Кузьма) Румынская тяга к знаниям',
    '13.04.2017', 69,
    '00:01');

second_season(
    ['72495291_456239874'],
    'Совершенно новый формат А4',
    '14.04.2017', 70,
    '00:01');

second_season(
    ['72495291_456239875'],
    'Никогда такого не было, и вот опять! (БАН на ЮТУБЕ)',
    '15.04.2017', 71,
    '00:01');

# yt_entries = find_not_uploaded(read_last_messages());
# for yt_entry in reversed(yt_entries):
#     if check_is_video_good(yt_entry.videoId):
#         download_tag_upload(yt_entry);
