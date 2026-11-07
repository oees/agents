# @oees/agents

A thin wrapper around the `oees-agents` Python CLI, which installs the shared OEES agent configuration into a project. This package contains no logic of its own: it finds `uv` and runs the real CLI through `uvx`.

## Requirement

[uv](https://docs.astral.sh/uv/). If it is missing, the wrapper prints the install command and exits; it never installs anything itself.

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Usage

```sh
npx @oees/agents init
```

All arguments are passed through unchanged.

## Version pinning

Each release of this package runs the CLI from the git tag matching its version, so `@oees/agents@1.2.0` runs tag `v1.2.0`. The equivalent direct command is:

```sh
uvx --from git+https://github.com/oees/agents@<tag> oees-agents init
```
