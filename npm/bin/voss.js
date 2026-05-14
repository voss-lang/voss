#!/usr/bin/env node
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const PLATFORMS = {
  darwin: {
    arm64: '@vosslang/cli-darwin-arm64',
    x64: '@vosslang/cli-darwin-x64',
  },
  linux: {
    arm64: '@vosslang/cli-linux-arm64',
    x64: '@vosslang/cli-linux-x64',
  },
  win32: {
    x64: '@vosslang/cli-win32-x64',
  },
};

const SIGNAL_EXIT_CODES = {
  SIGINT: 130,
  SIGTERM: 143,
};

function findPlatformPackage() {
  const platform = process.platform;
  const arch = process.arch;
  const pkg = PLATFORMS[platform] && PLATFORMS[platform][arch];
  if (!pkg) {
    process.stderr.write(
      'voss: unsupported platform: ' + platform + ' ' + arch + '\n'
    );
    process.exit(1);
  }
  try {
    const manifestPath = require.resolve(pkg + '/package.json');
    return { pkg, pkgDir: path.dirname(manifestPath) };
  } catch (e) {
    process.stderr.write(
      'voss: platform package ' + pkg + ' not installed.\n' +
      'Try: npm install ' + pkg + '\n'
    );
    process.exit(1);
  }
}

const { pkg, pkgDir } = findPlatformPackage();
const isWindows = process.platform === 'win32';

function resolvePythonBin() {
  if (isWindows) {
    return path.join(pkgDir, 'python', 'python.exe');
  }
  // npm publish drops symlinks, so the canonical `bin/python3` is missing
  // from the published tarball even though PBS extracts contain it as a
  // symlink to python3.12. Try the canonical name first (works for
  // dev / `npm link` flows), then fall back to python3.12.
  const candidates = [
    path.join(pkgDir, 'python', 'bin/python3'),
    path.join(pkgDir, 'python', 'bin/python3.12'),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) {
      return c;
    }
  }
  return candidates[0];
}

const pythonBin = resolvePythonBin();

if (!fs.existsSync(pythonBin)) {
  process.stderr.write(
    'voss: vendored Python not found at ' + pythonBin + '\n'
  );
  process.exit(1);
}

const result = spawnSync(
  pythonBin,
  ['-m', 'voss.cli', ...process.argv.slice(2)],
  { shell: false, stdio: 'inherit', env: process.env }
);

if (result.error) {
  throw result.error;
}
if (result.signal) {
  process.exitCode = SIGNAL_EXIT_CODES[result.signal] || 128;
} else {
  process.exitCode = result.status;
}
