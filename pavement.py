from paver.easy import *
from paver.setuputils import setup
from setuptools import find_packages
from functools import wraps

version = '0.1'

classifiers = [
    # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
    "Development Status :: 1 - Planning",
    ]

install_requires = []

entry_points="""
    # -*- Entry points: -*-
    """

# compatible with distutils of python 2.3+ or later
setup(
    name='loaf',
    version=version,
    description='gotta make bread if you want crumbs',
    long_description=open('README.rst', 'r').read(),
    classifiers=classifiers,
    keywords='',
    author='whit',
    author_email='whit @ nocoast.us',
    url='http://www.whitmorriss.org/loaf',
    license='BSD',
    packages = find_packages(exclude=['bootstrap', 'pavement',]),
    include_package_data=True,
    test_suite='nose.collector',
    zip_safe=False,
    install_requires=install_requires,
    entry_points=entry_points,
    )

options(
    # -*- Paver options: -*-
    minilib=Bunch(
        extra_files=[
            # -*- Minilib extra files: -*-
            ]
        ),
    sphinx=Bunch(
        docroot='docs',
        builddir="_build",
        sourcedir=""
        ),
    virtualenv=Bunch(
        packages_to_install=[
            # -*- Virtualenv packages to install: -*-
            'github-tools',
            "nose",
            "Sphinx>=0.6b1",
            "virtualenv",
            "setuptools_git",
            "jstools"],
        install_paver=True,
        script_name='bootstrap.py',
        paver_command_line='after_bootstrap'
        ),
    )

options.setup.package_data = paver.setuputils.find_package_data(
    'loaf', package='loaf', only_in_packages=False)


def task_all_loaded(*needed):
    def all_wrap(f):
        @task
        @needs(needed)
        @wraps(f)
        def wrapper(*args, **kw):
            if ALL_TASKS_LOADED:
                return f(*args, **kw)
            else:
                raise ValueError("Cannot run if all commands are not loaded")
        return wrapper
    return all_wrap



@task_all_loaded('generate_setup', 'minilib', 'setuptools.command.sdist')
def sdist():
    """Overrides sdist to make sure that our setup.py is generated."""
    pass


@task
def after_bootstrap(options):
    sh("bin/pip install -r reqs.txt")


@task
def git_ol(options):
    """
    Check out openlayers from github
    """
    src = path('src')
    if not (src / 'openlayers').exists():
        with pushd(src):
            sh("git clone git@github.com:ccnmtl/openlayers.git")

try:
    # Optional tasks, only needed for development
    # -*- Optional import: -*-
    from github.tools.task import *
    from paver.virtual import bootstrap
    import paver.doctools
    import paver.virtual
    import paver.misctasks
    ALL_TASKS_LOADED = True
except ImportError, e:
    info("some tasks could not not be imported.")
    debug(str(e))
    ALL_TASKS_LOADED = False
