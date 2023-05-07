from setuptools import setup, find_packages
import codecs
import os

#To create package: python setup.py sdist bdist_wheel
#To upload package: twine upload dist/*

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '1.0.9'
DESCRIPTION = 'This python script will sync user ratings for Movies and TV Shows both ways between Trakt and IMDb.'

# Setting up
setup(
    name="IMDbTraktSyncer",
    version=VERSION,
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    url="https://github.com/RileyXX/IMDb-Trakt-Syncer",
    packages=find_packages(),
    install_requires=['requests', 'feedparser', 'selenium'],
    keywords=['python', 'video', 'trakt', 'imdb', 'ratings', 'sync', 'movies', 'tv shows'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'IMDbTraktSyncer = IMDbTraktSyncer.IMDbTraktSyncer:main'
        ]
    }
)