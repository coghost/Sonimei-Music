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
from sonimei.site_header import NeteaseHeaders


class Sonimei(object):
    def __init__(self, site='qq', use_cache=True, log_level=10, timeout=10, override=False):
        self.home = 'http://music.sonimei.cn/'
        self.ac = AsyncCrawler(
            site_init_url=self.home,
            base_dir=os.path.expanduser('~/.crawler'),
            timeout=timeout,
            log_level=log_level,
        )
        self.ac.headers['post'] = SonimeiHeaders.post

        self.use_cache = use_cache
        if site == 'netease':
            self.site_netease = Netease(log_level)
        self.site = site
        self.save_dir = os.path.expanduser(cfg.get('snm.save_dir', '~/Music/sonimei'))
        self.all_songs = []
        self._song_metas = SongMetas(log_level <= 10)
        self._override = override
        self._spawn()

    def _spawn(self):
        self.ac.headers['Host'] = self.ac.domain
        helper.mkdir_p(self.save_dir, is_dir=True)
        self.scan_all_songs()

    def is_file_id3_ok(self, song_name):
        song_pth = os.path.join(self.save_dir, song_name)
        if song_pth[-4:] != '.mp3':
            song_pth += '.mp3'

        if helper.is_file_ok(song_pth):
            has_pic, song_id3 = self._song_metas.get_song_meta(song_pth)
            return has_pic, song_pth
        return False, None

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

    def parse_song(self, dat):
        if isinstance(dat, str):
            dat = json.loads(dat)
        url = dat['url']
        if self.site == 'qq':
            song_extension = url.split('?')[0].split('.')[-1]
        else:
            # elif self.site == 'netease':
            #     song_extension = url.split('.')[-1]
            # else:
            song_extension = 'mp3'
        return song_extension

    def get_song_album(self, dat):
        """
        TALB
        """
        if self.site == 'qq':
            return self.get_qq_album(dat)
        elif self.site == 'netease':
            return self.get_netease_album(dat)
        else:
            return ''

    def get_netease_album(self, dat):
        link = urljoin('https://music.163.com', dat['link'].split('#')[1])
        album = self.site_netease.do_get(link)
        return album

    def get_qq_album(self, dat):
        doc = self.ac.bs4get(dat['link'], use_cache=self.use_cache)
        _pg = re.compile('g_SongData = *')
        rs = doc.find(string=_pg)
        rs = rs.split(' = ')
        detail = json.loads(rs[1].strip()[:-1])
        return detail['albumname']

    def download(self, src, save_to):
        if not self._override and helper.is_file_ok(save_to):
            zlog.debug('{} is downloaded.'.format(save_to))
        else:
            zlog.debug('try get {}'.format(save_to))
            wget.download(src, out=save_to)
            # wget output end without new line
            print()
            zlog.info('downloaded {}'.format(helper.G.format(save_to)))

    def save_song(self, song):
        extension = self.parse_song(song)
        title = song['author'] + '-' + song['title']
        song_pth = os.path.join(self.save_dir, '{}.{}'.format(title, extension))
        pic_pth = os.path.join(self.ac.cache['site_media'], title + '.jpg')
        try:
            if not song.get('url'):
                zlog.warning('song has no url: {}'.format(song))
                return
            self.download(song['url'], song_pth)
            self.download(song['pic'], pic_pth)
        except Exception as ex:
            zlog.error('failed {}'.format(song))
            error_hint('maybe cache expired, use -nc to skip the cache')

            traceback.print_exc()
            os._exit(-1)
        self.update_song(song, song_pth, pic_pth)

    def update_song(self, song, song_pth, pic_pth):
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
            site_dat['TALB'] = self.get_song_album(song)

        if not id3_same:
            CP.G('update {}'.format(site_dat))
            self._song_metas.update_song_meta(song_pth, site_dat)

    def scan_all_songs(self):
        self.all_songs = helper.walk_dir_with_filter(self.save_dir, prefix=['.DS_Store'])
        self.all_songs = [x.split('/')[-1] for x in self.all_songs]

    def is_file_exist(self, song_name):
        """TODO: use sqlite to store song names"""
        song_name = song_name.split('-')[-1].split('.')[0]
        # print(song_name, local_musics)
        similar = []
        for song in self.all_songs:
            song_ = '.'.join(song.split('.')[:-1])
            candidates = [song_, *song_.split('-')]
            if song_name in '#'.join(candidates):
                similar.append(song)

        return similar


class Netease(object):
    def __init__(self, log_level=10):
        self.home = 'https://music.163.com/'
        self.ac = AsyncCrawler(
            site_init_url=self.home,
            base_dir=os.path.expanduser('~/.crawler'),
            timeout=10,
            log_level=log_level,
        )
        self.ac.headers['get'] = NeteaseHeaders.get

    def do_get(self, url):
        doc = self.ac.bs4get(url)
        album_doc = doc.find_all(class_='des s-fc4')[-1]
        album = album_doc.a.text
        return album