#!/usr/bin/env node

/**
 * LRA - Long-Running Agent CLI wrapper
 * This script provides a Node.js entry point that calls the Python CLI
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Try to find python3 or python
function findPython() {
  const pythonCommands = ['python3', 'python'];

  for (const cmd of pythonCommands) {
    try {
      const result = require('child_process').spawnSync(cmd, ['--version'], { encoding: 'utf8' });
      if (result.status === 0) {
        return cmd;
      }
    } catch (e) {
      // Continue to next option
    }
  }

  return 'python3'; // Default fallback
}

const python = findPython();

// Get the package directory (where package.json is)
const packageDir = path.resolve(__dirname, '..');
const pythonPackageDir = path.join(packageDir, 'long_run_agent');

// Check if Python package exists locally
const args = process.argv.slice(2);

let child;

if (fs.existsSync(pythonPackageDir)) {
  // Run from local Python package
  child = spawn(python, [path.join(pythonPackageDir, 'cli.py'), ...args], {
    stdio: 'inherit',
    env: { ...process.env, PYTHONPATH: packageDir },
    cwd: process.cwd()
  });
} else {
  // Try to run from installed Python package
  child = spawn(python, ['-m', 'long_run_agent', ...args], {
    stdio: 'inherit',
    env: { ...process.env }
  });
}

child.on('close', (code) => {
  process.exit(code || 0);
});

child.on('error', (err) => {
  console.error('❌ Failed to start LRA:', err.message);
  console.error('\nPlease ensure Python 3.8+ is installed and accessible.');
  console.error('Install LRA with: pip install long-run-agent');
  process.exit(1);
});
