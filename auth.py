from requests.auth import AuthBase


# def _oauth2_auth_str(token):
#     return 'Bearer %s' % token


class HTTPOAuth2Auth(AuthBase):
    """Attaches HTTP OAuth2 Authentication to a given Request object."""

    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = 'Bearer %s' % self.token
        return r
