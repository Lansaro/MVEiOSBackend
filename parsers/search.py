import logging
from google_images_download import google_images_download
from youtube_dlc import YoutubeDL
from pytube import Search as PytubeSearch
from googleapiclient.discovery import build
import settings
import time


class Search:

    def __init__(self, request_data):
        self.keywords = request_data['keywords']
        self.config = settings.get_search_config()
        self.type = request_data['type']
        self.limit = request_data.get('limit') or 10
        self.countrycode = request_data.get('countrycode') or 'US'
        self.page_token = request_data.get('page_token') or 1
        self.response = []
        self.time = time.time()

    def search(self):
        try:
            methods = {
                'image': self.search_images,
                'video': self.search_yt,
                'similar_images': self.search_images
            }
            methods[self.type]()
            return self.response
        except Exception as e:
            raise ValueError(str(e))
            logging.critical('critical search error' + str(e))

    def search_images(self):
        response = google_images_download.googleimagesdownload()
        search_settings = {
            'limit': self.limit,
            'safe_search': True,
            'no_download': True,
            'silent_mode': True,
        }
        if self.type == 'image':
            additional_search_settings = {
                'keywords': self.keywords
            }
        elif self.type == 'similar_images':
            additional_search_settings = {
                'similar_images': self.keywords
            }
        search_settings = {**search_settings, **additional_search_settings}
        response = response.download(search_settings)
        for response_list in response[0].values():  
            self.response = self.response + response_list

    def search_yt(self):
        methods = {
            self.config['PYTube_driver_priority']: self.yt_pytube,
            self.config['YTdl_driver_priority']: self.yt_dl,
            self.config['official_driver_priority']: self.yt_official,
        }
        for number in range(len(methods)):
            try:
                methods[number]()
            except Exception as e:
                raise ValueError(str(e))
                break
                self.response = []
                logging.warning('Search driver ' + str(number) + 'failed to parse ' + self.keywords)
            if len(self.response) != 0:
                break

    def yt_official(self):
        youtube = build(
            'youtube',
            'v3',
            developerKey=self.config['youtube_api_key'])
        search_response = youtube.search().list(
            q='test',
            part='id,snippet',
            maxResults=self.limit,
            type='video',
            pageToken=''
        ).execute()
        for result in search_response['items']:
            self.response.append({
                'url': 'https://www.youtube.com/watch?v=' + result['id']['videoId'],
                'title': result['snippet']['title']
            })

    def yt_pytube(self):
        results = PytubeSearch(self.keywords).results
        if len(results) == 0:
            raise ConnectionRefusedError('pytube returned 0 results')
        for result in results:
            self.response.append({
                'url': result.watch_url,
                'title': result.title,
                'channel': result.author,
                'thumbnail': result.thumbnail_url,
                'length': result.length
            })

    def yt_dl(self):
        ydl_opts = {
            'simulate': True,
            'noplaylist': True,
            'min_views': 1000,
            'playlistend': self.limit,
            'skip_download': True,
            'extract_flat': True,
            'quiet': True,
        }
        ydl_url = 'https://www.youtube.com/results?search_query=' + 'allintitle:' + self.keywords + '&page=' + str(
            self.page_token)
        search_response = YoutubeDL(ydl_opts).extract_info(ydl_url, download=False, ie_key='YoutubeSearchURL')
        if len(search_response['entries']) == 0:
            raise ConnectionRefusedError('yt_dl returned 0 results')
        ftr = [1, 60, 3600]
        for result in search_response['entries']:
            if result.get('length'):
                self.response.append({
                    'url': 'https://www.youtube.com/watch?v=' + result['url'],
                    'title': result['title'],
                    'thumbnail': result.get('thumbnail'),
                    'channel': result.get('channel'),
                    'length': sum([a * b for a, b in zip(ftr, map(int, reversed(result.get('length').split(':'))))]),
                })
