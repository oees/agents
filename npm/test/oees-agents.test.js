'use strict';

const { test, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { version } = require('../package.json');

const BIN = path.join(__dirname, '..', 'bin', 'oees-agents.js');

let tmp;
let argvFile;

function writeExecutable(dir, name, body) {
  const file = path.join(dir, name);
  fs.writeFileSync(file, `#!/bin/sh\n${body}\n`);
  fs.chmodSync(file, 0o755);
}

function runBin(args, env) {
  return spawnSync(process.execPath, [BIN, ...args], {
    encoding: 'utf8',
    env: { ...env, FAKE_UVX_ARGV_FILE: argvFile },
  });
}

beforeEach(() => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'oees-agents-test-'));
  argvFile = path.join(tmp, 'uvx-argv');
});

afterEach(() => {
  fs.rmSync(tmp, { recursive: true, force: true });
});

function fakeUvDir() {
  const dir = path.join(tmp, 'with-uv');
  fs.mkdirSync(dir);
  writeExecutable(dir, 'uv', 'exit 0');
  writeExecutable(
    dir,
    'uvx',
    'printf "%s\\n" "$@" > "$FAKE_UVX_ARGV_FILE"\nexit "${FAKE_UVX_EXIT_CODE:-0}"',
  );
  return dir;
}

test('passes the pinned tag and every user argument to uvx', () => {
  const result = runBin(['init', '--yes', '--kit', 'fastapi', 'a b'], {
    PATH: fakeUvDir(),
  });

  assert.equal(result.status, 0, result.stderr);
  const argv = fs.readFileSync(argvFile, 'utf8').split('\n').slice(0, -1);
  assert.deepEqual(argv, [
    '--from',
    `git+https://github.com/oees/agents@v${version}`,
    'oees-agents',
    'init',
    '--yes',
    '--kit',
    'fastapi',
    'a b',
  ]);
});

test('exits with the exit code of uvx', () => {
  const result = runBin(['init'], { PATH: fakeUvDir(), FAKE_UVX_EXIT_CODE: '3' });

  assert.equal(result.status, 3);
});

test('prints the uv install command and exits 1 when uv is missing', () => {
  const emptyDir = path.join(tmp, 'without-uv');
  fs.mkdirSync(emptyDir);
  writeExecutable(
    emptyDir,
    'uvx',
    'printf "%s\\n" "$@" > "$FAKE_UVX_ARGV_FILE"',
  );

  const result = runBin(['init'], { PATH: emptyDir });

  assert.equal(result.status, 1);
  assert.match(result.stderr, /https:\/\/astral\.sh\/uv\/install/);
  assert.equal(fs.existsSync(argvFile), false);
});
