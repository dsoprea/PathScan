import setuptools
import os

import fss

APP_PATH = os.path.dirname(fss.__file__)

with open(os.path.join(APP_PATH, 'resources', 'README.rst')) as f:
      _LONG_DESCRIPTION = f.read()

with open(os.path.join(APP_PATH, 'resources', 'requirements.txt')) as f:
      _INSTALL_REQUIRES = list(map(lambda s: s.strip(), f.readlines()))

_DESCRIPTION = \
    "Search a filesystem using zero or more file and directory filters."

setuptools.setup(
    name='pathscan',
    version=fss.__version__,
    description=_DESCRIPTION,
    long_description=_LONG_DESCRIPTION,
    classifiers=[
    ],
    keywords='filesystem file search scanner',
    author='Dustin Oprea',
    author_email='myselfasunder@gmail.com',
#    url='https://github.com/dsoprea/PyInotify',
    license='GPL 2',
    packages=setuptools.find_packages(exclude=['dev']),
    include_package_data=True,
    zip_safe=False,
    install_requires=_INSTALL_REQUIRES,
    package_data={
        'fss': [
            'resources/README.rst',
            'resources/requirements.txt',
        ]
    }
)
