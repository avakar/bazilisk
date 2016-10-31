#!/usr/bin/env python
# coding: utf-8

from setuptools import setup

setup(
    name='bazilisk',
    version='0.1',

    description='',
    author='Martin Vejnár',
    author_email='vejnar.martin@gmail.com',
    url='https://github.com/avakar/bazilisk',
    license='MIT',

    packages=['bazilisk'],
    data_files=[('bazilisk', ['bazilisk/sln.mako', 'bazilisk/vcxproj.mako'])],
    install_requires=['mako'],
    entry_points={
        'console_scripts': ['bzlsk=bazilisk.bazilisk:_main'],
        },
    )
