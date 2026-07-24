import json
import os
import signal
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestCredoHolderStartup:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setenv("HOLDER_URL", "http://localhost:8150")
        monkeypatch.setenv("HOLDER_TYPE", "credo")

    def test_start_allocates_port_and_starts_subprocess(self):
        with (
            patch("agents.holder.credo.subprocess.Popen") as mock_popen,
            patch("agents.holder.credo.portmanager.get_port", return_value=10001),
            patch("agents.holder.credo.CredoHolder.run_command") as mock_run,
            patch(
                "agents.holder.credo.CredoHolder.read_json_line",
                return_value={"result": {"endpoint": "http://localhost:10001"}},
            ),
        ):
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdin = MagicMock()
            mock_popen.return_value = mock_process

            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            holder.start()

            assert holder.port == 10001
            mock_popen.assert_called_once()
            assert "dist/agent.js" in mock_popen.call_args[0][0]
            mock_run.assert_called_once()

    def test_start_returns_port_on_failure(self):
        with (
            patch("agents.holder.credo.subprocess.Popen", side_effect=OSError("exec error")),
            patch("agents.holder.credo.portmanager.get_port", return_value=10002),
            patch("agents.holder.credo.portmanager.return_port") as mock_return,
        ):
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            with pytest.raises(OSError):
                holder.start()

            mock_return.assert_called_once_with(10002)

    def test_start_raises_when_process_dies_immediately(self):
        with (
            patch("agents.holder.credo.subprocess.Popen") as mock_popen,
            patch("agents.holder.credo.portmanager.get_port", return_value=10003),
            patch("agents.holder.credo.portmanager.return_port") as mock_return,
            patch(
                "agents.holder.credo.CredoHolder.read_json_line",
                return_value={"result": {"endpoint": "http://localhost:10003"}},
            ),
        ):
            mock_process = MagicMock()
            mock_process.poll.return_value = -1
            mock_process.stdin = MagicMock()
            mock_process.stdout.closed = False
            mock_popen.return_value = mock_process

            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            with pytest.raises(Exception, match="unable to start"):
                holder.start()

            mock_return.assert_called_once_with(10003)

    def test_start_reuses_agent_config_on_reinstantiate(self):
        with (
            patch("agents.holder.credo.subprocess.Popen") as mock_popen,
            patch("agents.holder.credo.portmanager.get_port", return_value=10004),
            patch("agents.holder.credo.CredoHolder.run_command") as mock_run,
            patch(
                "agents.holder.credo.CredoHolder.read_json_line",
                return_value={"result": {"endpoint": "http://localhost:10004"}},
            ),
        ):
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdin = MagicMock()
            mock_popen.return_value = mock_process

            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            holder.agent_config = {"existing": "config"}
            holder.start(reinstantiate=True)

            call = mock_run.call_args[0][0]
            assert call["agentConfig"] == {"existing": "config"}

    def test_start_returns_previous_port_before_allocating_new(self):
        with (
            patch("agents.holder.credo.subprocess.Popen") as mock_popen,
            patch("agents.holder.credo.portmanager.get_port", return_value=10005),
            patch("agents.holder.credo.portmanager.return_port") as mock_return,
            patch("agents.holder.credo.CredoHolder.run_command"),
            patch(
                "agents.holder.credo.CredoHolder.read_json_line",
                return_value={"result": {"endpoint": "http://localhost:10005"}},
            ),
        ):
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdin = MagicMock()
            mock_popen.return_value = mock_process

            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            holder.port = 9999
            holder.start()

            mock_return.assert_any_call(9999)
            assert holder.port == 10005


class TestCredoHolderShutdown:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setenv("SHUTDOWN_TIMEOUT_SECONDS", "5")
        monkeypatch.setenv("HOLDER_URL", "http://localhost:8150")
        monkeypatch.setenv("HOLDER_TYPE", "credo")

    def test_shutdown_returns_port_and_cleans_up(self):
        with (
            patch("agents.holder.credo.portmanager.return_port") as mock_return,
            patch("agents.holder.credo.os.kill") as mock_kill,
        ):
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            holder.port = 10006
            mock_stdin = MagicMock()
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_process.stdin = mock_stdin
            holder.agent = mock_process

            holder.shutdown()

            mock_return.assert_called_once_with(10006)
            assert holder.port is None
            mock_stdin.write.assert_called()
            mock_kill.assert_called_once_with(12345, signal.SIGTERM)
            assert holder.agent is None

    def test_shutdown_safe_when_agent_is_none(self):
        with patch("agents.holder.credo.portmanager.return_port") as mock_return:
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            holder.port = 10007
            holder.agent = None

            holder.shutdown()

            mock_return.assert_called_once_with(10007)
            assert holder.agent is None

    def test_shutdown_safe_when_port_is_none(self):
        with patch("agents.holder.credo.portmanager.return_port") as mock_return:
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            holder.port = None
            holder.agent = None

            holder.shutdown()

            mock_return.assert_not_called()

    def test_shutdown_safe_on_communicate_timeout(self):
        with patch("agents.holder.credo.portmanager.return_port"), patch("agents.holder.credo.os.kill") as mock_kill:
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            holder.port = 10008
            mock_stdin = MagicMock()
            mock_process = MagicMock()
            mock_process.pid = 12346
            mock_process.stdin = mock_stdin
            mock_process.communicate.side_effect = subprocess.TimeoutExpired("cmd", 5)
            holder.agent = mock_process

            holder.shutdown()

            mock_kill.assert_called_once_with(12346, signal.SIGTERM)
            assert holder.agent is None


class TestCredoHolderLifecycle:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setenv("SHUTDOWN_TIMEOUT_SECONDS", "5")
        monkeypatch.setenv("READ_TIMEOUT_SECONDS", "10")
        monkeypatch.setenv("ERRORS_BEFORE_RESTART", "10")
        monkeypatch.setenv("HOLDER_URL", "http://localhost:8150")
        monkeypatch.setenv("HOLDER_TYPE", "credo")

    def test_ensure_is_running_starts_when_not_running(self):
        with patch("agents.holder.credo.CredoHolder.start") as mock_start:
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            holder.agent = None

            holder.ensure_is_running()

            mock_start.assert_called_once()

    def test_ensure_is_running_returns_true_when_running(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.closed = False
        mock_process.stdin.closed = False
        holder.agent = mock_process

        assert holder.ensure_is_running() is True

    def test_ensure_is_running_restarts_on_closed_stdout(self):
        with patch("agents.holder.credo.CredoHolder.start") as mock_start:
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.stdout.closed = True
            mock_process.stdin.closed = False
            holder.agent = mock_process

            holder.ensure_is_running()

            mock_start.assert_called_once()

    def test_ensure_is_running_restarts_on_dead_process(self):
        with patch("agents.holder.credo.CredoHolder.start") as mock_start:
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            mock_process = MagicMock()
            mock_process.poll.return_value = -1
            holder.agent = mock_process

            holder.ensure_is_running()

            mock_start.assert_called_once()

    def test_is_running_returns_false_when_agent_none(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()
        holder.agent = None

        assert holder.is_running() is False

    def test_is_running_returns_false_when_process_dead(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()
        mock_process = MagicMock()
        mock_process.poll.return_value = -1
        holder.agent = mock_process

        assert holder.is_running() is False

    def test_is_running_returns_false_on_closed_pipes(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.closed = True
        holder.agent = mock_process

        assert holder.is_running() is False


class TestCredoHolderJsonRpc:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setenv("SHUTDOWN_TIMEOUT_SECONDS", "5")
        monkeypatch.setenv("READ_TIMEOUT_SECONDS", "10")
        monkeypatch.setenv("ERRORS_BEFORE_RESTART", "10")
        monkeypatch.setenv("HOLDER_URL", "http://localhost:8150")
        monkeypatch.setenv("HOLDER_TYPE", "credo")

    def test_run_command_writes_json_to_stdin(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()
        mock_stdin = MagicMock()
        mock_process = MagicMock()
        mock_process.stdin = mock_stdin
        holder.agent = mock_process

        holder.run_command({"cmd": "ping", "param": "value"})

        expected = json.dumps({"cmd": "ping", "param": "value"})
        mock_stdin.write.assert_any_call(expected)
        mock_stdin.write.assert_any_call("\n")
        mock_stdin.flush.assert_called_once()

    def test_run_command_calls_shutdown_on_error(self):
        with patch("agents.holder.credo.CredoHolder.shutdown") as mock_shutdown:
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()
            mock_stdin = MagicMock()
            mock_stdin.write.side_effect = BrokenPipeError()
            holder.agent = MagicMock()
            holder.agent.stdin = mock_stdin

            with pytest.raises(BrokenPipeError):
                holder.run_command({"cmd": "test"})

            mock_shutdown.assert_called_once()

    def _make_mock_poller(self, timeout_result=1):
        mock_poller = MagicMock()

        def poll_side_effect(timeout):
            return 0 if timeout == 0 else timeout_result

        mock_poller.poll.side_effect = poll_side_effect
        mock_poller.register = MagicMock()
        return mock_poller

    def test_read_json_line_parses_response(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()

        mock_stdout = MagicMock()
        mock_stdout.closed = False
        mock_stdout.readline.return_value = json.dumps({"error": 0, "result": "ok"}) + "\n"

        mock_process = MagicMock()
        mock_process.stdout = mock_stdout
        holder.agent = mock_process

        with patch("select.poll", return_value=self._make_mock_poller(timeout_result=1)):
            result = holder.read_json_line()

            assert result == {"error": 0, "result": "ok"}

    def test_read_json_line_raises_on_timeout(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()

        mock_process = MagicMock()
        mock_process.stdout.closed = False
        holder.agent = mock_process

        with patch("select.poll", return_value=self._make_mock_poller(timeout_result=0)):
            with pytest.raises(Exception, match="Read Timeout"):
                holder.read_json_line()

    def test_read_json_line_raises_on_eof(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()

        mock_stdout = MagicMock()
        mock_stdout.closed = False
        mock_stdout.readline.return_value = ""
        mock_process = MagicMock()
        mock_process.stdout = mock_stdout
        holder.agent = mock_process

        with patch("select.poll", return_value=self._make_mock_poller(timeout_result=1)):
            with pytest.raises(Exception, match="EOF reached"):
                holder.read_json_line()

    def test_read_json_line_raises_on_error_response(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()

        mock_stdout = MagicMock()
        mock_stdout.closed = False
        mock_stdout.readline.return_value = json.dumps({"error": 1, "result": "fail"}) + "\n"
        mock_process = MagicMock()
        mock_process.stdout = mock_stdout
        holder.agent = mock_process

        with patch("select.poll", return_value=self._make_mock_poller(timeout_result=1)):
            with pytest.raises(Exception, match="Error encountered"):
                holder.read_json_line()

    def test_read_json_line_increments_error_count(self):
        from agents.holder.credo import CredoHolder

        holder = CredoHolder()

        mock_stdout = MagicMock()
        mock_stdout.closed = False
        mock_stdout.readline.return_value = json.dumps({"error": 1, "result": "fail"}) + "\n"
        mock_process = MagicMock()
        mock_process.stdout = mock_stdout
        holder.agent = mock_process

        with patch("select.poll", return_value=self._make_mock_poller(timeout_result=1)):
            with pytest.raises(Exception, match="Error encountered"):
                holder.read_json_line()

            assert holder.errors == 1

    def test_read_json_line_shuts_down_after_max_errors(self):
        with patch("agents.holder.credo.CredoHolder.shutdown") as mock_shutdown:
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()

            mock_stdout = MagicMock()
            mock_stdout.closed = False
            mock_stdout.readline.return_value = json.dumps({"error": 1}) + "\n"
            mock_process = MagicMock()
            mock_process.stdout = mock_stdout
            holder.agent = mock_process

            with patch("select.poll", return_value=self._make_mock_poller(timeout_result=1)):
                holder.errors = 10
                with pytest.raises(Exception, match="Error encountered"):
                    holder.read_json_line()

                mock_shutdown.assert_called_once()


class TestCredoHolderCommands:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setenv("HOLDER_URL", "http://localhost:8150")
        monkeypatch.setenv("HOLDER_TYPE", "credo")

    def test_accept_invite_sends_receive_invitation(self):
        with (
            patch("agents.holder.credo.CredoHolder.run_command") as mock_run,
            patch("agents.holder.credo.CredoHolder.read_json_line", return_value={"connection": "conn-1"}),
        ):
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()

            result = holder.accept_invite("http://example.com/invite")

            assert result == "conn-1"
            mock_run.assert_called_with({"cmd": "receiveInvitation", "invitationUrl": "http://example.com/invite"})

    def test_accept_invite_fallback_on_connection_did(self):
        with (
            patch("agents.holder.credo.CredoHolder.run_command") as mock_run,
            patch("agents.holder.credo.CredoHolder.read_json_line", return_value={"connection": "conn-2"}),
        ):
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()

            result = holder.accept_invite("http://example.com/invite", use_connection_did=True)

            assert result == "conn-2"
            first_call = mock_run.call_args_list[0]
            assert first_call[0][0]["cmd"] == "receiveInvitationConnectionDid"

    def test_accept_invite_returns_none_when_no_connection(self):
        with (
            patch("agents.holder.credo.CredoHolder.run_command"),
            patch("agents.holder.credo.CredoHolder.read_json_line", return_value={"no_connection": True}),
        ):
            from agents.holder.credo import CredoHolder

            holder = CredoHolder()

            result = holder.accept_invite("http://example.com/invite")

            assert result is None
