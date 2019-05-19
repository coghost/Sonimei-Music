# -*- coding: utf-8 -*-
__author__ = 'lihe <imanux@sina.com>'
__date__ = '11/25 21:02'
__description__ = '''
'''

import os
import sys

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

from izen.crawler import UA, ParseHeaderFromFile

__general_post_header__ = {
    'User-Agent': UA.mac_safari__,
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
    'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/x-www-form-urlencoded',
}


class Headers(object):
    get: dict = {}
    post: dict = {}


class SonimeiHeaders(Headers):
    __get_raw__ = """"""
    __post_raw__ = """"""
    get: dict = {}
    post: dict = dict({
        'Host': 'music.sonimei.cn',
        'Referer': 'http://music.sonimei.cn',
    }, **__general_post_header__)


class NeteaseHeaders(Headers):
    __get_raw__ = """
    GET /song?id=28285910 HTTP/1.1
    Host: music.163.com
    Connection: keep-alive
    Pragma: no-cache
    Cache-Control: no-cache
    Upgrade-Insecure-Requests: 1
    User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36
    Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8
    Referer: https://music.163.com/
    Accept-Encoding: gzip, deflate, br
    Accept-Language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7
    """
    __post_raw__ = """
    POST /weapi/v1/play/record?csrf_token=999a54076e49d4c4478d495fbd46573f HTTP/1.1
    Host: music.163.com
    Connection: keep-alive
    Content-Length: 520
    Origin: https://music.163.com
    User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36
    Content-Type: application/x-www-form-urlencoded
    Accept: */*
    Referer: https://music.163.com/user/songs/rank?id=381661302
    Accept-Encoding: gzip, deflate, br
    Accept-Language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7
    """
    get: dict = ParseHeaderFromFile(raw=__get_raw__).headers
    post: dict = ParseHeaderFromFile(raw=__post_raw__).headers


class QQHeaders(Headers):
    __get_raw__ = """
    Host: y.qq.com
    User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:64.0) Gecko/20100101 Firefox/64.0
    Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
    Accept-Language: en-US,zh-CN;q=0.8,zh;q=0.7,zh-TW;q=0.5,zh-HK;q=0.3,en;q=0.2
    Accept-Encoding: gzip, deflate, br
    Connection: keep-alive
    Cookie: yqq_stat=0; pgv_info=ssid=s7188190737; ts_last=y.qq.com/n/yqq/song/0019n6dS204TzZ.html; pgv_pvid=5820260362; ts_uid=5769688544; pgv_pvi=8737058816; pgv_si=s4310818816
    Upgrade-Insecure-Requests: 1
    Pragma: no-cache
    Cache-Control: no-cache
    """
    get: dict = ParseHeaderFromFile(raw=__get_raw__).headers


class KugouHeaders(Headers):
    __get_raw__ = """
    GET /song/ HTTP/1.1
    Host: www.kugou.com
    Connection: keep-alive
    Pragma: no-cache
    Cache-Control: no-cache
    Upgrade-Insecure-Requests: 1
    User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36
    Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3
    Accept-Encoding: gzip, deflate
    Accept-Language: en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7
    """
    get: dict = ParseHeaderFromFile(raw=__get_raw__).headers
