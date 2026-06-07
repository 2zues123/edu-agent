from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_RESTORED_PYC = Path(__file__).with_name("_chat_workspace_restored.cpython-310.pyc")
_MODULE_NAME = "_edu_agent_restored_chat_workspace"

_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _RESTORED_PYC)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load restored chat workspace from {_RESTORED_PYC}")

_module = importlib.util.module_from_spec(_spec)
sys.modules[_MODULE_NAME] = _module
_spec.loader.exec_module(_module)

for _name, _value in vars(_module).items():
    if _name in {"__builtins__", "__cached__", "__file__", "__loader__", "__name__", "__package__", "__spec__"}:
        continue
    globals()[_name] = _value

__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__":
    main()
