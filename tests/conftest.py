""""
This is a standard pytest construct to setup commandline parameters
"""
import os
import pytest
import requests


def pytest_addoption(parser):
    """This adds the commandline options"""
    parser.addoption("--amurl", action="store")
    parser.addoption("--basic", action="store")


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


def pytest_generate_tests(metafunc):
    """This is called for every test, passing commandline arguments into the test"""
    option_value = metafunc.config.option.amurl
    if "amurl" in metafunc.fixturenames and option_value is not None:
        metafunc.parametrize("acct_mgt_url", [option_value])
    auth_str = metafunc.config.option.basic
    acct_mgt_user_file = os.environ.get("ACCT_MGT_USER_FILE")
    acct_mgt_username = os.environ.get("ACCT_MGT_USERNAME")
    acct_mgt_password = os.environ.get("ACCT_MGT_PASSWORD")
    session = requests.Session()
    session.verify = False
    if auth_str:
        cred = auth_str.split(":")
        session.auth = (cred[0], cred[1])
    elif acct_mgt_user_file:
        cred_str = ""
        with open(acct_mgt_user_file, "r", encoding="utf-8") as file:
            cred_str = file.read()
        cred = cred_str.split(" ")
        print(f"cred: {cred[0]}, {cred[1]}")
        session.auth = (cred[0], cred[1])
    elif acct_mgt_username and acct_mgt_password:
        if acct_mgt_username and acct_mgt_password:
            session.auth = (acct_mgt_username, acct_mgt_password)
    metafunc.parametrize("session", [session])
