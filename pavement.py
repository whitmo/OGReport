"""
Paver for setting up basic geo web stack
"""
from paver.easy import *
try:
    import eventlet.util
    eventlet.util.wrap_socket_with_coroutine_socket()
except ImportError:
    info("Socket not overridden")

from functools import wraps, update_wrapper
from paver.setuputils import setup
from paver.tasks import Task
from setuptools import find_packages
import ConfigParser
import contextlib
import functools
import getpass
import pwd
import shutil
import socket
import sys
import tarfile
import time

close = contextlib.closing

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
    config = Bunch(ini = path('build.ini'),
                   state_ini = path('build_state.ini')),
    env = path('.').abspath(),
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
        packages_to_install=["pip"],
        install_paver=True,
        script_name='bootstrap.py',
        paver_command_line='after_bootstrap'
        ),
    )

options.setup.package_data = paver.setuputils.find_package_data(
    'loaf', package='loaf', only_in_packages=False)

bag = type('bag', (object,), {})

default_pglog = options.env / path('var') / path('pgdata') / 'pg.log' # put in options

@task
def auto(options):
    """
    Sets up two configparsers: one for recording the state of the
    build, one for reading data about what to build.

    Adds the convenience functions 'options.conf_get' and
    'options.conf_set' to safely read and write from both files while
    ensuring the build.ini is never written
    """
    cp = ConfigParser.ConfigParser()
    state = ConfigParser.ConfigParser()
    
    cp.read(options.config.ini)
    state.read(options.config.state_ini)

    options.config.state = state
    options.config.build = cp

    options.config.parser = cp
    for opt, val in cp.items('general'):
        setattr(options, opt, val)
    options.save_conf = False

    def conf_get(*args, **kw):
        getter = kw.pop('type', 'get')
        section = args[0]
        try:
            for parser in cp, state,:
                if parser.has_section(section):
                    return getattr(parser, getter)(*args, **kw)
        except ConfigParser.NoOptionError:
            default = kw.get('default', None)
            if default is not None:
                return default

    @functools.wraps(cp.set)
    def conf_set(*args, **kw):
        options.save_conf = True
        return state.set(*args, **kw)

    def opt_func(func):
        functools.wraps(func)
        def closure():
            return func
        return closure
    
    options.conf_get = opt_func(conf_get)
    for t in 'getboolean', 'getint', 'getfloat',:
        setattr(options,
                "conf_%s" %t,
                opt_func(functools.partial(conf_get, type=t)))

    options.conf_set = opt_func(conf_set)
    options.app_path = options.env / path('src') / path(options.webapp_pkg)


def save_config(func):
    """
    Decorator for functions that create changes that need to be
    persisted to build_state.ini.
    """
    @functools.wraps(func)
    def wrapper(options, *args, **kw):
        ret = func(options, *args, **kw)
        if options.save_conf is True:
            call_task('save_cfg')
        return ret
    return wrapper

def pm(func):
    """
    Debugging decorator.  Use like so to do postmortem debugging::

    @pm
    def troublesome():
        raise HellException
    
    """
    @functools.wraps(func)
    def wrap(*args, **kw):
        try:
            return func(*args, **kw)
        except Exception, e:
            import pdb, sys; pdb.post_mortem(sys.exc_info()[2])
    return wrap
            


def tarball_unpack(fpath, dest, overwrite=False):
    """
    Dumbly unpack tarballs and unzips. Plays nice with 'get_sources'.

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
        shutil.copyfile(str(fpath.abspath()), str(newfile.abspath()))
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
@save_config
@needs('make_src')
def get_sources(options, key="postgis", ignore=['cbase']):
    """
    Uses 'grab_unpack' to download source files concurrently.
    """
    pkgs = options.build.options(key)
    global pool
    pool = eventlet.coros.CoroutinePool(max_size=len(pkgs))
    for pkg in pkgs:
        if pkg not in ignore:
            pool.execute(grab_unpack, pkg, options, key)
    pool.wait_all()

    # remove below?
    lpath = path("src/LICENSE.txt")
    if lpath.exists():
        lpath.remove()


def grab_unpack(name, options, section, src=path("./src").abspath()):
    """
    Concurrency friendly download and unpacker.
    """
    url = options.conf_get(section, name)
    cache = path('build')
    filename = url.split("/")[-1]
    dl_path = cache.abspath() / filename
    if not dl_path.exists():
        info("Download %s" %name)
        urlgrab(url, dl_path, progress_obj=text_progress_meter())
    eventlet.api.sleep(0)
    source_path = tarball_unpack(dl_path, src, True)
    eventlet.api.sleep(0)
    options.conf_set("sources", name, source_path.abspath())


@task
@save_config
@needs(['get_sources'])
def install_postgis(options):
    """
    Installs postgis per definition in build.ini:[postgis].
    
    [postgis]cbase are installed first, then postgres and postgis,
    then gdal again w/ postgres bindings
    """
    for pkg in options.conf_get('postgis', 'cbase').split():
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
        options.conf_set("installed", "gdal2", True)
    call_task('pg_after_install')


def mkdir(dirname):
    """
    Task maker for creating tasks to safely creating directories

    mkdir(path_to_dir_that_needs_to_exist)
    
    """
    def dirmaker(options):
        if not isinstance(dirname, path):
            tdir = path(options.env) / dirname
        if not tdir.exists():
            tdir.mkdir()
    dirmaker.__name__ = "make_%s" %dirname
    return Task(dirmaker)

make_var = mkdir('var')
make_src = mkdir('src')


@task
@needs('make_var')
def pg_after_install(options):
    """
    Sets up a basic postgres data dir and checks for a postgres user.
    """
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

def add_pg_user():
    info("ATTENTION: You must add your own postgres user manually")
    sys.exit()

@task
def start_pg(options=options, logfile=default_pglog, wait=True):
    """
    Starts postgres

    logfile: logfile you wish pg to use
    wait:    wait until postgres is accepting connections to exit
    """
    if wait_for_port(5432, 2, exit=False):
        info("posgres is running")
    else:
        cmd = "pg_ctl -D %s -l %s start" \
              %(options.env / path('var') / 'pgdata', default_pglog)
        sh_pg(cmd)
        if wait is True:
            wait_for_port(5432)


def wait_for_port(port, timeout=20, exit=True):
    """
    Attempts to connect to 'port' until timeout is up
    """
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
def stop_pg(options=options, restart=False, mode='fast'):
    """
    Stops postgres according to 'mode'.  If 'restart' is set to true,
    'restarts'
    """
    action = "stop"
    if restart is True:
        action = "restart"
    cmd = "pg_ctl %s -D %s %s" \
          %("-m " + mode, options.env / path('var') / 'pgdata', action)
    sh_pg(cmd)
    if restart is True:
        wait_for_port(5432)

def sh_pg(cmd):
    """
    Executes a subproccess call as the user 'postgres'
    """
    return subprocess.call("sudo -u postgres %s" %cmd, shell=True)

def get_dbs_and_users(pg=None):
    """
    Uses sqlalchemy engine 'pg' to introspect database and return list
    of databases and users
    """
    call_task('install_psyco_pg')
    if pg is None:
        pg = sqla.create_engine('postgres://postgres@0.0.0.0:5432')
    with close(pg.connect()):
        res = pg.execute(sql.text('select usename from pg_user'))
        with close(res):
            users = [x[0] for x in res]
        res = pg.execute(sql.text('select * from pg_database'))
        with close(res) as dres:
            dbs = dict([x[:2] for x in dres])
    return dbs, users,


@task
def install_psyco_pg(options):
    """
    installs pyscopg2 postgres bindings via pip
    """
    try:
        import psycopg2
    except ImportError:
        sh("pip install psycopg2")
        import psycopg2

        
@task
@needs('webapp_ez', 'start_pg')
def setup_cmds(options):
    """
    Sets up all needed sql and ddl bits for postgis
    """
    user = options.conf_get('pg', 'user')
    password = options.conf_get('pg', 'password')
    loafdb = options.conf_get('pg', 'dbname')

    dbs, users = get_dbs_and_users()
    if not dbs.has_key("template_postgis"):
        info('creating template_postgis and postgis language')
        sh_pg('createdb -E UTF8 template_postgis')
        sh_pg('createlang -d template_postgis plpgsql')

    tp = sqla.create_engine('postgres://postgres@0.0.0.0:5432/template_postgis')
    meta = sqla.MetaData()
    with close(tp.connect()):
        meta.reflect(tp)
    names = set([x.name for x in meta.sorted_tables])
    check = set([u'geometry_columns', u'spatial_ref_sys'])

    if names & check != check:
        info("Adding spatial_ref_sys.sql and postgis.sql")
        sh_pg('psql -d template_postgis -f %s' %(path(options.conf_get('sources', 'postgis')) / path('postgis') / 'postgis.sql'))
        sh_pg('psql -d template_postgis -f %s' %(path(options.conf_get('sources', 'postgis')) / 'spatial_ref_sys.sql'))
        sh_pg('psql -d template_postgis -c "GRANT ALL ON geometry_columns TO PUBLIC;"')
        sh_pg('psql -d template_postgis -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"')

    if not user in users:
        info('Adding user %s' %user)
        cmd = "CREATE USER %s WITH PASSWORD '%s'" %(user, password)
        sh_pg('psql -d template_postgis -c "%s"' %cmd)
        sh_pg('psql -d template1 -c "%s"' %cmd)


@task
@needs('setup_cmds')
def create_db(options):
    """
    Creates database for application
    """
    loafdb = options.conf_get('pg', 'dbname')
    dbs, users = get_dbs_and_users()
    if not dbs.has_key(loafdb):
        stop_pg(mode='immediate') # disconnect any users
        start_pg()
        cmd = 'createdb -T template_postgis %s' %loafdb
        info(cmd)
        sh_pg(cmd)
    else:
        info("%s exists" %loafdb)
                   

def get_option(config, section, opt, default=None):
    try:
        return config.get(section, opt)
    except ConfigParser.NoOptionError:
        return default


def basic_install(pkg, extra2="", options=options, clean=False, force=False):
    """
    Does a basic configure; make; make install with local environment
    as prefix (and referencing local environment for include and lib
    directories)
    """
    # use config.status to determine whether to rerun?
    pred = options.env
    src = path(options.conf_get('sources', pkg))
    extra = options.conf_get('install_options', pkg, default="")
    if force is True:
        config.remove_option('installed', pkg)
    if options.config.conf_get( "installed", pkg, default=None) is None:
        with pushd(src) as root:
            sh("./configure LDFLAGS=-L%s CPPFLAGS=-I%s --prefix=%s %s %s" %(str(path(pred) / 'lib'), str(path(pred) / 'include'), pred, extra, extra2))
            if clean:
                sh("make clean")
            sh("make")
            sh("make install")
        options.conf_set('installed', pkg, True)
        call_task("save_cfg")

@task
@needs(['auto'])
def save_cfg(options):
    options.config.state.write(open(options.config.state_ini, 'w'))

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
    """
    Grab javascript off of github
    """
    for name in options.build.options('git'):
        address = options.conf_get('git', name)
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


@task
def webapp_ez(options):
    """
    TG has a few deps that do not pip install!? but will install via
    easy_install
    """
    with open('ez.txt', 'r') as ez:
        for line in ez:
            sh("easy_install %s" %line)


def test_import(pkg):
    try:
        __import__(pkg)
        return True
    except ImportError:
        return False


@task
@save_config
@needs("create_db", "webapp_ez")
def setup_webapp(options):
    """
    Installs necessary dependencies for web application and runs
    webapp setup
    """
    if not test_import('tgext.geo'):
        sh("pip install -r tgext.geo.txt")
        
    try:
        import loafapp
    except ImportError:
        sh("pip install -r tg.txt")
        sh("pip install -e git+%s#egg=%s" %(options.webapp_url, options.webapp_pkg))
        
    if options.conf_getboolean('installed','app_setup'):
        info("Skipping TG setup")
    else:
        with pushd(options.env / path('src') / path(options.webapp_pkg)):
            sh("paster setup-app development.ini")
        options.conf_set('installed','app_setup', str(True))


def get_app_dbstr(options=options):
    cp = ConfigParser.ConfigParser()
    cp.read([options.app_path / options.webapp_dev_ini])
    return cp.get("app:main", "sqlalchemy.url")


@task
@save_config
@needs('start_pg')
def drop_webapp_tables(options):
    """
    Convenience task for dropping tables for webapp
    """
    pkg = options.webapp_pkg.lower()
    model = __import__('%s.model' %pkg, fromlist=[pkg])
    eng = sqla.create_engine(get_app_dbstr())
    with close(eng.connect()) as cxn:
        model.metadata.bind = cxn
        model.metadata.drop_all()
        info("Dropped Tables")
    options.conf_set('installed', 'app_setup', str(False))


@task
@save_config
@needs('start_pg')
@needs('setup_webapp')
def add_test_data(options):
    """
    Load a few test points.

    @@This ought to have a 'from file' flag and data/config driven.
    """
    from loafapp.model import DBSession, Spot
    from geoalchemy import WKTSpatialElement
    from loafapp.config.environment import load_environment
    import transaction
    eng = sqla.create_engine(get_app_dbstr())
    DBSession.configure(bind=eng)
    wkt = "POINT(-80.3 38.2, -81.03 38.04)"
    spot1 = Spot(name="My Bike Route", width=6, geom=WKTSpatialElement(wkt))
    wkt = "POINT(-79.8 38.5, -80.03 38.2)"
    spot2 = Spot(name="George Ave", width=8, geom=WKTSpatialElement(wkt))
    DBSession.add_all([spot1, spot2])
    DBSession.flush()
    transaction.commit()

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


try:
    import eventlet.api
    import eventlet.coros
    import eventlet.processes as proc
    import sqlalchemy as sqla
    from sqlalchemy import sql
    from urlgrabber.grabber import urlgrab, URLGrabError
    from urlgrabber.progress import text_progress_meter
except ImportError:
    info("Some libraries needed by the build not loaded")

