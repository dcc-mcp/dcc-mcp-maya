"""The user menu keeps discovery entries without server lifecycle controls."""

import test_plugin_env_vars as _plugin_fixtures

mock_maya_modules = _plugin_fixtures.mock_maya_modules
plugin_module = _plugin_fixtures.plugin_module


def test_menu_omits_lifecycle_controls_and_preserves_other_entries(plugin_module, mock_maya_modules):
    plugin_module._add_menu()

    items = [call[1] for call in mock_maya_modules.cmds.menuItem.call_args_list]
    assert [item["label"] for item in items if "label" in item] == [
        "OpenAPI Docs",
        "Admin Panel",
        "Copy Instance ID",
        "Server Info",
        "Enable/Disable Hot Reload",
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
