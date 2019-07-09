#! /usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'lihe <imanux@sina.com>'
__date__ = '11/16 22:17'
__description__ = '''
'''
import os
import sys

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

import click
from ihelp import helper
import ipretty

from sonimei.__const__ import CP, PRETTY, __VERSION__, SITES
from sonimei._cfg import cfg, zlog
from sonimei.zutil import fmt_help, error_hint
from sonimei._sonimei import Sonimei, NeteaseDL, check_player, check_failure, check_local, FailureHandle


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('Version {}'.format(__VERSION__))
    ctx.exit()


@click.command(
    context_settings=dict(
        help_option_names=['-h', '--help'],
        terminal_width=200,
    ),
)
@click.option('--auto_mode', '-a',
              is_flag=True,
              help=fmt_help('auto get music name from NeteaseMusic/Spotify', '-a'))
@click.option('--from_163_logs', '-163',
              is_flag=True,
              help=fmt_help('force using netease logs to download', '-163'))
@click.option('--clear_failure_songs', '-cfs',
              is_flag=True,
              help=fmt_help('clear all download failure songs', '-cfs'))
@click.option('--failure_songs', '-fs',
              is_flag=True,
              help=fmt_help('show failure songs and download', '-fs'))
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
@click.option('--override', '-o',
              is_flag=True, default=False,
              help=fmt_help('force override local file', '-o'))
@click.option('--site', '-s',
              default='qq',
              type=click.Choice(list(SITES.values())),
              help=fmt_help('the song source site', '-s <{}>'.format('/'.join(SITES.values()))))
@click.option('--scan_mode', '-scan',
              is_flag=True,
              help=fmt_help('scan all songs and add id3 info', '-scan'))
@click.option('--timeout', '-to', type=int,
              help=fmt_help('default timeout', '-to'))
@click.option('--version', '-V', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
def run(
        name, site, multiple, no_cache, log_level,
        scan_mode, timeout, override,
        auto_mode, failure_songs, clear_failure_songs,
        from_163_logs,
):
    """ a lovely script use sonimei search qq/netease songs """
    # if scan_mode, will be all songs local
    # else will be the name passed in
    scanned_songs = []
    timeout = timeout or cfg.get('snm.timeout')
    force_netease = False
    if clear_failure_songs:
        FailureHandle().dump_failure_songs([], action='clear')
        os._exit(0)

    if auto_mode:
        force_netease, scanned_songs = check_player(auto_mode)

    if failure_songs:
        scanned_songs = check_failure(failure_songs)

    if from_163_logs:
        force_netease = from_163_logs

    if force_netease:
        _client = NeteaseDL(not no_cache, log_level=log_level * 10, timeout=timeout, override=override)
    else:
        _client = Sonimei(site, not no_cache, log_level=log_level * 10, timeout=timeout, override=override)

    if scan_mode:
        _client.store.scan_all_songs()
        scanned_songs = _client.store.all_songs

    if name:
        scanned_songs = [x for x in name.split('#') if x]

    if not scanned_songs:
        error_hint('{0}>>> use -h for details <<<{0}'.format('' * 16), quit_out=None)

    for i, name in enumerate(scanned_songs):
        songs_store = {}
        page = 1
        is_searched_from_site = False
        CP.F((PRETTY.symbols['right'] + ' ') * 2, 'processing/total: {}/{}'.format(i + 1, len(scanned_songs)))

        while True:
            if not is_searched_from_site and check_local(scan_mode, _client.store, name):
                CP.G(PRETTY.symbols['end'], 'quit')
                break

            status, song_pth = _client.store.is_file_id3_ok(name)
            if status:
                CP.G(PRETTY.symbols['music'], '[{}] is found and updated'.format(song_pth))
                if not override:
                    error_hint('>>> you can do force download with -o <<<',
                               empty_line=False,
                               bg='black', fg='yellow')
                    break

            songs = songs_store.get(page)
            if not songs:
                zlog.info('from sonimei({}) try: {}/{}'.format(ipretty.G.format(site), name, page))
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
