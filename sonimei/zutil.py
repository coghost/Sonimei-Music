__author__ = 'lihe <imanux@sina.com>'
__date__ = '11/26 13:53'
__description__ = '''
'''

import os
import sys

app_root = '/'.join(os.path.abspath(__file__).split('/')[:-2])
sys.path.append(app_root)

import click
from ipretty import B, G

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def fmt_help(*args, show_more=True, opt_hint='[OPT] '):
    desc = G.format(args[0])
    if show_more:
        if len(args) > 1:
            args = list(args[1:])
            args.insert(0, opt_hint)
            usage = ''.join([B.format(x) for x in args])
            desc = '{}\n{}'.format(desc, usage)
    return desc


def error_hint(hints, empty_line=True, bg='blue', fg='white', quit_out=0):
    if empty_line:
        print()
    click.secho(hints, bg=bg, fg=fg)
    if empty_line:
        print()

    if isinstance(quit_out, int):
        os._exit(0)


def chrome_driver(**kwargs):
    options = Options()
    options.add_argument('--no-sandbox')
    # options.add_argument('--disable-gpu')
    # options.add_argument('blink-settings=imagesEnabled=false')
    prefs = {
        'profile.default_content_setting_values': {
            'images': kwargs.get('images', 0),
            'notifications': kwargs.get('notifications', 2),
        },
    }
    options.add_experimental_option("prefs", prefs)
    if kwargs.get('headless', False):
        options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1366, 768)
    driver.set_window_position(0, 0)
    driver.set_page_load_timeout(kwargs.get('to', 30))
    return driver


def headless_driver(headless=True):
    return chrome_driver(headless=headless)
