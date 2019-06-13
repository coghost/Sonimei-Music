# -*- coding: utf-8 -*-
__author__ = 'lihe <imanux@sina.com>'
__date__ = '11/26 13:00'
__description__ = '''
'''

import os
import sys

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

from izen.icfg import Conf, LFormatter
import logzero

PROJECT = 'sonimei'

cfg = Conf(
    pth=os.path.expanduser('~/.{0}/{0}.cfg'.format(PROJECT)),
    dat={
        'pretty.symbols': ' ,,,, ,,,,,,,,ﴖ,,,,,,,♪,',
        'snm.save_dir': '~/Music/sonimei',
        'snm.timeout': 15,
        'snm.progress_symbol': '.',
    },
).cfg

logzero.formatter(
    LFormatter(log_pre=cfg.get('log.symbol', ''))
)
zlog = logzero.logger
