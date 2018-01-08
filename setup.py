from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
  name = 'pats',
  packages=find_packages(exclude=['contrib', 'docs', 'tests']),
  version = '0.3',
  description = 'Client for the PATS API (www.pats.org.uk)',
  long_description=long_description,
  author = 'Brendan Quinn',
  author_email = 'brendan@cluefulmedia.com',
  url = 'https://github.com/bquinn/pats-api-python',
  download_url = 'https://github.com/bquinn/pats-api-python/archive/0.3.tar.gz',
  keywords = ['api', 'publishing', 'advertising'],
  classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
  ],
)
