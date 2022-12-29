import os
import re
import datetime
import settings
from database.model import MongoDB


class FileCleaningService:
    def __init__(self):
        self.mongo = MongoDB()
        self.base_directory = os.path.dirname(os.path.realpath('app.py'))
        self.config = settings.get_config()
        self.expired = datetime.datetime.utcnow() + datetime.timedelta(hours=-self.config['file_life_in_hours'])

    def cron_delete_expired(self) -> None:
        expired_files = self.mongo.find(
            'media',
            {
                'created_at': {'$lt': self.expired},
            }
        )
        for expired_file in expired_files:
            self.delete_files([expired_file['url']], None)
        self.mongo.delete_many(
            'media',
            {
                'created_at': {'$lt': self.expired},
            }
        )

    def delete_files(self, urls, update_db):
        for url in urls:
            file_path = self.base_directory + '/' + url
            if os.path.isfile(file_path):
                os.remove(file_path)
        if update_db:
            expired_files = self.mongo.delete_many(
                'media',
                {
                    'url': {'$in': urls},
                }
            )
        return True

