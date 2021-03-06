#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = 'lihe <imanux@sina.com>'
__date__ = '11/26 14:37'
__description__ = '''
'''

from setuptools import setup, find_packages
from sonimei.__const__ import __VERSION__

setup(
    name='sonimei',
    version=__VERSION__,
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['*.tpl', '*.md']},
    author='lihe',
    author_email='imanux@sina.com',
    url='https://github.com/coghost/Sonimei-Music',
    description='music downloader of music.sonimei.cn',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    license='GPL',
    install_requires=[
        'wget', 'click', 'logzero', 'mutagen', 'lxml',
        'requests', 'selenium', 'PyYAML', 'psutil', 'decorator',
        'sh', 'ipretty', 'ihelp', 'icraw', 'icfg'
    ],
    entry_points={
        'console_scripts': [
            'snm = sonimei.app:run'
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/coghost/Sonimei-Music/issues',
        'Source': 'https://github.com/coghost/Sonimei-Music',
    },
    python_requires='>=3.7',
    classifiers=[
        'Programming Language :: Python :: 3.7',
    ],
    keywords=['sonimei', 'music downloader']
)
