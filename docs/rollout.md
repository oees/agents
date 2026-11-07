# Rolling out `oees-agents`

How the installer reaches every OEES repository: one pilot per kit, a week of
real use, feedback folded back into the kits, then the rest. Source: Task 4.3 of
[the restructure plan](plans/2026-11-07-restructure-agents-repo.md).

## Before the pilot

- Phases 1 to 4.1 are merged to `main` and `make check` passes there.
- `v1.0.0` is tagged on `main` and the release workflow has run green: the
  `check` job passed and `@oees/agents` is published pinned to `v1.0.0`.
- From a scratch directory, all three entry points reach the same CLI:

  ```bash
  uvx --from git+https://github.com/oees/agents@v1.0.0 oees-agents list
  ```

  ```bash
  npx @oees/agents list
  ```

  ```bash
  bash <(curl -fsSL https://raw.githubusercontent.com/oees/agents/main/scripts/bootstrap.sh) --help
  ```

## Pilot: one repository per kit

| Repository | Kits | Why it pilots |
|---|---|---|
| `hermes` | `fastapi` | API-only middleware; exercises the FastAPI kit and outbound HTTP |
| `franklin` | `django-drf`, `htmx-alpine` | Server-rendered Django; exercises both Django-side kits together |

For each pilot repository:

1. Branch from the default branch: `git switch -c adopt-oees-agents`.
2. Run `init` from the repository root. Where the repository carries a
   pre-manifest install, `init` takes the legacy path: it builds a manifest
   from what is present, asks only the context questions, removes the files it
   can prove came from this repo and lists everything it kept.

   ```bash
   uvx --from git+https://github.com/oees/agents@v1.0.0 oees-agents init
   ```

3. Answer the context questions with the owning team, not alone. The
   description, users and blast radius are what every agent calibrates to.
4. Review what the legacy path kept, if it ran. Local text outside managed blocks stays;
   anything listed as kept but not recognised is either project guidance (leave
   it) or a stale copy (delete it in its own commit with a reason).
5. Record every opt-out in the manifest with a one-line reason (see
   [Opt-out convention](#opt-out-convention)).
6. Run the project's own checks, then `oees-agents check` to confirm the
   generated files are current.
7. Commit the manifest, the lock and the generated files in one commit, and
   open a PR for the team to review:

   ```bash
   git add .oees-agents.toml .oees-agents.lock AGENTS.md .claude/ .cursor/
   git commit -m "Adopt oees-agents v1.0.0"
   ```

8. Add `oees-agents check` to the repository's CI so stale generated files fail
   the build.

### The pilot week

Work in the pilot repositories with Claude Code, Cursor and Codex for a week of
ordinary tickets. Keep one running note per repository (an issue in this repo
labelled `pilot`) and record, as they happen:

- instructions an agent ignored, misread or followed when it should not have;
- kit guidance that did not match how the repository actually works;
- generated settings that blocked a routine command or allowed a risky one;
- questions in `init` that were unclear or that the team answered differently
  on reflection;
- anything `update` or `check` did that surprised someone.

### Folding the feedback back

At the end of the week, triage each note into one of:

- **Kit change**: fix it in `content/kits/<kit>/`, one commit per finding.
- **Default or conduct change**: fix it in `content/defaults/` or
  `content/conduct/`; a change to conduct needs the owner's sign-off.
- **Installer change**: a failing test first, then the fix in `src/oees_agents/`.
- **Project-specific**: belongs in that repository's own instructions outside
  the managed blocks, or as a recorded opt-out. No change here.

Tag a release with the fixes (`v1.1.0` or a patch), then run
`oees-agents update --ref <new tag>` in both pilots and check the diff contains
only the expected changes. The pilot is done when both pilot repositories are on
the new tag and their open notes are resolved or deliberately deferred with an
issue.

## Migrating the rest

Order by risk, lowest blast radius first, so problems surface where they cost
least: internal tools, then customer-facing services, then anything regulated.
The order below is a suggestion; confirm each blast radius with the owning
team before starting.

| Repository | Kits |
|---|---|
| `octopanel` | none |
| `vercel-deployer` | none |
| `bill-e` | `fastapi` |
| `consumer-site-embeds` | `fastapi` |
| `octohub` | `django-drf` |
| `octosentinel` | `django-drf` |

For each, repeat pilot steps 1 to 8 against the latest tag. A repository with no
kit still gets conduct, the defaults it keeps, skills and the extras it picks.
One PR per repository; the owning team reviews and merges it.

Track progress in a single issue in this repo with one checkbox per
repository, each linking its adoption PR.

## Opt-out convention

A project keeps every default unless it has a reason not to, and the reason
lives next to the decision. Remove the default from `[rules] defaults` and put a
one-line `#` comment directly above the `defaults` line naming what was removed
and why:

```toml
[rules]
# migrations: no database; this service is stateless
defaults = ["tdd", "git", "observability", "api", "standards", "quality-gates"]
```

The same applies to a kit or extra a team turns off after trying it:

```toml
[extras]
commands = true
# subagents: none until the team has reviewed the core set (issue #123)
subagents = "none"
loops = []
```

Rules for the comment:

- One line per opted-out item, starting with the item's name and a colon.
- The reason says why this project differs, not that the rule is unwanted.
- A temporary opt-out links the issue that will remove it, matching the
  tracked-debt rule in [CONTRIBUTING.md](../CONTRIBUTING.md).
- Conduct (`conduct`, `secrets`) cannot be opted out.

Then run `oees-agents update` so the generated files drop the rule, and commit
the manifest and the generated diff together.

When the same opt-out appears in three or more repositories, raise it here: the
default is probably wrong for OEES, not for those projects.
