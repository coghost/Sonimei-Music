# -*- coding: utf-8 -*-
__VERSION__ = '0.1.8.2'

from ipretty import ColorPrint, Prettify
from sonimei._cfg import cfg

PRETTY = Prettify(cfg)
CP = ColorPrint()
HIGH_Q = 320

SITES = {
    'qq': 'qq',
    '163': '163',
    'kugou': 'kugou',
}
