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
import click
import psutil

from sonimei.__const__ import CP, HIGH_Q
from sonimei.icfg import cfg
from sonimei.site_header import SonimeiHeaders
from sonimei.sites import Downloader, MusicStore
from sonimei.sites import MockAlbum, QQAlbum, NeteaseAlbum, KugouAlbum
from sonimei._spotify import SpotifyTrack
from sonimei.zutil import error_hint

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
        self.failure_handle = FailureHandle()

        self._spawn()

    def _spawn(self):
        self.ac.headers['post'] = SonimeiHeaders.post
        self.ac.headers['Host'] = self.ac.domain
        helper.mkdir_p(self.music_save_dir, is_dir=True)

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
            self.failure_handle.log_and_quit(self._song_name, 0)

        return songs

    def save_song(self, song):
        song, song_pth, pic_pth = self._downloader.save_song(song)
        if not song:
            self.failure_handle.log_and_quit(self._song_name, 0)
        album_info = self._album_handler.get_album(song)
        self._update_song(song, song_pth, pic_pth, album_info)

    def _update_song(self, song, song_pth, pic_pth, album_info):
        self.store.update_song(song, song_pth, pic_pth, album_info)
        self.failure_handle.dump_failure_songs(self._song_name, action='del')


class FailureHandle(object):
    def __init__(self):
        self.failure_store = cfg.get('snm.failure_store')

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

    def dump_failure_songs(self, song, action='add'):
        dat = self.load_failure_songs() or []
        dat = [x for x in dat if x]
        if action == 'add':
            dat.append(song)
        elif action == 'del':
            if song in dat:
                dat.pop(dat.index(song))
        elif action == 'clear':
            dat = []
        else:
            zlog.error('unsupported action: ({})'.format(action))
            return

        dat = list(set(dat))
        dat = yaml.dump(dat)
        file_pth = os.path.expanduser(self.failure_store)
        helper.write_file(dat, file_pth)


class NeteaseDL(Sonimei):
    """
    this will parse local logs for everything we need.
    beware this will only work when NeteaseMusic is playing.
    """

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
            self.failure_handle.log_and_quit(self._song_name, 0)
        self._update_song(song, song_pth, pic_pth, album_info)


def check_failure(failure_songs):
    if not failure_songs:
        return []
    scanned_songs = []
    dat = FailureHandle().load_failure_songs()
    if not dat:
        error_hint('{0}>>> no failed songs <<<{0}'.format('' * 16), bg='green')
    for i, s in enumerate(dat):
        CP.Y('{}. {}'.format(i + 1, s))
        scanned_songs.append(s)
    ch = click.confirm(helper.C.format('do you want continue with downloading all failure songs...'), default=True)
    if not ch:
        os._exit(0)
    return scanned_songs


def check_player(auto_mode):
    choice = False
    if not auto_mode:
        return choice, []

    players = ['Spotify', 'NeteaseMusic']
    player = ''
    for player in players:
        if player.lower() in (p.name().lower() for p in psutil.process_iter()):
            break

    return globals().get('check_{}_playing'.format(player.lower()))()


def check_spotify_playing():
    st = SpotifyTrack()
    CP.G('current playing  : [{}]'.format(
        helper.Y.format('{artist} - {name}'.format(**st.track))))
    if st.track:
        return False, ['{artist} - {name}'.format(**st.track)]


def check_neteasemusic_playing():
    choice = False
    song = get_playing_netease_music()
    if not song:
        error_hint('{0}>>> some error happened, contact author for help <<<{0}'.format('' * 16))

    song_info = '{}-{}'.format(song['author'], song['title'])
    CP.G('current playing  : [{}]'.format(
        helper.Y.format(
            '{}({}M/{}bits)'.format(
                song_info,
                round(int(song['fileSize']) / (1024.0 * 1024.0), 2),
                song['bitrate'])
        )))
    scanned_songs = [song_info]
    if int(song['bitrate']) >= HIGH_Q:
        # if bitrate >= 320, we will force use it
        choice = click.confirm(helper.C.format('high quality song got, force use NeteaseMusic/163 Source ?'),
                               default=True)
    return choice, scanned_songs


def get_playing_netease_music():
    songs = ''
    try:
        netease = NeteaseDL()
        song = netease.search_it()
        return song
    except Exception as e:
        zlog.error('{}, {}'.format(e, songs))
        return {}


def check_local(scan_mode, client, name):
    """judge if found from local, only press ``s`` will go next"""
    if scan_mode:
        return False

    client.scan_all_songs()
    cache = client.is_file_exist(name)
    if cache:
        CP.G('Found from local, still want search and download???')
        CP.R('press s to skip local, and re-download, or other key to exit')
        c = helper.num_choice(
            cache, default='q', valid_keys='s',
            extra_hints='s-skip',
        )
        return c != 's'
