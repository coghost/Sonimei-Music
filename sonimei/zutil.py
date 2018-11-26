# -*- coding: utf-8 -*-
__author__ = 'lihe <imanux@sina.com>'
__date__ = '11/26 13:53'
__description__ = '''
'''

import os
import sys

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)
from izen import helper


def fmt_help(*args, show_more=True, opt_hint='[OPT] '):
    desc = helper.G.format(args[0])
    if show_more:
        if len(args) > 1:
            args = list(args[1:])
            args.insert(0, opt_hint)
            usage = ''.join([helper.B.format(x) for x in args])
            desc = '{}\n{}'.format(desc, usage)
    return desc
