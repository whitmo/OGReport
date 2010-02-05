from gp.fileupload import Storage
from paste.config import ConfigMiddleware, CONFIG as config
from sqlalchemy import engine_from_config
from repoze import tm
from webob import Response
from ogreport import model
from ogreport.featureserver import FeatureServerMiddleware
import os
import tempfile
import wee

from paste.config import DispatchingConfig

config = DispatchingConfig()

@wee.get(r'^/?')
def index(request):
    return Response("OG!")


@wee.post(r'^/?')
def mobile_upload(request):
    import pdb;pdb.set_trace()

@wee.REST(r'^/spots')
class FeatureServer(object):

    def get(self, request):
        pass
    
    def getitem(self, request, uid):
        pass

    def put(self, request, uid):
        pass

    def put(self, request, uid):
        pass

    def delete(self, request, uid):
        pass

    def post(self, request):
        pass

def make_app(global_conf, **app_conf):
    global config
    global_conf.update(app_conf)
    conf = global_conf
    pm = conf.pop('postmortem', 'false')
    max_size = conf.get('upload_max_size', 150000)
    udd = conf.get('upload_dest_dir', None)

    conf['ogreport.engine'] = engine_from_config(conf)
    app = wee.make_app()
    app = FeatureServerMiddleware(app, conf['sqlalchemy.url'])
    app = ConfigMiddleware(app, conf, dispatching_config=config, environ_key="ogreport.config")
    app = tm.TM(app)
    
    if udd is not None:
        #hexd = hashlib.sha1(str(datetime.datetime.now())).hexdigest()
        tmpdir =  os.path.join(tempfile.gettempdir(), 'ogreporter')
        app = Storage(app, upload_to=udd, tempdir=tmpdir, max_size=max_size)

    if pm != 'false':
        from repoze.debug.pdbpm import PostMortemDebug
        app = PostMortemDebug(app)    

    app.conf = conf.copy()
    return app
