# =============================================================
#  tools/generate_plugin.py — Q-Vault OS  |  Decoupled Boilerplate
#
#  Generates architecturally compliant plugins:
#  - Logic Engine in apps/
#  - UI Component in components/
# =============================================================

import sys
import os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/generate_plugin.py <plugin_name>")
        sys.exit(1)

    name = sys.argv[1].lower()
    if not name.isidentifier():
        print("Error: name must be a valid Python identifier.")
        sys.exit(1)

    # Class name from snake_case
    class_name = "".join(word.capitalize() for word in name.split("_"))

    templates_dir = Path(__file__).parent / "templates"
    engine_tpl = (templates_dir / "engine.py.tpl").read_text("utf-8")
    ui_tpl = (templates_dir / "ui.py.tpl").read_text("utf-8")

    # 1. Generate Engine
    engine_path = Path(f"apps/{name}_engine.py")
    engine_content = engine_tpl.replace("{{name}}", name).replace("{{className}}", class_name)
    engine_path.write_text(engine_content, "utf-8")

    # 2. Generate UI
    ui_path = Path(f"components/{name}_ui.py")
    ui_content = ui_tpl.replace("{{name}}", name).replace("{{className}}", class_name)
    ui_path.write_text(ui_content, "utf-8")

    print(f"🚀 Plugin '{name}' generated successfully!")
    print(f"   [Logic] {engine_path}")
    print(f"   [UI]    {ui_path}")
    print("\nNext Steps:")
    print(f"   1. Initialize engine in main.py or PluginManager.")
    print(f"   2. Register UI in core/app_registry.py using {class_name}UI.")

if __name__ == "__main__":
    main()
