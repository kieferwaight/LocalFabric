"""Immutable snapshot of the invoking shell environment."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ShellEnvironment:
    cwd: str = field(default_factory=os.getcwd)
    cmd: str = field(default_factory=lambda: os.path.abspath(sys.argv[0]) if sys.argv else "")
    env: Dict[str, str] = field(default_factory=lambda: dict(os.environ))
    args: List[str] = field(default_factory=list)
    options: Dict[str, str] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_argv(cls, argv: List[str]) -> "ShellEnvironment":
        """Parse `argv` (positional args, --key=value options, --flag/-f flags).

        `argv` should be the slice AFTER yaml_file and definition_id are stripped.
        """
        args: List[str] = []
        options: Dict[str, str] = {}
        flags: Dict[str, bool] = {}
        for tok in argv:
            if tok.startswith("--") and "=" in tok:
                key, _, val = tok[2:].partition("=")
                options[key] = val
            elif tok.startswith("--"):
                flags[tok[2:]] = True
            elif tok.startswith("-") and len(tok) > 1 and not tok[1:].isdigit():
                flags[tok[1:]] = True
            else:
                args.append(tok)
        return cls(
            cwd=os.getcwd(),
            cmd=os.path.abspath(sys.argv[0]) if sys.argv else "",
            env=dict(os.environ),
            args=args,
            options=options,
            flags=flags,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cwd": self.cwd,
            "cmd": self.cmd,
            "env": dict(self.env),
            "args": list(self.args),
            "options": dict(self.options),
            "flags": dict(self.flags),
        }
