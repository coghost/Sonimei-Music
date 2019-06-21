# -*- coding: utf-8 -*-
__date__ = '05/19 12:37'
__description__ = '''
'''

import os
import sys
import json

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout
from logzero import logger as zlog
from izen.crawler import AsyncCrawler
from izen import helper
import yaml

from sonimei.icfg import cfg
from sonimei.site_header import SonimeiHeaders
from sonimei.sites import Downloader, MusicStore
from sonimei.sites import MockAlbum, QQAlbum, NeteaseAlbum, KugouAlbum

album_factory = {
    'qq': QQAlbum,
    '163': NeteaseAlbum,
    'kugou': KugouAlbum,
    'album': MockAlbum,
}


class Sonimei(object):
    def __init__(self, site='qq', use_cache=True, log_level=10, timeout=10, override=False):
        self.home = 'http://music.sonimei.cn/'
        self.ac = AsyncCrawler(
            site_init_url=self.home,
            base_dir=os.path.expanduser('~/.crawler'),
            timeout=timeout,
            log_level=log_level,
        )
        self.use_cache = use_cache
        self.music_save_dir = os.path.expanduser(cfg.get('snm.save_dir', '~/Music/sonimei'))
        self.site = site

        self._album_handler = album_factory.get(site, MockAlbum)(log_level=log_level, use_cache=use_cache)
        self._downloader = Downloader(self.music_save_dir, self.ac.cache['site_media'], override)
        self.store = MusicStore(self.music_save_dir, log_level)
        self._song_name = ''
        self.failure_store = cfg.get('snm.failure_store')

        self._spawn()

    def _spawn(self):
        self.ac.headers['post'] = SonimeiHeaders.post
        self.ac.headers['Host'] = self.ac.domain
        helper.mkdir_p(self.music_save_dir, is_dir=True)
        self.store.scan_all_songs()

    def search_it(self, name, page=1):
        form = {
            'filter': 'name',
            'type': self.site,
            'page': page,
            'input': name,
        }
        self._song_name = name
        doc = {}
        try:
            doc = self.ac.bs4post(self.home, data=form, show_log=True, use_cache=self.use_cache)
        except (ConnectTimeout, ConnectionError, ReadTimeout) as e:
            zlog.error('ReadTimeout: {}'.format(e))
        songs = doc.get('data')
        if not songs:
            zlog.warning('[{}] matched nothing.'.format(name))
            self.log_and_quit(self._song_name, 0)

        return songs

    def save_song(self, song):
        song, song_pth, pic_pth = self._downloader.save_song(song)
        if not song:
            self.log_and_quit(self._song_name, 0)
        album_info = self._album_handler.get_album(song)
        self.store.update_song(song, song_pth, pic_pth, album_info)
        self.dump_failure_songs(self._song_name, action='D')

    def log_and_quit(self, song, status=0):
        self.dump_failure_songs(song)
        os._exit(status)

    def load_failure_songs(self):
        try:
            file_pth = os.path.expanduser(self.failure_store)
            with open(file_pth, 'rb') as f:
                dat = yaml.load(f, Loader=yaml.FullLoader)

            dat = [x for x in dat if x]
            return dat
        except Exception as e:
            return

    def dump_failure_songs(self, song, action='C'):
        dat = self.load_failure_songs() or []
        dat = [x for x in dat if x]
        if action == 'C':
            dat.append(song)
        elif action == 'D':
            if song in dat:
                dat.pop(dat.index(song))
        else:
            zlog.error('unsupported action: ({})'.format(action))
            return

        dat = list(set(dat))
        dat = yaml.dump(dat)
        file_pth = os.path.expanduser(self.failure_store)
        helper.write_file(dat, file_pth)


class NeteaseDL(Sonimei):
    def __init__(self, site='163', use_cache=True, log_level=20, timeout=10, override=False):
        super().__init__(site, use_cache, log_level, timeout, override)
        self.log_dir = os.path.expanduser(cfg.get('163.log_dir'))

    def search_it(self, name='', page=1):
        try:
            _cmd = "tail -n {} {} | grep songName".format(cfg.get('163.log_count'), self.log_dir)
            songs = helper.os_cmd(_cmd)
            line = [x for x in songs.split('\n') if x][-1]
            line = '{' + line.split('{')[1]
            song = json.loads(line)
            # update according to the caller
            song['author'] = song['artistName']
            song['title'] = song['songName']
            self._song_name = '{}-{}'.format(song['author'], song['title'])
            song['pic'] = song['url'] + '?imageView&enlarge=1&quality=90&thumbnail=440y440'
            # m8.music may not available all time, so use m7
            song['url'] = song['musicurl'].replace('m8.music.126.net', 'm7.music.126.net')
            return song
        except Exception as e:
            zlog.error('{}'.format(e))
            return ''

    def save_song(self, song):
        album_info = song['albumName']
        song, song_pth, pic_pth = self._downloader.save_song(song)
        if not song:
            self.log_and_quit(self._song_name, 0)
        self.store.update_song(song, song_pth, pic_pth, album_info)
        self.dump_failure_songs(self._song_name, action='D')
