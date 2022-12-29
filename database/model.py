import settings
from bson.objectid import ObjectId
from pymongo import MongoClient


class MongoDB:
    def __init__(self):
        config = settings.get_config()
        self._client = MongoClient(config['db_host'], config['db_port'])
        self._db = self._client[config['db_name']]

    def find(self, collection_name, q={}):
        if '_id' in q:
            q['_id'] = ObjectId(q['_id'])

        return self._db[collection_name].find(q)

    def insert(self, collection_name, data):
        return self._db[collection_name].insert_one(data).inserted_id

    def update_many(self, collection_name, filter, update):
        self._db[collection_name].update_many(filter, update)

    def delete_many(self, collection_name, filter):
        self._db[collection_name].delete_many(filter)