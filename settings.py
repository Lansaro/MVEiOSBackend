import os
import json


path = os.path.dirname(__file__) + '/config.json'


def get_config():
    with open(path) as f:
        config = json.load(f).get('config')
    return config


def get_download_config():
    with open(path) as f:
        config = json.load(f).get('download_config')
    return config


def get_search_config():
    with open(path) as f:
        config = json.load(f).get('search_config')
    return config


def get_mail_config():
    with open(path) as f:
        config = json.load(f).get('mail_config')
    return config