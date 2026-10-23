"""The user menu exposes only administration and version information."""

from unittest.mock import Mock

import test_plugin_env_vars as _plugin_fixtures

mock_maya_modules = _plugin_fixtures.mock_maya_modules
plugin_module = _plugin_fixtures.plugin_module


def test_menu_contains_only_admin_and_about(plugin_module, mock_maya_modules):
    plugin_module._add_menu()

    items = [call[1] for call in mock_maya_modules.cmds.menuItem.call_args_list]
    assert [item["label"] for item in items if "label" in item] == [
        "Admin Panel",
        "About DCC MCP",
    ]
    assert not items[0].get("divider") and not items[-1].get("divider")
    assert not any(left.get("divider") and right.get("divider") for left, right in zip(items, items[1:]))


def test_menu_construction_preserves_internal_lifecycle_apis(plugin_module):
    lifecycle_names = ("_start", "_start_impl", "_start_async", "_stop_blocking", "_restart_deferred")
    lifecycle = {name: getattr(plugin_module, name) for name in lifecycle_names}

    plugin_module._add_menu()

    for name, function in lifecycle.items():
        assert callable(function)
        assert getattr(plugin_module, name) is function


def test_menu_callbacks_open_admin_and_version_information(plugin_module, mock_maya_modules, monkeypatch):
    admin = Mock()
    about = Mock()
    monkeypatch.setattr(plugin_module, "_open_admin_panel", admin)
    monkeypatch.setattr(plugin_module, "_show_about", about)
    plugin_module._add_menu()

    commands = {
        call.kwargs["label"]: call.kwargs["command"]
        for call in mock_maya_modules.cmds.menuItem.call_args_list
        if "label" in call.kwargs
    }
    commands["Admin Panel"](False)
    commands["About DCC MCP"](False)
    admin.assert_called_once_with()
    about.assert_called_once_with()


def test_reinstall_replaces_legacy_items_without_duplicates(plugin_module, mock_maya_modules):
    menus = {
        plugin_module._menu_name: [
            {"label": label}
            for label in (
                "OpenAPI Docs",
                "Admin Panel",
                "Copy Instance ID",
                "Server Info",
                "Start MCP Server",
                "Stop MCP Server",
                "Restart MCP Server",
                "Enable/Disable Hot Reload",
                "About DCC MCP",
            )
        ]
    }

    def menu(name, **kwargs):
        if kwargs.get("exists"):
            return name in menus
        assert name not in menus
        menus[name] = []

    mock_maya_modules.cmds.menu.side_effect = menu
    mock_maya_modules.cmds.deleteUI.side_effect = menus.pop
    mock_maya_modules.cmds.menuItem.side_effect = lambda **kwargs: menus[plugin_module._menu_name].append(kwargs)

    for _ in range(3):
        plugin_module._add_menu()
        items = menus[plugin_module._menu_name]
        assert [item.get("label", "separator") for item in items] == [
            "Admin Panel",
            "separator",
            "About DCC MCP",
        ]
    assert mock_maya_modules.cmds.deleteUI.call_count == 3
