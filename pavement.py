from paver.easy import *
try: from paver.virtual import bootstrap
except ImportError: pass

options(
    minilib=Bunch(extra_files=['virtual', 'doctools', 'misctasks']),
##    sphinx=Bunch(
##       docroot='docs',
##       builddir="_build",
##       sourcedir=""
##       ),
    virtualenv=Bunch(
      packages_to_install=['pip'],
      dest_dir='./',
      install_paver=True,
      script_name='bootstrap.py',
      paver_command_line='post_bootstrap'
      ),
##     deploy=Bunch(
##       pavement=path('shared/deployment_pavement.py'),
##       req_file=path('shared/deploy-libs.txt'),
##       packages_to_install=['pip'],
##       dest_dir='./',
##       out_dir=build_dir,
##       install_paver=True,
##       script_name=build_dir / 'bootstrap.py',
##       paver_command_line='post_bootstrap'      
##     )
)

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

