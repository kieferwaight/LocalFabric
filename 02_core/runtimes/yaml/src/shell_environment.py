"""Immutable snapshot of the invoking shell environment."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ShellEnvironment:
    cwd: str = field(default_factory=os.getcwd)
    cmd: str = field(default_factory=lambda: os.path.abspath(sys.argv[0]) if sys.argv else "")
    env: dict[str, str] = field(default_factory=lambda: dict(os.environ))
    args: list[str] = field(default_factory=list)
    options: dict[str, str] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_argv(cls, argv: list[str]) -> ShellEnvironment:
        """Parse `argv` (positional args, --key=value options, --flag/-f flags).

        `argv` should be the slice AFTER yaml_file and definition_id are stripped.
        """
        args: list[str] = []
        options: dict[str, str] = {}
        flags: dict[str, bool] = {}
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "cwd": self.cwd,
            "cmd": self.cmd,
            "env": dict(self.env),
            "args": list(self.args),
            "options": dict(self.options),
            "flags": dict(self.flags),
        }
