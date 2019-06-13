# -*- coding: utf-8 -*-
__date__ = '05/19 12:37'
__description__ = '''
'''

import os
import sys
import requests

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

from logzero import logger as zlog
from izen.crawler import AsyncCrawler
from izen import helper

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
        doc = {}
        try:
            doc = self.ac.bs4post(self.home, data=form, show_log=True, use_cache=self.use_cache)
        except requests.exceptions.ReadTimeout as e:
            zlog.error('ReadTimeout: {}'.format(e))
        songs = doc.get('data')
        if not songs:
            zlog.warning('[{}] matched nothing.'.format(name))
            os._exit(0)

        return songs

    def save_song(self, song):
        song, song_pth, pic_pth = self._downloader.save_song(song)
        album_info = self._album_handler.get_album(song)
        self.store.update_song(song, song_pth, pic_pth, album_info)
