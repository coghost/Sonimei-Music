#!/usr/bin/env bash

python setup.py sdist bdist_wheel
twine upload dist/* --verbose

rm -rf build
rm -rf dist
rm -rf sonimei.egg-info
