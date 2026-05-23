# YAML Examples

These YAML examples are runnable composed workflows built from the standard
library. Run the commands from `20_workspaces/06_workflows/yaml/`.

## Obsidian Template

Create a starter template beneath an Obsidian vault folder:

```bash
python interpreter.py examples/obsidian-template.yaml example/obsidian-template \
  --obsidian_folder="$HOME/Documents/My Vault"
```

This writes `Templates/daily-note.md` below the supplied folder. Override its
name with `--template_name=meeting.md`.

## Git In The Current Workspace

Initialize the current directory as a Git repository and add a Python-oriented
`.gitignore`:

```bash
python interpreter.py examples/git-current-workspace.yaml example/git/init
```

To additionally create a GitHub repository through authenticated `gh`:

```bash
python interpreter.py examples/git-current-workspace.yaml example/git/github \
  --repository_name=owner/project-name --visibility=private
```

The GitHub routine creates an `origin` remote but does not create a commit or
push work automatically.

## Gitignore Template

Write only the reusable `.gitignore` template in the current directory:

```bash
python interpreter.py examples/gitignore-template.yaml example/git/gitignore
```
