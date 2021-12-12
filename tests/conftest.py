""""
This is a standard pytest construct to setup commandline parameters
"""
import pytest


def pytest_addoption(parser):
    """This adds the commandline options"""
    parser.addoption("--amurl", action="store")
    parser.addoption("--basic", action="store")
    parser.addoption("--cert", action="store")
    parser.addoption("--proxy", action="store")


@pytest.fixture(scope="session")
def acct_mgt_url(request):
    """This ensures that we have an account management URL (amurl)"""
    amurl_value = request.config.option.amurl
    if amurl_value is None:
        pytest.skip()
    return amurl_value


@pytest.fixture(scope="session")
def basic(request):
    """This is an optional username/password for basic authentication"""
    user_passwd = request.config.option.basic
    return user_passwd


@pytest.fixture(scope="session")
def cert(request):
    """This an optional certificate for use with 2 way TLS - not fully implemented"""
    cert_value = request.config.option.cert
    return cert_value


@pytest.fixture(scope="session")
def proxy(request):
    """This was for a proxy server (bastion proxy) for the 2 way TLS - not fully implemented"""
    url = request.config.option.proxy
    return url


def pytest_generate_tests(metafunc):
    """This is called for every test, passing commandline arguments into the test"""
    # if the argument is specified in the list of test "fixturenames".
    option_value = metafunc.config.option.amurl
    if "amurl" in metafunc.fixturenames and option_value is not None:
        metafunc.parametrize("acct_mgt_url", [option_value])
    auth_str = metafunc.config.option.basic
    # metafunc.parametrize("basic_auth", [option_value])

    proxy_url = metafunc.config.option.proxy
    #   -- gets translated to:
    # metafunc.parametrize("cert", [option_value])
    #   --> get translated to the following:
    #   auth_ops = ["-E","./client_cert/acct-mgt-2.crt", "-key", "./client_cert/acct-mgt-2.key"]
    #   auth_ops = ["-cert", r"acct-mgt-2",]    metafunc.parametrize("auth_opts", [[]])
    auth_list = []
    if auth_str is not None:
        auth_list.extend(["-u", auth_str])
    if proxy_url is not None:
        auth_list.extend(["--proxy", proxy_url])
    metafunc.parametrize("auth_opts", [auth_list])
    # if auth_str is not None:
    #    metafunc.parametrize("auth_opts", [["-u", auth_str]])
    # else:
    #    metafunc.parametrize("auth_opts", [[]])