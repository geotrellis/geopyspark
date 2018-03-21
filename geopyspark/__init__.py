import os
import glob
import pkgutil
import sys
import tempfile
import zipfile
from pkg_resources import resource_filename
from geopyspark.geopyspark_utils import ensure_pyspark
ensure_pyspark()

from geopyspark.geopyspark_constants import JAR
from pyspark import RDD, SparkConf, SparkContext
from pyspark.serializers import AutoBatchedSerializer
from py4j.java_gateway import JavaClass, JavaObject


PACKAGE_EXTENSIONS = {'.zip', '.egg', '.jar'}


def get_spark_context():
    if SparkContext._active_spark_context:
        return SparkContext._active_spark_context
    else:
        raise RuntimeError("SparkContext must be initialized")


def scala_companion(class_name, gateway_client=None):
    """Returns referece to Scala companion object"""
    gateway_client = gateway_client or get_spark_context()._gateway._gateway_client
    return JavaClass(class_name + "$", gateway_client).__getattr__("MODULE$")


def create_python_rdd(jrdd, serializer):
    """Creates a Python RDD from a RDD from Scala.

    Args:
        jrdd (org.apache.spark.api.java.JavaRDD): The RDD that came from Scala.
        serializer (:class:`~geopyspark.AvroSerializer` or pyspark.serializers.AutoBatchedSerializer(AvroSerializer)):
            An instance of ``AvroSerializer`` that is either alone, or wrapped by ``AutoBatchedSerializer``.

    Returns:
        RDD
    """

    pysc = get_spark_context()

    if isinstance(serializer, AutoBatchedSerializer):
        return RDD(jrdd, pysc, serializer)
    else:
        return RDD(jrdd, pysc, AutoBatchedSerializer(serializer))


def geopyspark_conf(master=None, appName=None, additional_jar_dirs=[]):
    """Construct the base SparkConf for use with GeoPySpark.  This configuration
    object may be used as is , or may be adjusted according to the user's needs.

    Note:
        The GEOPYSPARK_JARS_PATH environment variable may contain a colon-separated
        list of directories to search for JAR files to make available via the
        SparkConf.

    Args:
        master (string): The master URL to connect to, such as "local" to run
            locally with one thread, "local[4]" to run locally with 4 cores, or
            "spark://master:7077" to run on a Spark standalone cluster.
        appName (string): The name of the application, as seen in the Spark
            console
        additional_jar_dirs (list, optional): A list of directory locations that
            might contain JAR files needed by the current script.  Already
            includes $(pwd)/jars.

    Returns:
        SparkConf
    """

    conf = SparkConf()

    if not appName:
        raise ValueError("An appName must be provided")
    else:
        conf.setAppName(appName)

    if master:
        conf.setMaster(master)

    if 'GEOPYSPARK_JARS_PATH' in os.environ:
        additional_jar_dirs = additional_jar_dirs + os.environ['GEOPYSPARK_JARS_PATH'].split(':')

    conf.set(key='spark.ui.enabled', value='false')
    conf.set(key='spark.serializer', value='org.apache.spark.serializer.KryoSerializer')
    conf.set(key='spark.kryo.registrator', value='geopyspark.geotools.kryo.ExpandedKryoRegistrator')

    current_location = os.path.dirname(os.path.realpath(__file__))
    cwd = os.getcwd()

    local_prefixes = [
        os.path.abspath(os.path.join(current_location, 'jars')),
        os.path.abspath(os.path.join(cwd, 'jars')),
        os.path.abspath(os.path.join(cwd, '../geopyspark/jars'))
    ]
    possible_jars = [os.path.join(prefix, '*.jar') for prefix in local_prefixes + additional_jar_dirs]
    configuration = os.path.join(current_location, 'command', 'geopyspark.conf')

    if not possible_jars:
        if os.path.isfile(configuration):
            with open(os.path.join(configuration)) as config_file:
                possible_jars.append(os.path.relpath(config_file.read(), cwd))

    module_jars = [
        os.path.abspath(resource_filename('geopyspark.jars', JAR))
    ]

    jar_dirs = [(jar, os.path.dirname(jar)) for jar in module_jars]

    for jar, jar_dir in jar_dirs:
        if jar_dir not in local_prefixes:
            possible_jars.append(jar)

    returned = [glob.glob(jar_files) for jar_files in possible_jars]
    jars = [jar for sublist in returned for jar in sublist]

    if not jars:
        raise IOError("Failed to find any jars. Looked at these paths {}".format(possible_jars))

    jar_string = ",".join(jars)
    conf.set(key='spark.jars', value=jar_string)

    conf.set(key='spark.driver.memory', value='8G')
    conf.set(key='spark.executor.memory', value='8G')

    if master == 'yarn':
        os.environ['PYSPARK_PYTHON'] = sys.executable

        spark_home = process_spark_home(spark_home)

        # TODO: Better way to get this?
        install_requires=[
            'protobuf>=3.3.0',
            'numpy>=1.8',
            'shapely>=1.6b3',
            'pytz',
            'python-dateutil>=2.6.1',
            'geopyspark'
        ]

        pyspark_dir = os.path.join(spark_home, 'python')
        pyspark_lib_dir = os.path.join(pyspark_dir, 'lib')
        pyspark_lib_zips = glob.glob(os.path.join(pyspark_lib_dir, '*.zip'))
        sys_path_set = {path for path in sys.path}
        for pyspark_lib_zip in pyspark_lib_zips:
            if pyspark_lib_zip not in sys_path_set and os.path.basename(pyspark_lib_zip) != 'pyspark.zip':
                sys.path.insert(1, pyspark_lib_zip)
        if pyspark_dir not in sys_path_set:
            sys.path.insert(1, pyspark_dir)

        py_files = pyspark_lib_zips + process_executor_packages(install_requires)

        conf.set(key='spark.yarn.dist.jars', value=jar_string)
        conf.set(key='spark.yarn.dist.files', value=','.join(py_files))
        conf.setExecutorEnv('PYTHONPATH', ":".join(map(os.path.basename, py_files)))
        conf.setExecutorEnv('PYSPARK_PYTHON', sys.executable)

    return conf


def _ensure_callback_gateway_initialized(gw):
    """ Ensure that python callback gateway is started and configured.
    Source: ``pyspark/streaming/context.py`` in ``StreamingContext._ensure_initialized``
    """
    # start callback server
    # getattr will fallback to JVM, so we cannot test by hasattr()
    if "_callback_server" not in gw.__dict__ or gw._callback_server is None:
        gw.callback_server_parameters.eager_load = True
        gw.callback_server_parameters.daemonize = True
        gw.callback_server_parameters.daemonize_connections = True
        gw.callback_server_parameters.port = 0
        gw.start_callback_server(gw.callback_server_parameters)
        cbport = gw._callback_server.server_socket.getsockname()[1]
        gw._callback_server.port = cbport
        # gateway with real port
        gw._python_proxy_port = gw._callback_server.port
        # get the GatewayServer object in JVM by ID
        jgws = JavaObject("GATEWAY_SERVER", gw._gateway_client)
        # update the port of CallbackClient with real port
        jgws.resetCallbackClient(jgws.getCallbackClient().getAddress(), gw._python_proxy_port)


def process_spark_home(spark_home):
    if spark_home is None:
        spark_home = os.environ.get('SPARK_HOME', None)
    assert spark_home is not None, 'unable to resolve SPARK_HOME'
    assert os.path.isdir(spark_home), '%s is not a directory' % spark_home
    os.environ['SPARK_HOME'] = spark_home
    return spark_home


def process_executor_packages(executor_packages):
    version_info = sys.version_info
    tmp_path = os.path.join(tempfile.gettempdir(), 'spark-python-%s.%s' % (version_info.major, version_info.minor))
    if not os.path.isdir(tmp_path):
        os.makedirs(tmp_path)
    driver_packages = {module for _, module, package in pkgutil.iter_modules() if package is True}
    executor_files = []
    for executor_package in executor_packages:

        if executor_package not in driver_packages:
            raise ImportError('unable to locate ' + executor_package + ' installed in driver')

        package = sys.modules.get(executor_package, None)
        if package is None:
            package = pkgutil.get_loader(executor_package).load_module(executor_package)

        package_path = os.path.dirname(package.__file__)
        package_root = os.path.dirname(package_path)

        if package_root[-4:].lower() in PACKAGE_EXTENSIONS:
            executor_files.append(package_root)
        elif os.path.isdir(package_root):
            package_version = getattr(package, '__version__', getattr(package, 'VERSION', None))
            zip_name = "%s.zip" % executor_package if package_version is None \
                else "%s-%s.zip" % (executor_package, package_version)
            zip_path = os.path.join(tmp_path, zip_name)
            if not os.path.isfile(zip_path):
                zip_package(package_path, zip_path)
            executor_files.append(zip_path)

    return executor_files


def zip_package(package_path, zip_path):
    path_offset = len(os.path.dirname(package_path)) + 1
    with zipfile.PyZipFile(zip_path, 'w') as writer:
        for root, _, files in os.walk(package_path):
            for file in files:
                full_path = os.path.join(root, file)
                archive_path = full_path[path_offset:]
                writer.write(full_path, archive_path)


__all__ = ['geopyspark_conf']

from . import geotrellis
from .geotrellis import *
from . import vector_pipe
from .vector_pipe import *
from . import geotools
from .geotools import *
from . import geomesa
from .geomesa import *

__all__.extend(geotrellis.__all__)
__all__.extend(vector_pipe.__all__)
__all__.extend(geotools.__all__)
__all__.extend(geomesa.__all__)
