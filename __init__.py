import sys
import json
import requests
import logging

from .auth import HTTPOAuth2Auth


logger = logging.getLogger('mytarget')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stderr))


class Error(Exception):
    pass


class AuthError(Error):
    pass


class ValidationError(Error):
    pass


class MyTargetClient(object):

    PRODUCTION_HOST = 'target.my.com'
    SANDBOX_HOST = 'target-sandbox.my.com'

    def __init__(self, client_id, client_secret, is_sandbox=True, debug=False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.is_sandbox = is_sandbox

        self.host = self.SANDBOX_HOST if self.is_sandbox else self.PRODUCTION_HOST
        self.root_url = 'https://{host}/api'.format(host=self.host)

        if debug:
            self.level = logging.INFO
        else:
            self.level = logging.DEBUG

        self.session = requests.Session()

        self.oauth2 = OAuth2(self)
        self.user = User(self)
        self.clients = Clients(self)
        self.campaigns = Campaigns(self)
        self.banners = Banners(self)
        self.statistics = Statistics(self)
        self.faststat = Faststat(self)

    def auth(self, token):
        self.session.auth = HTTPOAuth2Auth(token)

    def call(self, method, resource, **kwargs):
        url = self.root_url + resource

        self.log('Request to %s: %s' % (url, json.dumps(kwargs)))

        response = self.session.request(method, url, **kwargs)

        self.log('Received %s: %s' % (response.status_code, response.text))

        if response.status_code != requests.codes.ok:
            raise self.cast_error(response)

        return response.json()

    def get(self, resource, params=None):
        return self.call('GET', resource, params=params)

    def post(self, resource, **kwargs):
        return self.call('POST', resource, **kwargs)

    def log(self, *args, **kwargs):
        '''Proxy access to the targetmail logger, changing the level based on the debug setting'''
        logger.log(self.level, *args, **kwargs)

    def cast_error(self, response):
        body = response.json()
        if response.status_code == 400:
            return ValidationError(body)
        if response.status_code == 401:
            return AuthError(body)
        return Error(body)


class OAuth2(object):

    def __init__(self, master):
        self.master = master

    def _obtain_token(self, grant_type, **kwargs):
        data = {
            "grant_type": grant_type,
            "client_id": self.master.client_id,
            "client_secret": self.master.client_secret,
        }
        if kwargs:
            data.update(kwargs)

        return self.master.post('/v2/oauth2/token.json', data=data)

    def obtain_agency_token(self):
        return self._obtain_token('client_credentials')

    def obtain_client_token(self, client_name):
        return self._obtain_token('agency_client_credentials', agency_client_name=client_name)

    def refresh_token(self, refresh_token):
        return self._obtain_token('refresh_token', refresh_token=refresh_token)


class User(object):

    def __init__(self, master):
        self.master = master

    def get(self):
        return self.master.get('/v1/user.json')

    def update(self):
        raise NotImplementedError()


class Clients(object):

    def __init__(self, master):
        self.master = master

    def list(self):
        return self.master.get('/v1/clients.json')

    def add(self):
        raise NotImplementedError()


class Campaigns(object):

    def __init__(self, master):
        self.master = master

    def list(self, ids=None, status=None, fields=None, with_banners=False):
        tpl = '/v1/campaigns{ids}.json'
        macros = {'ids': ''}

        if ids:
            if type(ids) is not list:
                ids = [ids]
            ids_str = '/' + ';'.join([str(id_) for id_ in ids])
            macros.update({'ids': ids_str})

        _params = {}
        if status:
            _params['status'] = status
        if fields:
            if type(fields) is not list:
                fields = [fields]
            _params['fields'] = ','.join(fields)
        if with_banners:
            _params['with_banners'] = 1

        resource = tpl.format(**macros)
        return self.master.get(resource, _params)


class Banners(object):

    def __init__(self, master):
        self.master = master

    def list(self, ids=None, status=None, campaign_status=None, fields=None, updated__gte=None,
             last_stats_updated__gte=None):
        tpl = '/v1/banners{ids}.json'
        macros = dict()
        macros.setdefault('ids', '')

        if ids:
            if type(ids) is not list:
                ids = [ids]
            ids_str = '/' + ';'.join([str(id_) for id_ in ids])
            macros['ids'] = ids_str

        _params = {}
        if status:
            _params['status'] = status
        if campaign_status:
            _params['campaign__status'] = campaign_status
        if fields:
            if type(fields) is not list:
                fields = [fields]
            _params['fields'] = ','.join(fields)
        if updated__gte:
            _params['updated__gte'] = updated__gte
        if last_stats_updated__gte:
            _params['last_stats_updated__gte'] = last_stats_updated__gte

        resource = tpl.format(**macros)
        return self.master.get(resource, _params)

    def update(self, ids, **params):
        tpl = '/v1/banners/{ids}.json'
        macros = dict()
        macros.setdefault('ids', '')

        if type(ids) is not list:
            ids = [ids]
        ids_str = ';'.join([str(id_) for id_ in ids])
        macros['ids'] = ids_str

        resource = tpl.format(**macros)
        return self.master.post(resource, json=params)


class Statistics(object):

    def __init__(self, master):
        self.master = master

    def get(self, object_type, object_id, stat_type, date_from=None, date_to=None):
        tpl = '/v1/statistics/{object_type}/{object_id}/{stat_type}{dates}.json'

        macros = dict()
        macros['object_type'] = object_type
        macros['stat_type'] = stat_type
        macros['dates'] = ''

        if type(object_id) is not list:
            object_id = [object_id]
        object_id_str = ';'.join([str(id_) for id_ in object_id])
        macros['object_id'] = object_id_str

        if date_from:
            macros['dates'] = '/{date_from}-{date_to}'.format(date_from=date_from, date_to=date_to)

        resource = tpl.format(**macros)
        return self.master.get(resource)

    def campaigns(self, object_id, stat_type, date_from=None, date_to=None):
        return self.get('campaigns', object_id, stat_type, date_from, date_to)

    def banners(self, object_id, stat_type, date_from=None, date_to=None):
        return self.get('banners', object_id, stat_type, date_from, date_to)


class Faststat(object):

    def __init__(self, master):
        self.master = master

    def get(self, object_type, object_id):
        tpl = '/v1/statistics/faststat/{object_type}/{object_id}.json'

        macros = dict()
        macros['object_type'] = object_type

        if type(object_id) is not list:
            object_id = [object_id]
        object_id_str = ';'.join([str(id_) for id_ in object_id])
        macros['object_id'] = object_id_str

        resource = tpl.format(**macros)
        return self.master.get(resource)

    def campaigns(self, ids):
        return self.get('campaigns', ids)

    def banners(self, ids):
        return self.get('banners', ids)

    def users(self, ids):
        return self.get('users', ids)
