"""The installation script for GeoPySpark.
Downloads the backend jar to the designated location and keeps a reference of where it was saved
to.
"""
import sys
import os
from os import path
import argparse

from geopyspark.geopyspark_constants import JAR, CWD, VERSION

# https://github.com/aheyne/geopyspark/releases/download/v0.3.0.gm.4/geopyspark-assembly-0.3.0.gm.4.jar
#JAR_URL = 'https://github.com/locationtech-labs/geopyspark/releases/download/v0.3.0/' + JAR
JAR_URL = 'https://github.com/aheyne/geopyspark/releases/download/v' + VERSION + '/' + JAR
DEFAULT_JAR_PATH = path.join(CWD, 'jars')
CONF = path.join(CWD, 'command', 'geopyspark.conf')


parser = argparse.ArgumentParser(description='GeoPySpark Command Line Utility')
parser.set_defaults(func=lambda c, x: parser.print_help())
subparser = parser.add_subparsers(help='Commands')

installer_parser = subparser.add_parser('install-jar', help='Installs the jar to a given path')
installer_parser.add_argument('--path', '-p', metavar='INSTALL_PATH')

path_parser = subparser.add_parser('jar-path', help='Path to downloaded jar')
path_parser.add_argument('--absolute', '-a', action='store_true',
                         help='Prints the absolute path of the jar')

def write_jar_path(jar_path):
    with open(CONF, 'w') as f:
        f.write(jar_path)

def download_jar(jar_path):
    import subprocess

    jar_location = path.join(jar_path, JAR)
    write_jar_path(jar_location)

    subprocess.call(['curl', '-L', JAR_URL, '-o', jar_location])

def get_jar_path():
    default_jar_location = path.join(DEFAULT_JAR_PATH, JAR)
    if path.isfile(default_jar_location):
        return default_jar_location
    elif path.isfile(CONF):
        with open(CONF, 'r') as f:
            return f.read()
    else:
        raise Exception("The jar path has never been set.")

def parse_args():
    result = parser.parse_args()
    remaining = sys.argv[1:]

    if 'install-jar' in remaining:
        if result.path:
            download_jar(result.path)
        else:
            download_jar(DEFAULT_JAR_PATH)
    elif 'jar-path' in remaining:
        if result.absolute:
            print(get_jar_path())
        else:
            jar_path = get_jar_path()
            rel_path = path.join(path.relpath(jar_path, os.getcwd()))
            print(rel_path)
    else:
        parser.print_help()

def main():
    parse_args()
