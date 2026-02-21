<div align="center">

# LRA - Long-Running Agent Tool

**A powerful framework for managing long-running AI Agent tasks**

Based on best practices from Anthropic's paper [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#)

**English | [中文](README.md)**

</div>

---

> This is the English version of the documentation. For the complete bilingual documentation with all features, CLI reference, and usage examples, please see [README.md](README.md#english).

## Quick Overview

LRA is a command-line tool that helps manage long-running AI agent development tasks with:

- 🔄 **Auto-upgrade** - Seamless version migration with backup
- 📋 **Feature status workflow** - 7 states with transition validation
- 📝 **Requirements management** - Templates and validation
- 📊 **Code change tracking** - Per-feature records with Git integration
- 📜 **Operation audit logs** - Complete traceability
- 🔧 **Multi-language code checking** - Python, JavaScript, Go

## Installation

```bash
git clone https://github.com/your-username/long-run-agent.git
cd long-run-agent
./lra version
```

## Quick Start

```bash
# Initialize in your project
cd /path/to/your/project
lra project create my-project

# Create a feature
lra feature create "User Login" --category backend --priority P0

# Manage status
lra feature status feature_001 --set in_progress

# Check code
lra code check src/ --verbose

# View statistics
lra stats
```

## Documentation

Full documentation with CLI reference, status flow diagrams, and best practices is available in the [main README](README.md#english).

## License

MIT License
