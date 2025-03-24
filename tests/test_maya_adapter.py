"""Tests for the Maya MCP adapter.

This module contains tests for the Maya MCP adapter.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import json

# Import the module to test
from dcc_mcp_maya.adapter import MayaMCPAdapter
from dcc_mcp_maya.client import MayaRPyCClient


class TestMayaMCPAdapter(unittest.TestCase):
    """Test case for the Maya MCP adapter."""

    def setUp(self):
        """Set up the test case."""
        # Create a mock client
        self.mock_client = MagicMock(spec=MayaRPyCClient)
        self.mock_client.is_connected.return_value = True
        self.mock_client.get_scene_info.return_value = {
            "scene_name": "test_scene.ma",
            "selection": [],
            "objects": ["persp", "top", "front", "side"],
            "cameras": ["persp", "top", "front", "side"],
            "maya_version": "2023",
        }

        # Create a mock for the plugin manager
        self.mock_plugin_manager = MagicMock()
        self.mock_plugin_manager.call_plugin_function.return_value = {
            "status": "success",
            "message": "Plugin function called successfully",
        }

        # Create a mock for the get_plugin_manager function
        self.mock_get_plugin_manager = MagicMock(return_value=self.mock_plugin_manager)

        # Create a mock for the call_plugin_function function
        self.mock_call_plugin_function = MagicMock(
            return_value={
                "status": "success",
                "message": "Plugin function called successfully",
            }
        )

        # Create a mock for the get_client function
        self.mock_get_client = MagicMock(return_value=self.mock_client)

        # Create the adapter with the mock client
        with patch("dcc_mcp_maya.adapter.get_plugin_manager", self.mock_get_plugin_manager):
            with patch("dcc_mcp_maya.adapter.call_plugin_function", self.mock_call_plugin_function):
                with patch("dcc_mcp_maya.adapter.get_client", self.mock_get_client):
                    # Create the adapter
                    self.adapter = MayaMCPAdapter()

                    # Ensure the adapter has all necessary attributes
                    self.adapter.dcc_client = self.mock_client
                    self.adapter.timeout = 5
                    self.adapter.last_connection_check = 0

    def test_ensure_connected(self):
        """Test the ensure_connected method."""
        # Test when the client is connected
        self.assertTrue(self.adapter.ensure_connected())

        # Test when the client is not connected
        self.mock_client.is_connected.return_value = False
        self.mock_client.reconnect.return_value = True
        self.assertTrue(self.adapter.ensure_connected())

        # Test when the client fails to reconnect
        self.mock_client.reconnect.return_value = False
        self.adapter.last_connection_check = 0  # Force a connection check
        self.assertFalse(self.adapter.ensure_connected())

    def test_get_scene_info(self):
        """Test the get_scene_info method."""
        # Test when the client is connected
        scene_info = self.adapter.get_scene_info()
        self.assertEqual(scene_info["scene_name"], "test_scene.ma")
        self.assertEqual(scene_info["maya_version"], "2023")

        # Test when the client is not connected
        self.mock_client.is_connected.return_value = False
        self.mock_client.reconnect.return_value = False
        self.adapter.last_connection_check = 0  # Force a connection check
        scene_info = self.adapter.get_scene_info()
        self.assertIn("error", scene_info)

        # Test when the client raises an exception
        self.mock_client.is_connected.return_value = True
        self.mock_client.get_scene_info.side_effect = Exception("Test exception")
        scene_info = self.adapter.get_scene_info()
        self.assertIn("error", scene_info)

    def test_maya_create_primitive(self):
        """Test the maya_create_primitive method."""
        # Set up the mock client
        self.mock_client.create_primitive.return_value = ["pCube1", "polyCube1"]

        # Test creating a cube
        result = self.adapter.maya_create_primitive("cube", width=2, height=2, depth=2)
        self.mock_client.create_primitive.assert_called_with("cube", width=2, height=2, depth=2)
        self.assertEqual(result["result"], ["pCube1", "polyCube1"])
        self.assertIn("scene_info", result)

        # Test when the client is not connected
        self.mock_client.is_connected.return_value = False
        self.mock_client.reconnect.return_value = False
        self.adapter.last_connection_check = 0  # Force a connection check
        result = self.adapter.maya_create_primitive("cube")
        self.assertIn("error", result)

        # Test when the client raises an exception
        self.mock_client.is_connected.return_value = True
        self.mock_client.create_primitive.side_effect = Exception("Test exception")
        result = self.adapter.maya_create_primitive("cube")
        self.assertIn("error", result)

    def test_maya_execute_command(self):
        """Test the maya_execute_command method."""
        # Set up the mock client
        self.mock_client.execute_cmd.return_value = ["pCube1", "polyCube1"]

        # Test executing a command with string args
        result = self.adapter.maya_execute_command(
            "polyCube", args="[]", kwargs='{"width": 2, "height": 2, "depth": 2}'
        )
        self.mock_client.execute_cmd.assert_called_with("polyCube", width=2, height=2, depth=2)
        self.assertEqual(result["result"], ["pCube1", "polyCube1"])
        self.assertIn("scene_info", result)

        # Test executing a command with JSON args
        result = self.adapter.maya_execute_command("polyCube", args="[1, 2, 3]", kwargs='{"width": 2}')
        self.mock_client.execute_cmd.assert_called_with("polyCube", 1, 2, 3, width=2)

        # Test executing a command with invalid JSON args
        result = self.adapter.maya_execute_command("polyCube", args="invalid", kwargs="invalid")
        self.mock_client.execute_cmd.assert_called_with("polyCube", "invalid")

        # Test when the client is not connected
        self.mock_client.is_connected.return_value = False
        self.mock_client.reconnect.return_value = False
        self.adapter.last_connection_check = 0  # Force a connection check
        result = self.adapter.maya_execute_command("polyCube")
        self.assertIn("error", result)

        # Test when the client raises an exception
        self.mock_client.is_connected.return_value = True
        self.mock_client.execute_cmd.side_effect = Exception("Test exception")
        result = self.adapter.maya_execute_command("polyCube")
        self.assertIn("error", result)

    def test_maya_execute_mel(self):
        """Test the maya_execute_mel method."""
        # Set up the mock client
        self.mock_client.execute_mel.return_value = "Result of MEL script"

        # Test executing a MEL script
        result = self.adapter.maya_execute_mel("polyCube -width 2 -height 2 -depth 2;")
        self.mock_client.execute_mel.assert_called_with("polyCube -width 2 -height 2 -depth 2;")
        self.assertEqual(result["result"], "Result of MEL script")
        self.assertIn("scene_info", result)

        # Test when the client is not connected
        self.mock_client.is_connected.return_value = False
        self.mock_client.reconnect.return_value = False
        self.adapter.last_connection_check = 0  # Force a connection check
        result = self.adapter.maya_execute_mel("polyCube;")
        self.assertIn("error", result)

        # Test when the client raises an exception
        self.mock_client.is_connected.return_value = True
        self.mock_client.execute_mel.side_effect = Exception("Test exception")
        result = self.adapter.maya_execute_mel("polyCube;")
        self.assertIn("error", result)

    def test_maya_get_scene_info(self):
        """Test the maya_get_scene_info method."""
        # Test getting scene info
        result = self.adapter.maya_get_scene_info()
        self.assertEqual(result["scene_name"], "test_scene.ma")
        self.assertEqual(result["maya_version"], "2023")

    def test_maya_plugin_call(self):
        """Test the maya_plugin_call method."""
        # Test calling a plugin function using the plugin manager
        result = self.adapter.maya_plugin_call("test_plugin", {"param": "value"})
        self.mock_call_plugin_function.assert_called_with("maya", "test_plugin", "func_call", {"param": "value"})
        self.assertEqual(result["result"]["status"], "success")
        self.assertIn("scene_info", result)

        # Test calling a plugin function using RPYC
        self.mock_call_plugin_function.side_effect = ImportError("Test exception")
        self.mock_client.plugin_call.return_value = {
            "status": "success",
            "message": "Plugin function called successfully through RPYC",
        }
        result = self.adapter.maya_plugin_call("test_plugin", {"param": "value"})
        self.mock_client.plugin_call.assert_called_with("test_plugin", {"param": "value"})
        self.assertEqual(result["result"]["status"], "success")
        self.assertIn("scene_info", result)

        # Test when the client is not connected
        self.mock_client.is_connected.return_value = False
        self.mock_client.reconnect.return_value = False
        self.adapter.last_connection_check = 0  # Force a connection check
        result = self.adapter.maya_plugin_call("test_plugin")
        self.assertIn("error", result)

        # Test when the client raises an exception
        self.mock_client.is_connected.return_value = True
        self.mock_client.plugin_call.side_effect = Exception("Test exception")
        result = self.adapter.maya_plugin_call("test_plugin")
        self.assertIn("error", result)

    def test_initialize_plugin_paths(self):
        """Test the _initialize_plugin_paths method."""
        # Mock os.path.exists to control which paths exist
        with patch("os.path.exists", side_effect=lambda path: "plugins" in path):
            # Mock os.environ to provide custom plugin paths
            with patch.dict("os.environ", {"DCC_MCP_PLUGIN_PATHS": "/custom/path1:/custom/path2"}):
                # Mock os.pathsep to handle path separator
                with patch("os.pathsep", ":"):
                    # Create a new adapter instance to trigger _initialize_plugin_paths
                    adapter = MayaMCPAdapter()

                    # Check that the plugin paths were correctly initialized
                    self.assertIn("/custom/path1", adapter.maya_mcp_plugins_paths)
                    self.assertIn("/custom/path2", adapter.maya_mcp_plugins_paths)

    def test_discover_plugins(self):
        """Test the discover_plugins method."""
        # Mock glob.glob to return a list of plugin files
        mock_plugin_files = [
            "/path/to/plugins/maya/plugin1.py",
            "/path/to/plugins/maya/plugin2.py",
            "/path/to/plugins/maya/__init__.py",  # This should be skipped
        ]

        with patch("glob.glob", return_value=mock_plugin_files):
            # Mock _get_plugin_info to return plugin info
            self.adapter._get_plugin_info = MagicMock(
                side_effect=[
                    {"name": "plugin1", "path": "/path/to/plugins/maya/plugin1.py", "description": "Plugin 1"},
                    {"name": "plugin2", "path": "/path/to/plugins/maya/plugin2.py", "description": "Plugin 2"},
                ]
            )

            # Set plugin paths
            self.adapter.maya_mcp_plugins_paths = ["/path/to/plugins/maya"]

            # Test discovering plugins
            plugins = self.adapter.discover_plugins()

            # Check that the correct plugins were discovered
            self.assertEqual(len(plugins), 2)
            self.assertEqual(plugins[0]["name"], "plugin1")
            self.assertEqual(plugins[1]["name"], "plugin2")

            # Test with an exception during plugin discovery
            self.adapter._get_plugin_info = MagicMock(side_effect=Exception("Test exception"))
            plugins = self.adapter.discover_plugins()
            self.assertEqual(len(plugins), 0)

    def test_get_plugin_info(self):
        """Test the _get_plugin_info method."""
        # Create a mock module with the required attributes
        mock_module = MagicMock()
        mock_module.func_call = MagicMock()
        mock_module.__doc__ = "Test plugin description"
        mock_module.PLUGIN_INFO = {"version": "1.0", "author": "Test Author"}

        # Mock importlib.util.spec_from_file_location and related functions
        with patch("importlib.util.spec_from_file_location") as mock_spec_from_file_location:
            with patch("importlib.util.module_from_spec") as mock_module_from_spec:
                # Set up the mocks
                mock_spec = MagicMock()
                mock_spec_from_file_location.return_value = mock_spec
                mock_module_from_spec.return_value = mock_module

                # Test getting plugin info
                plugin_info = self.adapter._get_plugin_info("/path/to/plugin.py", "plugin")

                # Check that the correct plugin info was returned
                self.assertEqual(plugin_info["name"], "plugin")
                self.assertEqual(plugin_info["path"], "/path/to/plugin.py")
                self.assertEqual(plugin_info["description"], "Test plugin description")
                self.assertEqual(plugin_info["version"], "1.0")
                self.assertEqual(plugin_info["author"], "Test Author")

                # Test with a module that doesn't have func_call
                delattr(mock_module, "func_call")
                plugin_info = self.adapter._get_plugin_info("/path/to/plugin.py", "plugin")
                self.assertIsNone(plugin_info)

                # Test with an exception during module loading
                mock_spec.loader.exec_module.side_effect = Exception("Test exception")
                plugin_info = self.adapter._get_plugin_info("/path/to/plugin.py", "plugin")
                self.assertIsNone(plugin_info)


if __name__ == "__main__":
    unittest.main()
