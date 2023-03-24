# pylint: disable=missing-module-docstring
import os
from unittest import mock

import kubernetes.config.config_exception as kexc

from acct_mgt import app


def test_env_config():
    os.environ[f"{app.ENVPREFIX}TESTVAR"] = "testvalue"
    res = app.env_config()
    assert res["TESTVAR"] == "testvalue"


@mock.patch("acct_mgt.app.DynamicClient")
@mock.patch("acct_mgt.app.kubernetes.config.new_client_from_config")
@mock.patch("acct_mgt.app.kubernetes.client", mock.Mock())
def test_get_dynamic_client_kubeconfig(fake_kube_config, fake_ocp_client):
    fake_kube_config.return_value = "FAKE CLIENT"
    app.get_dynamic_client(mock.Mock())
    fake_ocp_client.assert_called_with("FAKE CLIENT")


@mock.patch("acct_mgt.app.DynamicClient")
@mock.patch("acct_mgt.app.kubernetes.config.load_incluster_config")
@mock.patch("acct_mgt.app.kubernetes.config.new_client_from_config")
@mock.patch("acct_mgt.app.kubernetes.client")
def test_get_dynamic_client_incluster(
    fake_kube_client, fake_new_client, fake_load_incluster, fake_ocp_client
):
    fake_new_client.side_effect = kexc.ConfigException()
    fake_kube_client.ApiClient.return_value = "FAKE CLIENT"

    app.get_dynamic_client(mock.Mock())

    fake_load_incluster.assert_called()
    fake_ocp_client.assert_called_with("FAKE CLIENT")
