from setuptools import setup
import sys

if sys.version_info < (3, 3):
    sys.exit("GeoPySpark does not support Python versions before 3.3")

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
        'fastavro>=0.13.0',
        'numpy>=1.8',
        'shapely>=1.6b3'
    ],
    packages=[
        'geopyspark',
        'geopyspark.geotrellis',
        'geopyspark.tests',
        'geopyspark.tests.schema_tests',
        'geopyspark.jars',
    ],
    include_package_data=True,
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
