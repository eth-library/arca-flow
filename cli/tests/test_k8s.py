"""Tests for k8s commands — unit and behavioral."""

import string
from unittest.mock import MagicMock, patch

from arca_flow_cli.app import app
from arca_flow_cli.commands.k8s import _generate_password, _get_pending_pods, _wait_for_pods
from typer.testing import CliRunner

runner = CliRunner()


# ── Unit: _generate_password ──


def test_generate_password_length():
    pw = _generate_password()
    assert len(pw) == 32


def test_generate_password_custom_length():
    pw = _generate_password(64)
    assert len(pw) == 64


def test_generate_password_characters():
    allowed = set(string.ascii_letters + string.digits)
    pw = _generate_password()
    assert all(c in allowed for c in pw)


# ── Unit: _get_pending_pods ──


@patch("arca_flow_cli.commands.k8s.run_capture")
def test_get_pending_pods_all_ready(mock_run):
    mock_run.return_value = (
        0,
        "dagster-webserver-abc|Running|true\ndagster-daemon-xyz|Running|true",
    )
    assert _get_pending_pods() == []


@patch("arca_flow_cli.commands.k8s.run_capture")
def test_get_pending_pods_some_pending(mock_run):
    mock_run.return_value = (
        0,
        "dagster-webserver-abc|Running|true\ndagster-daemon-xyz|Pending|false",
    )
    pending = _get_pending_pods()
    assert len(pending) == 1
    assert "daemon-xyz" in pending[0]
    assert "Pending" in pending[0]


@patch("arca_flow_cli.commands.k8s.run_capture")
def test_get_pending_pods_kubectl_fails(mock_run):
    mock_run.return_value = (1, "")
    pending = _get_pending_pods()
    assert pending == ["unable to query pods"]


@patch("arca_flow_cli.commands.k8s.run_capture")
def test_get_pending_pods_empty_output(mock_run):
    mock_run.return_value = (0, "")
    pending = _get_pending_pods()
    assert pending == ["unable to query pods"]


# ── Behavioral: down() ──


@patch("arca_flow_cli.commands.k8s.run_capture", return_value=(0, ""))
def test_down_calls_all_teardown_steps(mock_run):
    result = runner.invoke(app, ["k8s", "down", "--yes"])
    assert result.exit_code == 0

    cmds = [c[0][0] for c in mock_run.call_args_list]
    # Should call helm uninstall
    assert any("helm" in cmd and "uninstall" in cmd for cmd in cmds)
    # Should delete jobs
    assert any("delete" in cmd and "jobs" in cmd for cmd in cmds)
    # Should delete pods
    assert any("delete" in cmd and "pods" in cmd for cmd in cmds)
    # Should delete PVC
    assert any("delete" in cmd and "pvc" in cmd for cmd in cmds)
    # Should delete ConfigMap
    assert any("delete" in cmd and "configmap" in cmd for cmd in cmds)


@patch("arca_flow_cli.commands.k8s.run_capture", return_value=(1, ""))
def test_down_shows_not_found_on_failure(mock_run):
    result = runner.invoke(app, ["k8s", "down", "--yes"])
    assert result.exit_code == 0
    assert "not found" in result.output


@patch("arca_flow_cli.commands.k8s.run_capture", return_value=(0, ""))
def test_down_shows_teardown_complete(mock_run):
    result = runner.invoke(app, ["k8s", "down", "--yes"])
    assert "Teardown complete" in result.output


# ── Behavioral: status() ──


@patch("arca_flow_cli.commands.k8s.run_capture")
def test_status_no_deployment(mock_run):
    mock_run.return_value = (1, "")
    result = runner.invoke(app, ["k8s", "status"])
    assert result.exit_code == 0
    assert "not running" in result.output.lower()


@patch("arca_flow_cli.commands.k8s.run_capture")
def test_status_with_pods(mock_run):
    def side_effect(cmd, **kwargs):
        if "get" in cmd and "namespace" in cmd:
            return (0, "dagster   Active   10d")
        if "get" in cmd and "pods" in cmd:
            return (0, "NAME         READY   STATUS\nwebserver    1/1     Running")
        if "get" in cmd and "svc" in cmd:
            return (0, "NAME         TYPE        CLUSTER-IP\nwebserver    ClusterIP   10.0.0.1")
        return (0, "")

    mock_run.side_effect = side_effect
    result = runner.invoke(app, ["k8s", "status"])
    assert result.exit_code == 0
    assert "Pods" in result.output
    assert "Services" in result.output


# ── Unit: _wait_for_pods timeout ──


@patch("arca_flow_cli.commands.k8s.time")
@patch("arca_flow_cli.commands.k8s._get_pending_pods")
def test_wait_for_pods_timeout(mock_pending, mock_time):
    # Simulate: first call sets deadline, second enters loop, third for elapsed, fourth exceeds deadline
    mock_time.monotonic.side_effect = [0.0, 0.0, 3.0, 181.0]
    mock_time.sleep = MagicMock()
    mock_pending.return_value = ["webserver (Pending)"]

    status_obj = MagicMock()
    result = _wait_for_pods(status_obj)

    assert result is False
    mock_time.sleep.assert_called_once_with(3)
    status_obj.update.assert_called_once()


@patch("arca_flow_cli.commands.k8s.time")
@patch("arca_flow_cli.commands.k8s._get_pending_pods")
def test_wait_for_pods_success(mock_pending, mock_time):
    # Pods become ready on first check
    mock_time.monotonic.side_effect = [0.0, 0.0]
    mock_pending.return_value = []

    status_obj = MagicMock()
    result = _wait_for_pods(status_obj)

    assert result is True
    mock_time.sleep.assert_not_called()


@patch("arca_flow_cli.commands.k8s.time")
@patch("arca_flow_cli.commands.k8s._get_pending_pods")
def test_wait_for_pods_becomes_ready(mock_pending, mock_time):
    # Pods pending on first check, ready on second
    mock_time.monotonic.side_effect = [0.0, 0.0, 3.0, 6.0]
    mock_time.sleep = MagicMock()
    mock_pending.side_effect = [["daemon (Pending)"], []]

    status_obj = MagicMock()
    result = _wait_for_pods(status_obj)

    assert result is True
