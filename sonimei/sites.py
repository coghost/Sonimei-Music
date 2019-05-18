# -*- coding: utf-8 -*-
__date__ = '05/18 12:52'
__description__ = '''
'''
import os
import sys
import json
from urllib.parse import urljoin
import re
import traceback

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

import requests
from logzero import logger as zlog
from izen import helper
from izen.prettify import ColorPrint, Prettify

from sonimei.metas import SongMetas
from sonimei.icfg import cfg
from sonimei.zutil import error_hint
from sonimei.site_header import SonimeiHeaders
from sonimei import wget

SITES = {
    'qq': 'qq',
}

PRETTY = Prettify(cfg)
CP = ColorPrint()

from izen.crawler import AsyncCrawler
from sonimei.site_header import NeteaseHeaders, QQHeaders


class MusicStore(object):
    def __init__(self, song_dir, log_level=10):
        self._music_dir = song_dir
        self._all_songs = []
        self._song_metas = SongMetas(log_level <= 10)

    @property
    def all_songs(self):
        return self._all_songs

    def scan_all_songs(self):
        self._all_songs = helper.walk_dir_with_filter(self._music_dir, prefix=['.DS_Store'])
        self._all_songs = [x.split('/')[-1] for x in self._all_songs]

    def is_file_exist(self, song_name):
        """TODO: use sqlite to store song names"""
        song_name = song_name.split('-')[-1].split('.')[0]
        # print(song_name, local_musics)
        similar = []
        for song in self._all_songs:
            song_ = '.'.join(song.split('.')[:-1])
            candidates = [song_, *song_.split('-')]
            if song_name in '#'.join(candidates):
                similar.append(song)

        return similar

    def is_file_id3_ok(self, song_name):
        song_pth = os.path.join(self._music_dir, song_name)
        if song_pth[-4:] != '.mp3':
            song_pth += '.mp3'

        if helper.is_file_ok(song_pth):
            has_pic, song_id3 = self._song_metas.get_song_meta(song_pth)
            return has_pic, song_pth
        return False, None

    def update_song(self, song, song_pth, pic_pth, album_info):
        tags = ['TIT2', 'TPE1', 'TALB']
        site_dat = {'TPE1': song['author'].strip(), 'TIT2': song['title'].strip()}
        has_pic, song_id3 = self._song_metas.get_song_meta(song_pth)

        id3_same = True
        # skip TALB
        for tag in tags[:-1]:
            if site_dat[tag] != song_id3.get(tag):
                zlog.debug('Not Matched: site({}) != id3({})'.format(site_dat[tag], song_id3.get(tag)))
                id3_same = False
                # id3_same = id3_same and site_dat[tag] == song_id3[tag]
        if not has_pic:
            site_dat['APIC'] = pic_pth
            id3_same = False

        if not song_id3.get('TALB') or not id3_same:
            site_dat['TALB'] = album_info

        if not id3_same:
            CP.G('update {}'.format(site_dat))
            self._song_metas.update_song_meta(song_pth, site_dat)


class Downloader(object):
    def __init__(self, dst_dir, cache_dir, override=False):
        self._override = override
        self._media_dst_dir = dst_dir
        self._media_cache_dir = cache_dir

    @staticmethod
    def _parse_song(dat):
        if isinstance(dat, str):
            dat = json.loads(dat)
        url = dat.get('url')
        zlog.info('song url: [{}]'.format(url))
        return 'mp3'

    def _download(self, src, save_to):
        if not self._override and helper.is_file_ok(save_to):
            zlog.debug('{} is downloaded.'.format(save_to))
        else:
            zlog.debug('try get {}'.format(save_to))
            wget.download(src, out=save_to)
            # wget output end without new line
            print()
            zlog.info('downloaded {}'.format(helper.G.format(save_to)))

    def save_song(self, song):
        extension = self._parse_song(song)
        title = song['author'] + '-' + song['title']
        song_pth = os.path.join(self._media_dst_dir, '{}.{}'.format(title, extension))
        pic_pth = os.path.join(self._media_cache_dir, title + '.jpg')
        try:
            if not song.get('url'):
                zlog.warning('song has no url: {}'.format(song))
                return
            self._download(song['url'], song_pth)
            self._download(song['pic'], pic_pth)
            return song, song_pth, pic_pth
        except Exception:
            zlog.error('failed {}'.format(song))
            error_hint('maybe cache expired, use -nc to skip the cache')

            traceback.print_exc()
            os._exit(-1)


class QQAlbum(object):
    def __init__(self, log_level=10, use_cache=True):
        self.home = 'http://y.qq.com/'
        self.ac = AsyncCrawler(
            site_init_url=self.home,
            base_dir=os.path.expanduser('~/.crawler'),
            timeout=10,
            log_level=log_level,
        )
        self.ac.headers['get'] = QQHeaders.get
        self._use_cache = use_cache

    def get_album(self, dat):
        """
        Args:
            dat (dict):
            {
                'type': 'qq',
                'link': 'http://y.qq.com/n/yqq/song/0019n6dS204TzZ.html',
                'songid': '0019n6dS204TzZ',
                'title': '有一种悲伤',
                'author': 'A-Lin',
                'lrc': '...',
                'url': 'http://dl.stream.qqmusic.qq.com/M5000019n6dS204TzZ.mp3',
                'pic': 'http://y.gtimg.cn/music/photo_new/T002R300x300M0000030IgT80txlIK.jpg'
            }
        Returns:
            album (str)
        """
        doc = self.ac.bs4get(dat['link'], use_cache=self._use_cache)
        _pg = re.compile('g_SongData = *')
        rs = doc.find(string=_pg)
        rs = rs.split(' = ')
        detail = json.loads(rs[1].strip()[:-1])
        return detail['albumname']


class NeteaseAlbum(object):
    def __init__(self, log_level=10, use_cache=True):
        self.home = 'https://music.163.com/'
        self.ac = AsyncCrawler(
            site_init_url=self.home,
            base_dir=os.path.expanduser('~/.crawler'),
            timeout=10,
            log_level=log_level,
        )
        self.ac.headers['get'] = NeteaseHeaders.get
        self._use_cache = use_cache

    def _do_get(self, url):
        doc = self.ac.bs4get(url)
        album_doc = doc.find_all(class_='des s-fc4')[-1]
        album = album_doc.a.text
        return album

    def get_album(self, dat):
        link = urljoin(self.home, dat['link'].split('#')[1])
        doc = self.ac.bs4get(link, use_cache=self._use_cache)
        album_doc = doc.find_all(class_='des s-fc4')[-1]
        album = album_doc.a.text
        return album


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
        self.site = site
        self.save_dir = os.path.expanduser(cfg.get('snm.save_dir', '~/Music/sonimei'))

        if site == 'qq':
            self._album_handler = QQAlbum(log_level, use_cache)
        else:
            self._album_handler = NeteaseAlbum(log_level, use_cache)
        # self._song_metas = SongMetas(log_level <= 10)
        self._downloader = Downloader(self.save_dir, self.ac.cache['site_media'], override)
        self.store = MusicStore(self.save_dir, log_level)
        self._spawn()

    def _spawn(self):
        self.ac.headers['post'] = SonimeiHeaders.post
        self.ac.headers['Host'] = self.ac.domain
        helper.mkdir_p(self.save_dir, is_dir=True)
        self.store.scan_all_songs()

    @staticmethod
    def get_best_match(songs, name, author):
        best_match = []
        songs_got = []
        for i, song in enumerate(songs):
            _title = '{}-{}'.format(song['author'], song['title'])
            url = song['url']
            songs_got.append('{} {}'.format(_title, url))

            b = False or author in song['author'] or song['author'] in author
            b = b and (name in song['title'] or song['title'] in name)
            if b:
                best_match.append('{} {}'.format(_title, url))

        keys = ['demo', 'live']
        for k in keys:
            if len(best_match) == 1:
                return best_match[0]
            elif not best_match:
                return songs_got
            best_match = [x for x in best_match if k not in x]

        return best_match

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
