from FeatureServer.DataSource.GeoAlchemy import GeoAlchemy
from FeatureServer.Server import Server
from ogreport import app, model


class FeatureServerMiddleware(object):
    """
    Feature server on the inside

    Keeping it simple for right now, but init could load up multiple layers
    """
    def __init__(self, app, dsn):
        self.app = app
        # layer specific data
        params = dict(model = model.__name__,
                      cls = model.Spot.__name__,
                      fid = 'id',
                      geom = 'geom',
                      dburi=dsn)
        self.params = params
        self.datasource = GeoAlchemy('spots', **params)
        self.server = Server({'/spots', self.datasource})

    def __call__(environ, start_response):
        environ['ogreport.featureserver'] = self.featureserver
        return self.app(environ, start_response)

