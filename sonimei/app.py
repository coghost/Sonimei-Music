#! /usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'lihe <imanux@sina.com>'
__date__ = '11/16 22:17'
__description__ = '''
'''
import os
import sys
import json

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

import click
from izen import helper
from sonimei.__const__ import CP, PRETTY
from sonimei.icfg import cfg, zlog
from sonimei.zutil import fmt_help, error_hint
from sonimei._sonimei import Sonimei, NeteaseDL

HIGH_Q = 320

SITES = {
    'qq': 'qq',
    '163': '163',
    'kugou': 'kugou',
}


def get_playing_netease_music():
    songs = ''
    try:
        netease = NeteaseDL()
        song = netease.search_it()
        return song
    except Exception as e:
        zlog.error('{}, {}'.format(e, songs))
        return {}


def local_existed(scan_mode, client, name):
    """judge if found from local, only press ``s`` will go next"""
    if not scan_mode:
        client.scan_all_songs()
        cache = client.is_file_exist(name)
        if cache:
            CP.G('Found from local, still want search and download???')
            CP.R('press s to skip local, and re-download, or other key to exit')
            c = helper.num_choice(
                cache, default='q', valid_keys='s',
                extra_hints='s-skip',
            )
            if c == 's':
                return False
            return True
    return False


@click.command(
    context_settings=dict(
        help_option_names=['-h', '--help'],
        terminal_width=200,
    ),
)
@click.option('--force_mode', '-f',
              is_flag=True, default=False,
              help=fmt_help('force override local file', '-f'))
@click.option('--log_level', '-l',
              default=2, type=click.IntRange(1, 5),
              help=fmt_help('set log level', '-l <1~5>\n1=Debug,2=Info,3=Warn,4=Error,5=Fatal'))
@click.option('--multiple', '-m',
              is_flag=True,
              help=fmt_help('download multiple songs', '-m'))
@click.option('--name', '-n',
              help=fmt_help('the name of song/songs', '-n <song1#song2#...>'))
@click.option('--no_cache', '-nc',
              is_flag=True,
              help=fmt_help('use no cache', '-nc'))
@click.option('--site', '-s',
              default='qq',
              type=click.Choice(list(SITES.values())),
              help=fmt_help('the song source site', '-s <{}>'.format('/'.join(SITES.values()))))
@click.option('--scan_mode', '-scan',
              is_flag=True,
              help=fmt_help('scan all songs and add id3 info', '-scan'))
@click.option('--auto_mode', '-a',
              is_flag=True,
              help=fmt_help('auto get music name from neteaseMusic', '-a'))
@click.option('--failure_songs', '-fs',
              is_flag=True,
              help=fmt_help('show failure songs', '-fs'))
@click.option('--force_netease', '-163',
              is_flag=True,
              help=fmt_help('show failure songs', '-163'))
@click.option('--timeout', '-to', type=int,
              help=fmt_help('default timeout', '-to'))
def run(name, site, multiple, no_cache, log_level, scan_mode, timeout, force_mode, auto_mode, failure_songs,
        force_netease):
    """ a lovely script use sonimei search qq/netease songs """
    if not name and not scan_mode and not auto_mode and not failure_songs:
        error_hint('{0}>>> use -h for details <<<{0}'.format('' * 16))
        return

    # if scan_mode, will be all songs local
    # else will be the name passed in
    scanned_songs = []
    timeout = timeout or cfg.get('snm.timeout')
    if not force_netease:
        _client = Sonimei(site, not no_cache, log_level=log_level * 10, timeout=timeout, override=force_mode)
    else:
        _client = NeteaseDL(log_level=log_level * 10)

    if failure_songs:
        dat = _client.load_failure_songs()
        if not dat:
            error_hint('{0}>>> no failed songs <<<{0}'.format('' * 16), bg='green')
            os._exit(0)
        for i, s in enumerate(dat):
            CP.Y('{}. {}'.format(i + 1, s))
            scanned_songs.append(s)
        ch = click.confirm(helper.C.format('do you want continue with downloading all failure songs...'), default=True)
        if not ch:
            os._exit(0)

    if scan_mode:
        scanned_songs = _client.store.all_songs
    if auto_mode:
        song = get_playing_netease_music()
        if not song:
            error_hint('{0}>>> some error happened, contact author for help <<<{0}'.format('' * 16))
            os._exit(0)
        else:
            song_info = '{}-{}'.format(song['author'], song['title'])
            CP.G('current playing: [{}]'.format(
                helper.Y.format(
                    '{}({}M/{}bits)'.format(
                        song_info,
                        round(int(song['fileSize']) / (1024.0 * 1024.0), 2),
                        song['bitrate']))))
            scanned_songs = [song_info]
            if int(song['bitrate']) >= HIGH_Q:
                # if bitrate >= 320, we will force use it
                ch = click.confirm(helper.C.format('high quality song got, force use NeteaseMusic/163 Source ?'),
                                   default=True)
                if ch:
                    _client = NeteaseDL(log_level=log_level * 10)

    if not scanned_songs:
        scanned_songs = [x for x in name.split('#') if x]

    for i, name in enumerate(scanned_songs):
        songs_store = {}
        page = 1
        is_searched_from_site = False
        CP.F((PRETTY.symbols['right'] + ' ') * 2, 'processing/total: {}/{}'.format(i + 1, len(scanned_songs)))

        while True:
            if not is_searched_from_site and local_existed(scan_mode, _client.store, name):
                CP.G(PRETTY.symbols['end'], 'quit')
                break

            status, song_pth = _client.store.is_file_id3_ok(name)
            if status:
                CP.G(PRETTY.symbols['music'], '[{}] is found and updated'.format(song_pth))
                break

            songs = songs_store.get(page)
            if not songs:
                zlog.info('from sonimei({}) try: {}/{}'.format(helper.G.format(site), name, page))
                songs = _client.search_it(name, page=page)
                if not isinstance(songs, list):
                    songs = [songs]
                songs_store[page] = songs

            is_searched_from_site = True
            song_info = [x['author'] + '-' + x['title'] for x in songs]

            c = helper.num_choice(
                song_info, valid_keys='p,n,s', depth=page,
                extra_hints='n-next,p-pre,s-skip',
                clear_previous=True,
            )
            if isinstance(c, str):
                if c in 'qQ':
                    return
                if c in 'bp':
                    if page > 1:
                        page -= 1
                    continue
                if c == 'n':
                    page += 1
                    continue
                if c == 's':  # skip current song
                    break
            _client.save_song(songs[c])

            # multiple mode is only worked in none scanned mode
            if not multiple:
                break


if __name__ == '__main__':
    run()
