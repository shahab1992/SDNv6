from setuptools import setup, find_packages 
from codecs import open 
from os import path
here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='crackle',

    # Versions should comply with PEP440. For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.1.1',
    description='The Crackle project',
    long_description=long_description,

    # The project's main homepage.
    url='https://systemx.enst.fr/crackle.html',

    # Author details
    author='shahab SHARIAT BAGHERI',
    author_email='shahab1992@yahoo.com',
    # Choose your license
    license='GPL',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
	'Development Status :: 3 - Alpha',
	'Intended Audience :: Developers',
	'Topic :: Software Development :: Build Tools',
	'License :: OSI Approved :: GPL License',
	# Specify the Python versions you support here. In particular, ensure
	# that you indicate whether you support Python 2, Python 3 or both.
	#'Programming Language :: Python :: 2',
	#'Programming Language :: Python :: 2.6',
	#'Programming Language :: Python :: 2.7',
	#'Programming Language :: Python :: 3',
	#'Programming Language :: Python :: 3.2',
	#'Programming Language :: Python :: 3.3',
	'Programming Language :: Python :: 3.4',
    ],

    # What does your project relate to?
    keywords='Large experiments test with NFD',


    packages=['src'],
    package_dir={'src': 'src/'},

    # If there are data files included in your packages that need to be
    # installed, specify them here. If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={'src': [' localclient.sh','manage_key/config']},

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages.
    # see http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    data_files=[('usr/share/crackle/', ['scripts/localclient.sh','manage_key/config'])],

    scripts=['manage_key/manage_leader_key.sh'],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
	'console_scripts': [
	'crackle=src.crackle:main',
	],
    },
)
