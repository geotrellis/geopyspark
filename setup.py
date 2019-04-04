import os
import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 3):
    sys.exit("GeoPySpark does not support Python versions before 3.3")

setup_args = dict(
    name='geopyspark',
    version='0.4.2',
    author='Jacob Bouffard, James McClain',
    author_email='jbouffard@azavea.com, jmcclain@azavea.com',
    download_url='http://github.com/locationtech-labs/geopyspark',
    description='Python bindings for GeoTrellis',
    long_description=open('README.rst').read(),
    license='LICENSE',
    install_requires=[
        'protobuf>=3.3.0',
        'numpy>=1.8',
        'shapely>=1.6b3',
        'pytz',
        'python-dateutil>=2.6.1'
    ],
    packages=find_packages(exclude=['tests']),
    entry_points={
        "console_scripts": ['geopyspark = geopyspark.command.configuration:main']
    },
    scripts=[],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)

if 'ASSEMBLED' in os.environ.keys():
    setup_args['include_package_data'] = True


if __name__ == "__main__":
    setup(**setup_args)
