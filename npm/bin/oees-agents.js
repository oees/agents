#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

// The release workflow sets the package version from the git tag, so the version is the pin.
const TAG = `v${require('../package.json').version}`;

const UV_INSTALL =
  process.platform === 'win32'
    ? 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
    : 'curl -LsSf https://astral.sh/uv/install.sh | sh';

function isExecutable(file) {
  try {
    fs.accessSync(file, fs.constants.X_OK);
    return fs.statSync(file).isFile();
  } catch {
    return false;
  }
}

function findOnPath(name) {
  const extensions =
    process.platform === 'win32' ? ['', ...(process.env.PATHEXT || '.EXE').split(';')] : [''];
  const dirs = (process.env.PATH || '').split(path.delimiter).filter(Boolean);
  for (const dir of dirs) {
    for (const ext of extensions) {
      const candidate = path.join(dir, name + ext);
      if (isExecutable(candidate)) return candidate;
    }
  }
  return null;
}

const uvx = findOnPath('uv') && findOnPath('uvx');
if (!uvx) {
  console.error(`oees-agents needs uv. Install it with: ${UV_INSTALL}`);
  process.exit(1);
}

const result = spawnSync(
  uvx,
  ['--from', `git+https://github.com/oees/agents@${TAG}`, 'oees-agents', ...process.argv.slice(2)],
  { stdio: 'inherit' },
);

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
if (result.signal) {
  process.kill(process.pid, result.signal);
}
process.exit(result.status);
