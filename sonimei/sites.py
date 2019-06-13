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

from logzero import logger as zlog
from izen import helper
from izen.prettify import ColorPrint, Prettify

from sonimei.metas import SongMetas
from sonimei.icfg import cfg
from sonimei.zutil import error_hint, headless_driver
from sonimei import wget

PRETTY = Prettify(cfg)
CP = ColorPrint()

from izen.crawler import AsyncCrawler
from sonimei.site_header import NeteaseHeaders, QQHeaders, KugouHeaders


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
        if not has_pic and pic_pth:
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
            return save_to
        if self._override and helper.is_file_ok(save_to):
            zlog.info('force remove exist file: ({})'.format(helper.C.format(save_to)))
            os.remove(save_to)
        zlog.debug('try get {}'.format(save_to))
        try:
            wget.download(src, out=save_to)
            # wget output end without new line
            print()
            zlog.info('downloaded {}'.format(helper.G.format(save_to.split('/')[-1])))
            return save_to
        except Exception as e:
            zlog.error('Download {} Failed: {}'.format(save_to.split('/')[-1], e))
            return ''

    def save_song(self, song):
        extension = self._parse_song(song)
        title = song['author'] + '-' + song['title']
        song_pth = os.path.join(self._media_dst_dir, '{}.{}'.format(title, extension))
        pic_pth = os.path.join(self._media_cache_dir, title + '.jpg')
        try:
            if not song.get('url'):
                zlog.warning('song has no url: {}'.format(song))
                return
            song_pth = self._download(song['url'], song_pth)
            if song_pth == '':
                error_hint('failed download song: {}'.format(song_pth))
                os._exit(-1)
            pic_pth = self._download(song['pic'], pic_pth)
            return song, song_pth, pic_pth
        except Exception:
            zlog.error('failed {}'.format(song))
            error_hint('maybe cache expired, use -nc to skip the cache')
            traceback.print_exc()
            os._exit(-1)


class SiteAlbum(object):
    def __init__(self, home, log_level=10, use_cache=True):
        self.ac = AsyncCrawler(
            site_init_url=home,
            base_dir=os.path.expanduser('~/.crawler'),
            timeout=10,
            log_level=log_level,
        )
        self._use_cache = use_cache

    def fetch(self, url):
        return self.ac.bs4get(url, use_cache=self._use_cache)

    def get_album(self, dat):
        pass


class MockAlbum(SiteAlbum):
    def __init__(self, url='', log_level=10, use_cache=True):
        super().__init__('mock_site', log_level, use_cache)

    def get_album(self, dat):
        zlog.info('got {}'.format(dat))
        return ''


class QQAlbum(SiteAlbum):
    def __init__(self, url='', log_level=10, use_cache=True):
        self.home = 'http://y.qq.com/'
        super().__init__(self.home, log_level, use_cache)
        self.ac.headers['get'] = QQHeaders.get

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
        doc = self.fetch(dat['link'])
        _pg = re.compile('g_SongData = *')
        rs = doc.find(string=_pg)
        rs = rs.split(' = ')
        detail = json.loads(rs[1].strip()[:-1])
        return detail['albumname']


class NeteaseAlbum(SiteAlbum):
    def __init__(self, url='', log_level=10, use_cache=True):
        self.home = 'https://music.163.com/'
        super().__init__(self.home, log_level, use_cache)
        self.ac.headers['get'] = NeteaseHeaders.get

    def get_album(self, dat):
        link = urljoin(self.home, dat['link'].split('#')[1])
        doc = self.fetch(link)
        album_doc = doc.find_all(class_='des s-fc4')[-1]
        album = album_doc.a.text
        return album


class KugouAlbum(SiteAlbum):
    def __init__(self, log_level=10, use_cache=True):
        super().__init__('', log_level, use_cache)
        self.driver = headless_driver()

    def get_album(self, dat):
        """"""
        try:
            css_selector = '.albumName>a'
            self.driver.get(dat['link'])
            elem = self.driver.find_element_by_css_selector(css_selector)
            album = elem.get_attribute('title')
            zlog.debug('album is: {}'.format(album))
            return album
        except Exception as e:
            zlog.error('({}):{}'.format(dat.get('link'), e))
