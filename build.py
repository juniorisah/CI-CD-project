import sys
import os

from pybuilder.core import use_plugin

use_plugin("python.core")
use_plugin("python.distutils")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")
use_plugin("python.flake8")
use_plugin("copy_resources")

default_task = ["install_dependencies", "analyze", "publish"]

name = "pybuilder-cdo"
summary = "AT&T CDO build extensions for PyBuilder."
version = "1.3.1"

# Augment path so we can include our own code within build process
content_path = os.path.abspath("src/main/python/")
sys.path += [content_path]
print(sys.path)
from pybuilder_cdo import *


@init
def initialize(project):
    is_release = str_to_bool(project.get_property("release", "False"))

    if not is_release:
        project.version = version + ".isa"

    project.build_depends_on("unittest-xml-reporting")

    project.depends_on("jinja2")
    project.depends_on("docker")
    project.depends_on("twine")
    project.depends_on("gitpython")

    # Set by the core plugin but we set it again after having manipulated the version
    project.set_property("dir_dist", "$dir_target/dist/{0}-{1}".format(project.name, project.version))

    sys.path.append(project.expand_path("$dir_target"))

    project.set_property("flake8_break_build", False)
    project.set_property("flake8_verbose_output", True)

    project.set_property("copy_resources_target", "${dir_dist}")
    project.set_property("copy_resources_glob", ["src/main/resources/*"])

    project.install_file("./", "src/main/resources/setup.cfg")

    project.set_property("distutils_commands", "sdist")
    project.set_property("distutils_classifiers", ["Development Status :: 4 - Beta",
                                                   "Environment :: No Input/Output (Daemon)",
                                                   "Programming Language :: Python :: 3",
                                                   "Topic :: Scientific/Engineering"])

    project.set_property("unittest_module_glob", "test_*")


def str_to_bool(value):
    value = value.lower()

    if value in ["true", "1", "yes"]:
        return True
    elif value in ["false", "0", "no"]:
        return False
    else:
        raise KeyError("Could not map '{0}' to bool.".format(value))
