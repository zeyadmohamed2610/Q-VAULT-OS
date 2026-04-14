from dataclasses import dataclass


@dataclass(frozen=True)
class AppDefinition:
    name: str
    emoji: str
    module: str
    class_name: str
    icon_asset: str | None = None
    sessions: frozenset[str] = frozenset({"real", "fake"})
    show_on_desktop: bool = True


APP_DEFINITIONS: tuple[AppDefinition, ...] = (
    AppDefinition(
        name="Terminal",
        emoji="🖥️",
        module="terminal",
        class_name="Terminal",
        icon_asset="icon-terminal.svg",
    ),
    AppDefinition(
        name="Files",
        emoji="📁",
        module="file_explorer",
        class_name="FileExplorer",
        icon_asset="icon-files.svg",
    ),
    AppDefinition(
        name="Task Manager",
        emoji="📊",
        module="task_manager",
        class_name="TaskManager",
        sessions=frozenset({"real"}),
        show_on_desktop=False,
    ),
    AppDefinition(
        name="Security",
        emoji="🔒",
        module="security_panel",
        class_name="SecurityPanel",
        icon_asset="icon-security.svg",
        sessions=frozenset({"real"}),
        show_on_desktop=False,
    ),
    AppDefinition(
        name="Network",
        emoji="📡",
        module="network_tools",
        class_name="NetworkTools",
        icon_asset="icon-network.svg",
        show_on_desktop=False,
    ),
    AppDefinition(
        name="Vault",
        emoji="🔐",
        module="vault_tool",
        class_name="VaultTool",
        icon_asset="icon-vault.svg",
        sessions=frozenset({"real"}),
        show_on_desktop=False,
    ),
    AppDefinition(
        name="Core",
        emoji="⚛️",
        module="core_app",
        class_name="QVaultCoreApp",
        sessions=frozenset({"real"}),
        show_on_desktop=False,
    ),
    AppDefinition(
        name="Storage",
        emoji="💾",
        module="storage_view",
        class_name="StorageView",
        show_on_desktop=False,
    ),
    AppDefinition(
        name="Settings",
        emoji="⚙️",
        module="settings_app",
        class_name="SettingsApp",
    ),
)


def apps_for_session(session_type: str) -> list[AppDefinition]:
    active_session = "fake" if session_type == "fake" else "real"
    return [app for app in APP_DEFINITIONS if active_session in app.sessions]
