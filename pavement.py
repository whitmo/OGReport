from paver.easy import *
import time
import shutil
import tarfile
from paver.setuputils import setup
from setuptools import find_packages
from functools import wraps, update_wrapper
import ConfigParser
import eventlet.api
import eventlet.util
import eventlet.coros
import eventlet.processes as proc
from urlgrabber.grabber import urlgrab, URLGrabError
from urlgrabber.progress import text_progress_meter
import socket
import getpass
import pwd
import sys

eventlet.util.wrap_socket_with_coroutine_socket()

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
    config = Bunch(ini = path('build.ini')),
    env = path('.').abspath(),
    dbname="loaf",
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
            "jstools",
            "urlgrabber",
            "eventlet",
            "pip"],
        install_paver=True,
        script_name='bootstrap.py',
        paver_command_line='after_bootstrap'
        ),
    )

options.setup.package_data = paver.setuputils.find_package_data(
    'loaf', package='loaf', only_in_packages=False)

bag = type('bag', (object,), {})


@task
def auto(options):
    cp = ConfigParser.ConfigParser()
    cp.read(options.config.ini)
    options.config.parser = cp


def tarball_unpack(fpath, dest, overwrite=False):
    """
    Dumbly unpack tarballs and zips

    fpath --
       filepath of tarball

    dest --
       folder to upack into

    @return
        name of folder created by unpacking
    """
    dest = path(dest)
    filename = fpath.split("/")[-1]
    newfile = dest / filename

    dest_folder = dest / filename.split(".tar.")[0]
    if not dest_folder.exists() and overwrite:
        shutil.copyfile(fpath.abspath(), newfile.abspath())
        with pushd(dest):#necessary?
            mode = "r:gz"
            if filename.endswith("bz2") or filename.endswith("bz"):
                mode = "r:bz2"
            tarball = tarfile.open(filename, mode)
            eventlet.api.sleep(0)        
            tarball.extractall()
        os.remove(newfile)
    return dest_folder


@task
def get_sources(options, key="postgis", ignore=['cbase']):
    config = options.config.parser
    pkgs = config.options(key)
    global pool
    #pool = eventlet.coros.CoroutinePool(max_size=len(pkgs))
    pool = eventlet.coros.CoroutinePool(max_size=len(pkgs))
    for pkg in pkgs:
        if pkg not in ignore:
            pool.execute(grab_unpack, pkg, config, key)
    pool.wait_all()

    # remove below?
    lpath = path("src/LICENSE.txt")
    if lpath.exists():
        lpath.remove()
    call_task('save_cfg')

def grab_unpack(name, config, section, src=path("./src").abspath()):
    url = config.get(section, name)
    cache = path('build')
    filename = url.split("/")[-1]
    dl_path = cache.abspath() / filename
    if not dl_path.exists():
        info("Download %s" %name)
        urlgrab(url, dl_path, progress_obj=text_progress_meter())
    eventlet.api.sleep(0)
    source_path = tarball_unpack(dl_path, src, True)
    eventlet.api.sleep(0)
    config.set("sources", name, source_path.abspath())

@task
@needs(['get_sources'])
def install_postgis(options):
    for pkg in options.config.parser.get('postgis', 'cbase').split():
        basic_install(pkg)
    basic_install("readline")
    basic_install("postgres")
    pg_config = options.env.abspath() / "bin/pg_config"
    geos_config = options.env.abspath() / "bin/geos-config"
    projdir = options.env
    extra_args = "--with-pgconfig=%s --with-geosconfig=%s --with-projdir=%s" %(pg_config, geos_config, projdir)
    basic_install("postgis", extra_args)
    if  get_option(options.config, "installed", "gdal2") is None:
        basic_install("gdal", "--with-pg=%s" %pg_config, force=True)
        options.config.set("installed", "gdal2", True)
        call_task("save_cfg")
    call_task('pg_after_install')

@task
def vardir(options):
    vardir = path(options.env) / 'var'
    if not vardir.exists():
        vardir.mkdir()
    return vardir

@task
@needs('vardir')
def pg_after_install(options):
    # set up postgres user
    try:
        pguserid = pwd.getpwnam('postgres')[2]
    except KeyError:
        pguserid = add_pg_user()
    vardir = path(options.env) / 'var'
    pgdata = vardir / 'pgdata'
    if not pgdata.exists():
        try:
            pgdata.mkdir()
            subprocess.call("sudo chown postgres:postgres %s" %pgdata.abspath(), shell=True)
            subprocess.call("sudo -u postgres bin/initdb -E UNICODE -D %s" %pgdata.abspath(), shell=True)
        except :
            pgdata.rmdir()
            raise
    call_task('setup_cmds')

default_pglog = options.env / path('var') / path('pgdata') / 'pg.log'

@task
def start_pg(options=options, logfile=default_pglog):
    if wait_for_port(5432, 2, exit=False):
        info("posgres is running")
    else:
        cmd = "pg_ctl -D %s -l %s start" \
              %(options.env / path('var') / 'pgdata', default_pglog)
        sh_pg(cmd)
        wait_for_port(5432)


def wait_for_port(port, timeout=20, exit=True):
    state = bag()
    state.connected = False
    def dowait(state=state):
        while True:
            try:
                cxn = eventlet.api.connect_tcp(('localhost', port))
                cxn.close()
                info("Connected: %s" %port)
                state.connected = True
                break
            except KeyboardInterrupt:
                break
            except socket.error:
                info("No connection: %s" %port)
                eventlet.api.sleep(0)
                time.sleep(4)

    try:
        eventlet.api.with_timeout(timeout, dowait)
    except eventlet.api.TimeoutError:
        if exit is True:
            sys.exit(info('Timed out'))

    return state.connected

@task
def stop_pg(options=options, restart=False):
    action = "stop"
    if restart is True:
        action = "restart"
    cmd = "pg_ctl -D %s %s" \
          %(options.env / path('var') / 'pgdata', action)
    sh_pg(cmd)
    if restart is True:
        wait_for_port(5432)

def sh_pg(cmd):
    return subprocess.call("sudo -u postgres %s" %cmd, shell=True)

    
@task
def setup_cmds(options):
    config = options.config.parser
    start_pg()
    try:
        sh_pg('createdb -E UTF8 template_postgis')
        sh_pg('createlang -d template_postgis plpgsql')
        # location specific to 1.4.0
        sh_pg('psql -d template_postgis -f %s' %(path(config.get('sources', 'postgis')) / path('postgis') / 'postgis.sql'))
        sh_pg('psql -d template_postgis -f %s' %(path(config.get('sources', 'postgis')) / 'spatial_ref_sys.sql'))
        sh_pg('psql -d template_postgis -c "GRANT ALL ON geometry_columns TO PUBLIC;"')
        sh_pg('psql -d template_postgis -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"')
        sh_pg('createdb -T template_postgis %s' %options.dbname)
    finally:
        stop_pg()

def get_option(config, section, opt, default=None):
    try:
        return config.get(section, opt)
    except ConfigParser.NoOptionError:
        return default

def basic_install(pkg, extra2="", options=options, clean=False, force=False):
    # use config.status to determine whether to rerun?
    config = options.config.parser
    pred = options.env
    src = path(config.get('sources', pkg))
    extra = get_option(config, 'install_options', pkg, "")
    if force is True:
        config.remove_option('installed', pkg)
    if get_option(config, "installed", pkg) is None:
        with pushd(src) as root:
            sh("./configure LDFLAGS=-L%s CPPFLAGS=-I%s --prefix=%s %s %s" %(str(path(pred) / 'lib'), str(path(pred) / 'include'), pred, extra, extra2))
            if clean:
                sh("make clean")
            sh("make")
            sh("make install")
        config.set('installed', pkg, True)
        call_task("save_cfg")

@task
@needs(['auto'])
def save_cfg(options):
    options.config.parser.write(open(options.config.ini, 'w'))

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

def git_it(name, address):
    src = path('src')
    if not (src / name).exists():
        with pushd(src):
            sh("git clone %s %s" %(address, name))

@task
def go_git_js(options):
    parser = options.config.parser
    for name in parser.options('git'):
        address = parser.get('git', name)
        info("gitting %s @ %s" %(name, address))
        git_it(name, address)


def move_overwrite(source, dest_folder):
    dest = path(dest_folder) / source
    if dest.exists():
        dest.unlink()
    path(source).move(dest_folder)

@task
def build_js_for_ti(options):
    sh("jsbuild -us loaf.js shared/build.cfg")
    move_overwrite('OpenLayers.js', 'Resources')
    move_overwrite('IOL.js', 'Resources')


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
