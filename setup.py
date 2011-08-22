#!/usr/bin/env python
import os

version = '0.3.1'

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='redmodel',
      version=version,
      description='Python Library for Data Models Persisted in Redis',
      url='http://github.com/beatmax/redmodel',
      download_url='',
      long_description=read('README.rst'),
      author='Maximiliano Pin',
      author_email='mxcpin@gmail.com',
      maintainer='Maximiliano Pin',
      maintainer_email='mxcpin@gmail.com',
      keywords=['Redis', 'model', 'container'],
      license='GPL',
      packages=['redmodel', 'redmodel.models'],
      #test_suite='test.models.all_tests',
      classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python'],
    )

