import logging
import os
import uuid
import json

from pytube import YouTube

import settings
import multiprocessing
from aiohttp import web
from cerberus import Validator
from parsers.downloader import Download
from parsers.search import Search
from database.file_cleaning_service import FileCleaningService
from youtube_dlc import YoutubeDL


async def server_status(request):
    request_data = await request.text()
    encode_data = json.loads(request_data)
    v = Validator(purge_unknown=True)
    v.schema = {'generate_uuid': {'required': True, 'type': 'integer'}}

    if v.validate(encode_data):
        config = settings.get_config()
        response_data = {'status': config['server_enabled'], 'errors': {}}

        if encode_data['generate_uuid']:
            response_data['uuid'] = uuid.uuid4().hex  # 32 symbols

        return web.json_response(response_data)
    else:
        return web.json_response({'errors': v.errors})


async def search(request):
    request_data = await request.text()
    encode_data = json.loads(request_data)
    v = Validator(purge_unknown=True)
    v.schema = {
        'page_token': {'type': 'integer'},
        'limit': {'type': 'integer'},
        'keywords': {'required': True, 'type': 'string'},
        'type': {'required': True, 'type': 'string', 'allowed': ['video', 'image', 'similar_images']},
        'countrycode': {'type': 'string', 'max': 2}
    }

    if v.validate(encode_data):
        return web.json_response(Search(encode_data).search())
    else:
        return web.json_response({'errors': v.errors})


async def download_file(request):
    try:
        request_data = await request.text()
        request_data = json.loads(request_data)
        resp = Download(request_data).download()
        return web.json_response(resp)
    except Exception as error:
        return web.json_response({'errors': str(error)})


async def delete(request):
    request_data = await request.text()
    request_data = json.loads(request_data)
    try:
        return web.json_response(FileCleaningService().delete_files(request_data['files'], True))
    except Exception as e:
        logging.critical('file delete failed'.join(request_data['files']))


async def share(request):
    request_data = await request.multipart()
    file_address = uuid.uuid4().hex
    # Validator here

    field = await request_data.next()
    assert field.name == 'project_name'
    name = await field.text()
    file_address = file_address + name + config['project_format']

    field = await request_data.next()
    assert field.name == 'project'
    file_address = os.path.join(config['project_file_path'], file_address)
    with open(file_address, 'wb') as f:
        while True:
            chunk = await field.read_chunk()
            if not chunk:
                break
            f.write(chunk)
    return web.json_response({'file_address': file_address})


async def get_video(request):
    request_data = await request.text()
    request_data = json.loads(request_data)

    streams = YoutubeDL().extract_info(request_data.get('url'), download=False)['formats']
    result = dict()
    result['full']=list(filter(filterStreams, streams))
    result['audio']=list(filter(filterAudioStreams, streams))
    result['video']=list(filter(filterVideoStreams, streams))

    try:
        return web.json_response({
            'full': [x.get('url') for x in result['full']],
            'audio': [x.get('url') for x in result['audio']],
            'video': [x.get('url') for x in result['video']]
        })
    except Exception as e:
        return web.json_response({'errors': 'invalid YT URL'})


def filterStreams(stream):
    if stream['ext'] == 'mp4' \
            and stream['height'] <= 1080 \
            and stream['fps'] <= 30 \
            and stream['height'] >= 720 \
            and stream['vcodec'].find('av1') == -1 \
            and stream['acodec'] != 'none' \
            and stream['vcodec'].find('av01') == -1:
        return True
    return False

def filterVideoStreams(stream):
    if stream['ext'] == 'mp4' \
            and stream['height'] <= 1080 \
            and stream['fps'] <= 30 \
            and stream['height'] >= 720 \
            and stream['vcodec'].find('av1') == -1 \
            and stream['acodec'] == 'none' \
            and stream['vcodec'].find('av01') == -1:
        return True
    return False

def filterAudioStreams(stream):
    if stream['vcodec'] == 'none' \
            and stream['acodec'] != 'none':
        return True
    return False

config = settings.get_config()
BASE_DIR = os.path.dirname(os.path.realpath(__file__))

app = web.Application()

try:
    logging.basicConfig(filename='logs/log.log')
    app.add_routes([web.post('/search', search)])
    app.add_routes([web.post('/server_status', server_status)])
    app.add_routes([web.post('/download_file', download_file)])
    app.add_routes([web.post('/delete', delete)])
    app.add_routes([web.post('/share', share)])
    app.add_routes([web.post('/get_stream', get_video)])
    app.add_routes([web.static(config['public_file_path'], BASE_DIR + config['public_file_path'])])
    streams = YoutubeDL().extract_info('https://www.youtube.com/watch?v=ypty0GkXV5w', download=False)['formats']
    result = dict()
    result['full']=list(filter(filterStreams, streams))
    result['audio']=list(filter(filterAudioStreams, streams))
    result['video']=list(filter(filterVideoStreams, streams))
    web.run_app(app, host=config['server_url'], port=config['app_port'])

    multiprocessing.set_start_method('spawn')
except Exception as e:
    logging.warning(e)
