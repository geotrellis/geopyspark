import sys
import os
import subprocess

from setuptools import setup
from setuptools.command.install import install


if sys.version_info < (3, 3):
    sys.exit("GeoPySpark does not support Python versions before 3.3")

URL = 'https://github.com/locationtech-labs/geopyspark/releases/download/v0.1.0-RC1/'
JAR = 'geotrellis-backend-assembly-0.1.0.jar'
JAR_PATH = 'geopyspark/jars/'


class Installer(install):
    def run(self):
        if not os.path.isfile(JAR_PATH):
            subprocess.call(['curl', '-L', URL + JAR, '-o', JAR_PATH + JAR])
        install.run(self)


setup(
    name='geopyspark',
    version='0.1.0',
    author='Jacob Bouffard, James McClain',
    author_email='jbouffard@azavea.com, jmcclain@azavea.com',
    download_url='http://github.com/locationtech-labs/geopyspark',
    description='Python bindings for GeoTrellis and GeoMesa',
    long_description=open('README.rst').read(),
    license='LICENSE',
    install_requires=[
        'avro-python3>=1.8',
        'numpy>=1.8',
        'shapely>=1.6b3'
    ],
    packages=[
        'geopyspark',
        'geopyspark.geotrellis',
        'geopyspark.tests',
        'geopyspark.tests.schema_tests',
        'geopyspark.jars'
    ],
    cmdclass={'install': Installer},
    scripts=[],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ]
)
