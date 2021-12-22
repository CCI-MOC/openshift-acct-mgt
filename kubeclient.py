"""Create a requests.Session object for communicating with OpenShift"""

import os
import requests

INCLUSTER_TOKEN_PATH = "/run/secrets/kubernetes.io/serviceaccount/token"
INCLUSTER_CA_PATH = "/run/secrets/kubernetes.io/serviceaccount/ca.crt"
INCLUSTER_KUBERNETES_URL = "https://kubernetes.default.svc"


class Client(requests.Session):
    """Create an OpenShift client using a Bearer token"""

    def __init__(self, baseurl=None, token=None, verify=None):
        super().__init__()
        self.baseurl = baseurl if baseurl else self.get_url()
        self.verify = verify if verify is not None else self.get_ca_path()
        self.token = token if token else self.get_token()
        self.headers["Authorization"] = f"Bearer {self.token}"

    @staticmethod
    def get_url():
        url = INCLUSTER_KUBERNETES_URL
        return url

    @staticmethod
    def get_token():
        """Return an authorization token"""
        with open(INCLUSTER_TOKEN_PATH) as file:
            token = file.read()

        return token

    @staticmethod
    def get_ca_path():
        """Return path to a CA certificate file"""
        ca_path = None

        if os.path.exists(INCLUSTER_CA_PATH):
            ca_path = INCLUSTER_CA_PATH

        return ca_path

    # pylint: disable=arguments-differ
    def request(self, method, url, **kwargs):
        """Wrapper for request method that prepends base url if necessary"""
        if not url.startswith("http"):
            if not url.startswith("/"):
                url = f"/{url}"
            url = f"{self.baseurl}{url}"

        return super().request(method, url, **kwargs)
