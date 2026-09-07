import unittest
from unittest import mock

from dwarf_comms import send_without_response


class SendWithoutResponseTests(unittest.TestCase):
    def test_returns_false_when_socket_is_not_started(self):
        with mock.patch("dwarf_python_api.lib.websockets_utils.client_instance", None):
            self.assertFalse(send_without_response(object(), 11000, 3))

    def test_sends_on_the_client_loop_without_waiting_for_ack(self):
        loop = mock.Mock()
        client = mock.Mock()
        client.task.get_loop.return_value = loop
        future = mock.Mock()
        with mock.patch("dwarf_python_api.lib.websockets_utils.client_instance", client):
            with mock.patch("dwarf_python_api.lib.websockets_utils.send_socket", mock.Mock()):
                with mock.patch(
                    "dwarf_comms.asyncio.run_coroutine_threadsafe", return_value=future
                ) as run:
                    self.assertTrue(send_without_response(object(), 15004, 8, timeout=2))
        run.assert_called_once()
        future.result.assert_called_once_with(timeout=2)
        self.assertEqual(run.call_args[0][1], loop)
