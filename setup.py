import os
from setuptools import setup, find_packages

version = '1'
README = os.path.join(os.path.dirname(__file__), 'README')
long_description = 'Tool for analyzing page load performance.'

setup(
    name='pageload',
    version=version,
    description=long_description,
    author='Scott Frazer',
    author_email='sfrazer@bluestatedigital.com',
    packages=['pageload'],
    package_dir={'pageload': 'pageload'},
    entry_points={
      'console_scripts': [
            'pageload = pageload.Main:Cli'
        ]
      },
    license = "GPL",
    keywords = "PageSpeed, Performance, Web, HTTP",
    url = "http://bluestatedigital.com/",
    classifiers=[
          "Programming Language :: Python",
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "Natural Language :: English",
      ]
    )
