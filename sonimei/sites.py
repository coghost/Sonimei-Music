# -*- coding: utf-8 -*-
__date__ = '05/18 12:52'
__description__ = '''
'''

import os
import sys

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

from izen.crawler import AsyncCrawler
from sonimei.site_header import NeteaseHeaders


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
