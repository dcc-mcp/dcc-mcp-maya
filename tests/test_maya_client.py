"""Tests for the Maya RPYC client.

This module contains tests for the Maya RPYC client.
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# Import the module to test
from dcc_mcp_maya.client import MayaRPyCClient, get_maya_client


class TestMayaRPyCClient(unittest.TestCase):
    """Test case for the Maya RPYC client."""

    def setUp(self):
        """Set up the test case."""
        # Create a mock for the RPYC connection
        self.mock_connection = MagicMock()

        # Create a mock for the Maya commands module
        self.mock_cmds = MagicMock()
        self.mock_connection.modules.maya.cmds = self.mock_cmds

        # Create a mock for the Maya MEL module
        self.mock_mel = MagicMock()
        self.mock_connection.modules.maya.mel = self.mock_mel

        # Create a mock for the proxy object
        self.mock_proxy = MagicMock()

        # Create the client with mocked connection
        with patch("rpyc.connect") as mock_connect:
            mock_connect.return_value = self.mock_connection
            self.client = MayaRPyCClient(host="localhost", port=12345)
            self.client.connection = self.mock_connection
            self.client.proxy = self.mock_proxy

    def test_cmds_property(self):
        """Test the cmds property."""
        # Test when connected
        self.client.ensure_connected = MagicMock(return_value=True)
        self.client._cmds = self.mock_cmds  # Ensure _cmds is set.
        cmds = self.client.cmds
        self.assertEqual(cmds, self.mock_cmds)

        # Test when not connected
        self.client.ensure_connected = MagicMock(return_value=False)
        cmds = self.client.cmds
        self.assertIsNone(cmds)

        # Test when retrieving cmds raises an exception
        self.client.ensure_connected = MagicMock(return_value=True)
        self.client._cmds = None

        # Mock access to connection.modules.maya.cmds throws an exception
        with patch.object(self.client, "connection", create=True) as mock_conn:
            type(mock_conn).modules = PropertyMock(side_effect=Exception("Test exception"))
            cmds = self.client.cmds
            self.assertIsNone(cmds)

    def test_execute_mel(self):
        """Test the execute_mel method."""
        # Set up the mock
        self.mock_mel.eval.return_value = "Result of MEL script"

        # Test executing a MEL script
        self.client.ensure_connected = MagicMock(return_value=True)
        result = self.client.execute_mel("polyCube -width 2 -height 2 -depth 2;")
        self.mock_mel.eval.assert_called_with("polyCube -width 2 -height 2 -depth 2;")
        self.assertEqual(result, "Result of MEL script")

        # Test when not connected
        self.client.ensure_connected = MagicMock(return_value=False)
        with self.assertRaises(ConnectionError):
            self.client.execute_mel("polyCube;")

        # Test when execution raises an exception
        self.client.ensure_connected = MagicMock(return_value=True)
        self.mock_mel.eval.side_effect = Exception("Test exception")
        with self.assertRaises(Exception):
            self.client.execute_mel("polyCube;")

    def test_execute_cmd(self):
        """Test the execute_cmd method."""
        # Test when connected and cmds is available
        self.client.ensure_connected = MagicMock(return_value=True)
        self.client._cmds = self.mock_cmds
        self.mock_cmds.polyCube = MagicMock(return_value=["pCube1", "polyCube1"])

        result = self.client.execute_cmd("polyCube")
        self.mock_cmds.polyCube.assert_called_once()
        self.assertEqual(result, ["pCube1", "polyCube1"])

        # Test with arguments
        self.mock_cmds.polyCube.reset_mock()
        result = self.client.execute_cmd("polyCube", width=2, height=3)
        self.mock_cmds.polyCube.assert_called_with(width=2, height=3)

        # Test when not connected
        self.client.ensure_connected = MagicMock(return_value=False)
        with self.assertRaises(ConnectionError):
            self.client.execute_cmd("polyCube")

        # Test when cmds is None
        self.client.ensure_connected = MagicMock(return_value=True)
        self.client._cmds = None
        with self.assertRaises(ConnectionError):
            self.client.execute_cmd("polyCube")

    def test_create_primitive(self):
        """Test the create_primitive method."""
        # Set up the mocks for different primitive commands
        self.mock_cmds.polyCube = MagicMock(return_value=["pCube1", "polyCube1"])
        self.mock_cmds.polySphere = MagicMock(return_value=["pSphere1", "polySphere1"])
        self.mock_cmds.polyCylinder = MagicMock(return_value=["pCylinder1", "polyCylinder1"])
        self.mock_cmds.polyCone = MagicMock(return_value=["pCone1", "polyCone1"])
        self.mock_cmds.polyPlane = MagicMock(return_value=["pPlane1", "polyPlane1"])
        self.mock_cmds.polyTorus = MagicMock(return_value=["pTorus1", "polyTorus1"])

        # Test creating different primitives
        self.client.ensure_connected = MagicMock(return_value=True)
        self.client._cmds = self.mock_cmds

        # Test cube
        result = self.client.create_primitive("cube", width=2)
        self.mock_cmds.polyCube.assert_called_with(width=2)
        self.assertEqual(result, ["pCube1", "polyCube1"])

        # Test sphere
        result = self.client.create_primitive("sphere", radius=3)
        self.mock_cmds.polySphere.assert_called_with(radius=3)
        self.assertEqual(result, ["pSphere1", "polySphere1"])

        # Test cylinder
        result = self.client.create_primitive("cylinder", height=4)
        self.mock_cmds.polyCylinder.assert_called_with(height=4)
        self.assertEqual(result, ["pCylinder1", "polyCylinder1"])

        # Test cone
        result = self.client.create_primitive("cone")
        self.mock_cmds.polyCone.assert_called_with()
        self.assertEqual(result, ["pCone1", "polyCone1"])

        # Test plane
        result = self.client.create_primitive("plane")
        self.mock_cmds.polyPlane.assert_called_with()
        self.assertEqual(result, ["pPlane1", "polyPlane1"])

        # Test torus
        result = self.client.create_primitive("torus")
        self.mock_cmds.polyTorus.assert_called_with()
        self.assertEqual(result, ["pTorus1", "polyTorus1"])

        # Test unsupported primitive
        with self.assertRaises(ValueError):
            self.client.create_primitive("unsupported")

        # Test when not connected
        self.client.ensure_connected = MagicMock(return_value=False)
        with self.assertRaises(ConnectionError):
            self.client.create_primitive("cube")

        # Test when creation raises an exception
        self.client.ensure_connected = MagicMock(return_value=True)
        self.mock_cmds.polyCube.side_effect = Exception("Test exception")
        with self.assertRaises(Exception):
            self.client.create_primitive("cube")

    def test_get_scene_info(self):
        """Test the get_scene_info method."""
        # Set up the mocks
        self.mock_cmds.file = MagicMock(return_value="/path/to/scene.ma")
        self.mock_cmds.ls = MagicMock(
            side_effect=[
                ["pCube1", "pSphere1"],  # For selection=True
                ["persp", "top", "front", "side", "pCube1", "pSphere1"],  # For long=True
            ]
        )

        # Test getting scene info
        self.client.ensure_connected = MagicMock(return_value=True)
        self.client._cmds = self.mock_cmds

        result = self.client.get_scene_info()

        # Check that the correct methods were called
        self.mock_cmds.file.assert_called_with(query=True, sceneName=True)
        self.mock_cmds.ls.assert_any_call(selection=True)
        self.mock_cmds.ls.assert_any_call(long=True)

        # Check the result
        self.assertEqual(result["scene_path"], "/path/to/scene.ma")
        self.assertEqual(result["selection"], ["pCube1", "pSphere1"])
        self.assertEqual(result["stats"]["num_objects"], 6)
        self.assertEqual(result["stats"]["num_selected"], 2)

        # Test when not connected
        self.client.ensure_connected = MagicMock(return_value=False)
        with self.assertRaises(ConnectionError):
            self.client.get_scene_info()

        # Test when getting scene info raises an exception
        self.client.ensure_connected = MagicMock(return_value=True)
        self.mock_cmds.file.side_effect = Exception("Test exception")
        with self.assertRaises(Exception):
            self.client.get_scene_info()

    def test_action_call(self):
        """Test the action_call method."""
        # Set up the mock
        mock_call_action_function = MagicMock(
            return_value={
                "success": True,
                "message": "Action function called successfully",
                "context": {"result": "test_result"},
            }
        )

        # Test calling an action function
        self.client.ensure_connected = MagicMock(return_value=True)
        self.client.is_connected = MagicMock(return_value=True)

        # Mock the import of call_action_function
        with patch.dict(
            "sys.modules", {"dcc_mcp_core.actions.manager": MagicMock(call_action_function=mock_call_action_function)}
        ):
            result = self.client.action_call("test_action", "test_function", {"param": "value"})

            # Check that the correct methods were called
            mock_call_action_function.assert_called_with(
                "maya",
                "test_action",
                "test_function",
                {"param": "value", "_maya_rpyc_client": self.client, "_maya_cmds": self.client._cmds},
            )

            # Check the result
            self.assertEqual(result["success"], True)
            self.assertEqual(result["message"], "Action function called successfully")
            self.assertEqual(result["context"]["result"], "test_result")

        # Test with default function name
        with patch.dict(
            "sys.modules", {"dcc_mcp_core.actions.manager": MagicMock(call_action_function=mock_call_action_function)}
        ):
            result = self.client.action_call("test_action", None, {"param": "value"})

            # Check that the correct methods were called with default function name 'main'
            mock_call_action_function.assert_called_with(
                "maya",
                "test_action",
                "main",
                {"param": "value", "_maya_rpyc_client": self.client, "_maya_cmds": self.client._cmds},
            )

        # Test when not connected
        self.client.is_connected = MagicMock(return_value=False)
        self.client.reconnect = MagicMock()
        with patch.dict(
            "sys.modules", {"dcc_mcp_core.actions.manager": MagicMock(call_action_function=mock_call_action_function)}
        ):
            self.client.action_call("test_action", "test_function")
            self.client.reconnect.assert_called_once()

        # Test when action call raises an exception
        self.client.is_connected = MagicMock(return_value=True)
        with patch.dict(
            "sys.modules",
            {
                "dcc_mcp_core.actions.manager": MagicMock(
                    call_action_function=MagicMock(side_effect=Exception("Test exception"))
                )
            },
        ):
            with self.assertRaises(Exception):
                self.client.action_call("test_action", "test_function")

    def test_plugin_call(self):
        """Test the plugin_call method."""
        # Set up the mock
        mock_action_call = MagicMock(return_value={"success": True, "message": "Action function called successfully"})

        # Test that plugin_call redirects to action_call
        self.client.action_call = mock_action_call
        result = self.client.plugin_call("test_plugin", {"param": "value"})

        # Check that action_call was called with the correct parameters
        mock_action_call.assert_called_with("test_plugin", "func_call", {"param": "value"})

        # Check the result
        self.assertEqual(result["success"], True)
        self.assertEqual(result["message"], "Action function called successfully")


class TestGetMayaClient(unittest.TestCase):
    """Test case for the get_maya_client function."""

    def test_get_maya_client(self):
        """Test the get_maya_client function."""
        # Create a mock for the rpyc_get_client function
        mock_rpyc_get_client = MagicMock()

        # Test when rpyc_get_client returns a MayaRPyCClient
        mock_maya_client = MagicMock(spec=MayaRPyCClient)
        mock_rpyc_get_client.return_value = mock_maya_client

        with patch("dcc_mcp_maya.client.rpyc_get_client", mock_rpyc_get_client):
            client = get_maya_client("localhost", 12345, True, 5.0)

            # Check that the correct methods were called
            mock_rpyc_get_client.assert_called_with("maya", "localhost", 12345, True, 5.0, None)

            # Check the result
            self.assertEqual(client, mock_maya_client)

        # Test when rpyc_get_client returns a non-MayaRPyCClient
        mock_other_client = MagicMock()  # Not a MayaRPyCClient
        mock_rpyc_get_client.return_value = mock_other_client

        with patch("dcc_mcp_maya.client.rpyc_get_client", mock_rpyc_get_client):
            with patch("dcc_mcp_maya.client.MayaRPyCClient") as mock_maya_rpyc_client_class:
                mock_maya_rpyc_client = MagicMock(spec=MayaRPyCClient)
                mock_maya_rpyc_client_class.return_value = mock_maya_rpyc_client

                client = get_maya_client("localhost", 12345, True, 5.0)

                # Check that the correct methods were called
                mock_rpyc_get_client.assert_called_with("maya", "localhost", 12345, True, 5.0, None)
                mock_maya_rpyc_client_class.assert_called_with(
                    dcc_name="maya",
                    host="localhost",
                    port=12345,
                    auto_connect=True,
                    connection_timeout=5.0,
                    registry_path=None,
                )

                # Check the result
                self.assertEqual(client, mock_maya_rpyc_client)


if __name__ == "__main__":
    unittest.main()
