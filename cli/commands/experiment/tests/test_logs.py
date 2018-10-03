#
# INTEL CONFIDENTIAL
# Copyright (c) 2018 Intel Corporation
#
# The source code contained or described herein and all documents related to
# the source code ("Material") are owned by Intel Corporation or its suppliers
# or licensors. Title to the Material remains with Intel Corporation or its
# suppliers and licensors. The Material contains trade secrets and proprietary
# and confidential information of Intel or its suppliers and licensors. The
# Material is protected by worldwide copyright and trade secret laws and treaty
# provisions. No part of the Material may be used, copied, reproduced, modified,
# published, uploaded, posted, transmitted, distributed, or disclosed in any way
# without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be express
# and approved by Intel in writing.
#

from click.testing import CliRunner
from unittest.mock import patch, mock_open
import pytest

from commands.experiment import logs
from logs_aggregator.k8s_log_entry import LogEntry
from util.exceptions import K8sProxyOpenError, K8sProxyCloseError
from platform_resources.run_model import Run
from cli_text_consts import ExperimentLogsCmdTexts as Texts

TEST_LOG_ENTRIES = [LogEntry(date='2018-04-17T09:28:39+00:00',
                             content='Warning: Unable to load '
                                     '/usr/share/zoneinfo/right/Factory as time zone. Skipping it.\n',
                             pod_name='understood-gnat-mysql-868b556f8f-lwdr9',
                             namespace='default'),
                    LogEntry(date='2018-04-17T09:28:49+00:00',
                             content='MySQL init process done. Ready for start up.\n',
                             pod_name='understood-gnat-mysql-868b556f8f-lwdr9',
                             namespace='default')]


def test_show_logs_success(mocker):
    es_client_mock = mocker.patch('commands.experiment.logs.K8sElasticSearchClient')
    es_client_instance = es_client_mock.return_value
    es_client_instance.get_experiment_logs_generator.return_value = TEST_LOG_ENTRIES

    proxy_mock = mocker.patch.object(logs, 'K8sProxy')

    get_current_namespace_mock = mocker.patch('commands.experiment.logs.get_kubectl_current_context_namespace')
    fake_experiment_name = 'fake-experiment'
    list_runs_mock = mocker.patch('commands.experiment.logs.list_runs')
    list_runs_mock.return_value = [Run(name=fake_experiment_name, experiment_name=fake_experiment_name)]

    runner = CliRunner()
    runner.invoke(logs.logs, [fake_experiment_name])

    assert proxy_mock.call_count == 1, 'port forwarding was not initiated'
    assert get_current_namespace_mock.call_count == 1, 'namespace was not retrieved'
    assert list_runs_mock.call_count == 1, 'run was not retrieved'
    assert es_client_instance.get_experiment_logs_generator.call_count == 1, 'Experiment logs were not retrieved'


def test_show_logs_failure(mocker):
    es_client_mock = mocker.patch('commands.experiment.logs.K8sElasticSearchClient')
    es_client_instance = es_client_mock.return_value
    es_client_instance.get_experiment_logs_generator.side_effect = RuntimeError

    proxy_mock = mocker.patch.object(logs, 'K8sProxy')

    get_current_namespace_mock = mocker.patch('commands.experiment.logs.get_kubectl_current_context_namespace')
    fake_experiment_name = 'fake-experiment'
    list_runs_mock = mocker.patch('commands.experiment.logs.list_runs')
    list_runs_mock.return_value = [Run(name=fake_experiment_name, experiment_name=fake_experiment_name)]

    runner = CliRunner()

    result = runner.invoke(logs.logs, [fake_experiment_name])

    assert proxy_mock.call_count == 1, 'port forwarding was not initiated'
    assert get_current_namespace_mock.call_count == 1, 'namespace was not retrieved'
    assert list_runs_mock.call_count == 1, 'run was not retrieved'
    assert es_client_instance.get_experiment_logs_generator.call_count == 1, 'Experiment logs retrieval was not called'
    assert result.exit_code == 1


@pytest.mark.parametrize("exception", [K8sProxyCloseError(), K8sProxyOpenError()])
def test_show_logs_failure_proxy_problem(mocker, exception):
    es_client_mock = mocker.patch('commands.experiment.logs.K8sElasticSearchClient')
    es_client_instance = es_client_mock.return_value
    es_client_instance.get_experiment_logs_generator.side_effect = RuntimeError

    proxy_mock = mocker.patch.object(logs, 'K8sProxy')
    proxy_mock.side_effect = exception
    get_current_namespace_mock = mocker.patch('commands.experiment.logs.get_kubectl_current_context_namespace')
    fake_experiment_name = 'fake-experiment'
    list_runs_mock = mocker.patch('commands.experiment.logs.list_runs')
    list_runs_mock.return_value = [Run(name=fake_experiment_name, experiment_name=fake_experiment_name)]

    runner = CliRunner()

    result = runner.invoke(logs.logs, [fake_experiment_name])

    assert proxy_mock.call_count == 1, 'port forwarding was not initiated'
    assert get_current_namespace_mock.call_count == 0, 'namespace was retrieved'
    assert list_runs_mock.call_count == 0, 'run was retrieved'
    assert es_client_instance.get_experiment_logs_generator.call_count == 0, 'Experiment logs retrieval was called'
    assert result.exit_code == 1


def test_show_logs_too_many_params(mocker):
    runner = CliRunner()

    result = runner.invoke(logs.logs, ['fake_experiment', '-m', 'match_name'])

    assert Texts.NAME_M_BOTH_GIVEN_ERROR_MSG in result.output


def test_show_logs_lack_of_params(mocker):
    runner = CliRunner()

    result = runner.invoke(logs.logs)

    assert Texts.NAME_M_NONE_GIVEN_ERROR_MSG in result.output


def test_show_logs_from_two_experiments(mocker):
    es_client_mock = mocker.patch('commands.experiment.logs.K8sElasticSearchClient')
    es_client_instance = es_client_mock.return_value
    es_client_instance.get_experiment_logs_generator.return_value = TEST_LOG_ENTRIES

    proxy_mock = mocker.patch.object(logs, 'K8sProxy')

    get_current_namespace_mock = mocker.patch("commands.experiment.logs.get_kubectl_current_context_namespace")

    fake_experiment_name = 'fake-experiment'
    list_runs_mock = mocker.patch('commands.experiment.logs.list_runs')
    list_runs_mock.return_value = [Run(name=fake_experiment_name, experiment_name=fake_experiment_name)]

    runner = CliRunner()
    m = mock_open()
    with patch("builtins.open", m) as open_mock:
        exception = RuntimeError()
        exception.message = "Cause of an error"
        open_mock.return_value.__enter__.side_effect = exception
        result = runner.invoke(logs.logs, ['fake-experiment', '-o'], input='y')

    assert Texts.LOGS_STORING_ERROR.format(exception_message=exception.message) in result.output
    assert proxy_mock.call_count == 1, "port forwarding was not initiated"
    assert get_current_namespace_mock.call_count == 1, "namespace was not retrieved"
    assert list_runs_mock.call_count == 1, "run was not retrieved"
    assert es_client_instance.get_experiment_logs_generator.call_count == 1, "Experiment logs were not retrieved"


def test_show_logs_to_file_success(mocker):
    es_client_mock = mocker.patch("commands.experiment.logs.K8sElasticSearchClient")
    es_client_instance = es_client_mock.return_value
    es_client_instance.get_experiment_logs_generator.return_value = TEST_LOG_ENTRIES

    proxy_mock = mocker.patch.object(logs, 'K8sProxy')

    get_current_namespace_mock = mocker.patch("commands.experiment.logs.get_kubectl_current_context_namespace")
    fake_experiment_name = 'fake-experiment'
    list_runs_mock = mocker.patch('commands.experiment.logs.list_runs')
    list_runs_mock.return_value = [Run(name=fake_experiment_name, experiment_name=fake_experiment_name)]

    runner = CliRunner()
    m = mock_open()
    with patch("builtins.open", m) as open_mock:
        runner.invoke(logs.logs, ['fake-experiment', '-o'], input='y')

    assert proxy_mock.call_count == 1, "port forwarding was not initiated"
    assert get_current_namespace_mock.call_count == 1, "namespace was not retrieved"
    assert list_runs_mock.call_count == 1, "run was not retrieved"
    assert es_client_instance.get_experiment_logs_generator.call_count == 1, "Experiment logs were not retrieved"
    assert open_mock.call_count == 1, "File wasn't saved."


def test_show_logs_match(mocker):
    es_client_mock = mocker.patch("commands.experiment.logs.K8sElasticSearchClient")

    es_client_instance = es_client_mock.return_value
    es_client_instance.get_experiment_logs_generator.return_value = TEST_LOG_ENTRIES

    proxy_mock = mocker.patch.object(logs, 'K8sProxy')

    get_current_namespace_mock = mocker.patch('commands.experiment.logs.get_kubectl_current_context_namespace')
    fake_experiment_1_name = 'fake-experiment-1'
    fake_experiment_2_name = 'fake-experiment-2'
    list_runs_mock = mocker.patch('commands.experiment.logs.list_runs')
    list_runs_mock.return_value = [Run(name=fake_experiment_1_name, experiment_name=fake_experiment_1_name),
                                   Run(name=fake_experiment_2_name, experiment_name=fake_experiment_2_name)]

    runner = CliRunner()
    result = runner.invoke(logs.logs, ['-m', 'fake-experiment'])

    assert proxy_mock.call_count == 1, 'port forwarding was not initiated'
    assert get_current_namespace_mock.call_count == 1, 'namespace was not retrieved'
    assert list_runs_mock.call_count == 1, 'run was not retrieved'
    assert es_client_instance.get_experiment_logs_generator.call_count == 2, 'Experiment logs were not retrieved'

    assert fake_experiment_1_name in result.output
    assert fake_experiment_2_name in result.output
