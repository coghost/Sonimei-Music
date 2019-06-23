# -*- coding: utf-8 -*-
from izen.prettify import ColorPrint, Prettify
from sonimei.icfg import cfg

__VERSION__ = '0.1.8.1'

IS_PROD = False

PRETTY = Prettify(cfg)
CP = ColorPrint()
HIGH_Q = 320

SITES = {
    'qq': 'qq',
    '163': '163',
    'kugou': 'kugou',
}
