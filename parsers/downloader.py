import datetime
import os
import shutil
import uuid
from ffmpy import *
import urllib3
from pytube import YouTube
from youtube_dlc import YoutubeDL
from database.model import MongoDB
import settings
from cerberus import Validator
from urllib.parse import urlparse
import logging
import multiprocessing


class Download:

    def __init__(self, request_data):
        self.manager = multiprocessing.Manager()
        self.duration = 0
        self._mongo = MongoDB()
        self.url = request_data.get('url')
        self.split_seconds = request_data.get('split_seconds')
        self.response = []
        self.download_info = request_data.get('download_info')
        self.download_config = settings.get_download_config()
        self.BASE_DIR = os.path.dirname(os.path.abspath('app.py'))
        self.driver_list = {
            self.download_config['PYTube_driver_priority']: self.py_tube,
            self.download_config['YTdl_driver_priority']: self.yt_dl,
        }
        self.processes = []


    def download(self):
        try:
            if 'image' in self.download_info['type']:
                result = self.download_image()
                self.response.append({
                    'url': result,
                    'type': 'image'
                })
            else:
                self.duration = self.download_info['timecodes']['time_end'] - self.download_info['timecodes'][
                    'time_start']
                for number in range(len(self.driver_list)):
                    try:
                        self.driver_list[number]()
                        for process in self.processes:
                            process.join()
                        self.response = list(self.response)
                    except Exception as e:
                        raise ConnectionError(str(e))
                        logging.warning('Download driver ' + str(number) + 'failed to parse ' + self.url)
                    if len(self.response) >= len(self.download_info['type']):
                        break
            for file in self.response:
                self._mongo.insert('media', {
                    'url': file['url'],
                    'created_at': datetime.datetime.utcnow(),
                    'type': file['type']
                })
            return self.response
        except Exception as e:
            logging.critical(str(e))
            return {'exception': str(e)}

    def py_tube(self):
        yt = YouTube(self.url)
        if 'video' in self.download_info['type']:
            yt_rules_video = {
                'file_extension': 'mp4',
                'custom_filter_functions': [
                    lambda s: (int(s.resolution.replace('p', '')) <= 720 and s.fps <= 30),
                    lambda s: ('av01' not in s.video_codec and 'av1' not in s.video_codec)
                ],
                'only_video': True
            }
            stream = yt.streams.filter(**yt_rules_video).order_by('resolution').last()
            self.ffmpeg_process(stream.url, 'video')
        if 'audio' in self.download_info['type']:
            yt_rules_audio = {
                'only_audio': True,
                'custom_filter_functions': [
                    lambda s: (int(s.abr.replace('kbps', '')) <= 128),
                ]
            }
            audio = yt.streams.filter(**yt_rules_audio).order_by('abr').last()
            self.ffmpeg_process(audio.url, 'audio')

    def yt_dl(self):
        if 'video' in self.download_info['type']:
            original_url = YoutubeDL({'youtube_include_dash_manifest': False,
                                      'format': 'bestvideo[height<=1080][fps<=30][ext=mp4]/bestvideo[height<=1080]['
                                                'fps<=30]'}).extract_info(
                self.url, download=False)['url']
            self.ffmpeg_process(original_url, 'video')
        if 'audio' in self.download_info['type']:
            original_url = YoutubeDL({'youtube_include_dash_manifest': False,
                                      'format': 'bestaudio[abr<=128]'}).extract_info(self.url, download=False)['url']
            self.ffmpeg_process(original_url, 'audio')

    def ffmpeg_process(self, original_url, type):
        self.response = self.manager.list()
        start = self.download_info['timecodes']['time_start']
        while start <= self.download_info['timecodes']['time_start'] + self.duration:
            config = {
                'BASE_DIR': self.BASE_DIR,
                'split_seconds': self.split_seconds or self.download_config.get('split_seconds'),
                'download_file_path': self.download_config['download_file_path']
            }
            process = multiprocessing.Process(target=Download.download_stream,
                                              args=(original_url, start, type, config, self.response))
            process.start()
            self.processes.append(process)
            start = start + self.download_config.get('split_seconds')

    def download_image(self):
        http_client = urllib3.PoolManager()
        new_name = uuid.uuid4().hex + '.' + self.get_extension(self.url)
        path = self.download_config['download_file_path'] + '/images' + '/' + new_name
        with http_client.request('GET', self.url, preload_content=False) as r, open(self.BASE_DIR + '/' + path,
                                                                                    'wb') as out_file:
            shutil.copyfileobj(r, out_file)
        return path

    @staticmethod
    def download_stream(url, start, filetype, config, response):
        ffmpeg_rules = {
            'audio': 'ffmpeg -ss {0}.000 -t {1}.000 -i "{2}" -b:a 128k -vn "{3}" -loglevel quiet',
            'video': 'ffmpeg -ss {0}.000 -t {1}.000 -i "{2}" -vcodec copy "{3}" -loglevel quiet'

        }

        if filetype == 'video':
            new_name = uuid.uuid4().hex + '.mp4'
        elif filetype == 'audio':
            new_name = uuid.uuid4().hex + '.mp3'

        ffmpeg_processs = ffmpeg_rules[filetype] \
            .format(str(start), str(config.get('split_seconds')), str(url),
                    config.get('BASE_DIR') + '/' + config.get(
                        'download_file_path') + '/' + filetype + '/' + new_name)
        subprocess.check_call(ffmpeg_processs, shell=True)
        response.append({
            'url': (config.get('download_file_path') + '\\' + filetype + '\\' + new_name).replace("\\", "/"),
            'type': filetype,
            'start': start,
        })

    @staticmethod
    def get_extension(string):
        tmp_list = string.split('.')
        for extension in ('png', 'jpg', 'gif', 'svg'):
            if extension in tmp_list:
                return tmp_list[-1]

        return 'jpeg'

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        url = urlparse(value)
        if not url.hostname or not url.scheme or not url.path:
            raise ValueError("URL invalid")
        self._url = value

    @property
    def download_info(self):
        return self._download_info

    @download_info.setter
    def download_info(self, value):
        if value.get('type'):
            v = Validator(purge_unknown=True)
            v.schema = {
                'type': {'required': True, 'type': 'list', 'schema': {'allowed': ['video', 'audio', 'image']}}
            }
            if 'image' not in value['type']:
                v.schema['timecodes'] = {'required': True, 'type': 'dict', 'schema': {
                    'time_start': {'type': 'integer', 'max': value.get('timecodes').get('time_end') or 0,
                                   'required': True},
                    'time_end': {'type': 'integer', 'required': True}
                }}
            if v.validate(value):
                self._download_info = value
            else:
                raise ValueError(v.errors)
        else:
            raise ValueError("Type is required")
