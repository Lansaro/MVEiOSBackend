import random
import unittest
from parsers.search import Search
from parsers.downloader import Download
from random_word import RandomWords
import pytest


class ValueStorage:
    image = None
    video = None


class TestParsers(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.limit = random.randrange(10, 50)
        self.keywords = RandomWords().get_random_words(hasDictionaryDef="true", includePartOfSpeech="noun,verb",
                                                       minLength=5, maxLength=10, limit=random.randrange(1, 3))
        while not isinstance(self.keywords, list):
            self.keywords = RandomWords().get_random_words(hasDictionaryDef="true", includePartOfSpeech="noun,verb", minLength=5, maxLength=10, limit=random.randrange(1, 3))
        self.keywords = ' '.join(map(str, self.keywords))

    def test1_images_search(self):
        request_data = {
            'keywords': self.keywords,
            'limit': self.limit,
            'type': 'image'
        }
        result = Search(request_data).search()
        ValueStorage.image = result[0]
        self.assertGreaterEqual(len(result) + 9, self.limit)

    def test2_search_by_image(self):
        request_data = {
            'keywords': ValueStorage.image,
            'limit': self.limit,
            'type': 'similar_images'
        }
        result = Search(request_data).search()
        self.assertGreaterEqual(len(result) + 9, self.limit)

    def test3_video_search(self):
        request_data = {
            'keywords': self.keywords,
            'limit': self.limit,
            'type': 'video'
        }
        result = Search(request_data).search()
        ValueStorage.video = result.pop()['url']
        self.assertGreaterEqual(len(result) + 9, self.limit)

    def test4_video_download(self):
        types = [
            ['video'],
            ['video', 'audio'],
            ['audio']
        ]
        randomize_type = random.randrange(0, 2)
        time_start = random.randrange(0, 30)
        request_data = {
            'url': ValueStorage.video,
            'download_info': {
                'type': types[randomize_type],
                'timecodes': {
                    'time_start': time_start,
                    'time_end': time_start + random.randrange(5, 20)
                }
            }
        }
        result = Download(request_data).download()
        self.assertEqual(len(types[randomize_type]), len(result))

    def test5_image_download(self):
        request_data = {
            "url": ValueStorage.image,
            "download_info": {
                "type": [
                    'image'
                ]
            }
        }
        result = Download(request_data).download()
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()


