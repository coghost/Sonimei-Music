# -*- coding: utf-8 -*-
__date__ = '06/22 15:36'
__description__ = '''
'''

import os
import sys

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

from decorator import decorator
import sh
import psutil


@decorator
def strfy(fn, *args, **kwargs):
    rs = fn(*args, **kwargs)
    return '\n'.join([x for x in rs.split('\n') if x])


class Spotify(object):
    def __init__(self):
        self.status = ''
        self.track = {}

    @strfy
    def _control(self, prop, ret_type='string'):
        _cmd = 'tell application "Spotify" to {} as {}'.format(prop, ret_type)
        # print(_cmd)
        try:
            return sh.osascript("-e", _cmd)
        except sh.ErrorReturnCode:
            return ''

    def get_status(self):
        return self._control('player state')


class SpotifyApp(Spotify):
    def __init__(self):
        super().__init__()
        self.app = {}

    def get_app(self):
        props = {
            'current track': 'string',
            'sound volume': 'string',
            'player state': 'string',
            'player position': 'string',
            'repeating enabled': 'string',
            'repeating': 'string',
            'shuffling enabled': 'string',
            'shuffling': 'string',
        }
        invalid = [
            'current track',
        ]
        for prop, _type in props.items():
            if prop in invalid:
                continue
            self.app[prop] = self._control(prop, _type)


class SpotifyTrack(Spotify):
    def __init__(self, minimize=True):
        super().__init__()
        self.minimize = minimize
        self._spawn()
        self.track_name = ''

    def __str__(self):
        return '{artist} - {name}'.format(**self.track)

    def _spawn(self):
        self.get_track()

    def _curr_track(self, prop, ret_type):
        return self._control('{} of current track'.format(prop), ret_type)

    def get_track(self):
        # self.status = self.get_status()
        # if self.status != 'playing':
        #     return
        props = {
            'artist': 'string',
            'album': 'string',
            'disc number': 'number',
            'duration': 'number',
            'played count': 'number',
            'track number': 'number',
            'starred': 'bool',
            'popularity': 'number',
            'id': 'string',
            'name': 'string',
            'artwork url': 'string',
            'artwork': 'string',
            'album artist': 'string',
            'spotify url': 'string',
        }
        invalid = [
            'starred',
        ]
        if self.minimize:
            props = {
                'name': 'string',
                'artist': 'string',
            }
        for prop, _type in props.items():
            if prop in invalid:
                continue
            self.track[prop] = self._curr_track(prop, _type)


if __name__ == '__main__':
    print('Spotify' in (p.name() for p in psutil.process_iter()))
