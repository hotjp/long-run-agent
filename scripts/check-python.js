#!/usr/bin/env node

/**
 * Post-install script for long-run-agent npm package
 * Checks for Python installation and provides installation instructions
 */

const { execSync } = require('child_process');

console.log('\n📦 LRA - Long-Running Agent\n');
console.log('This npm package is a wrapper for the Python CLI.');
console.log('To use LRA, please install the Python package:\n');
console.log('  pip install long-run-agent\n');
console.log('Or with pipx:\n');
console.log('  pipx install long-run-agent\n');

// Check for Python
const pythonCommands = ['python3', 'python'];
let pythonFound = false;

for (const cmd of pythonCommands) {
  try {
    execSync(`${cmd} --version`, { stdio: 'pipe' });
    pythonFound = true;
    console.log(`✅ Python found: ${cmd}`);
    break;
  } catch (e) {
    // Continue
  }
}

if (!pythonFound) {
  console.log('⚠️  Python 3.8+ is required but not found.');
  console.log('   Please install Python: https://www.python.org/downloads/\n');
}

console.log('After installing the Python package, run:\n');
console.log('  lra --help\n');
