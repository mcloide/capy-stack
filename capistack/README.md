# CapiStack

A lightweight Python CI/CD web application for deploying applications from Git repositories via a browser interface.

---

## TL;DR

**CapiStack** is a self-hosted CI/CD platform that keeps things simple, secure, and transparent. It deploys a single app from a Git repo (GitHub, GitLab, or any Git server) to your servers with minimal config. Built with *Python + Flask + SQLAlchemy + RQ*, using a straightforward pipeline: `checkout → build → deploy → post-deploy`.

In plain terms, it’s an over-glorified `git pull` with a web UI, auth, and logs. And yes—the mascot is a cute capybara my youngest picked. 🫶

### Why another CI/CD?

Using Jenkins to ship a tiny service is overkill. Most other tools felt too complex, too heavy, or too opaque. I wanted a “pick a branch → deploy → see logs” workflow. Also, I was a little bored.

### What it doesn’t do (yet)

- Multi-repo or multi-app orchestration (it’s intentionally single-app for now).
- Server-to-server “promote host A → host B” flows.

It’s open-source and evolving. If it helps you as much as it helps me, awesome. Run the setup, kick the tires, and if you hit a bug or have an idea, please open an issue or PR.

---

## Features

- **Simple Deployment**: Select a branch, tag, or release and deploy with one click
- **Live Progress**: Watch deployment progress with real-time logs via Server-Sent Events
- **Multiple Auth Modes**: None, Basic Auth, or OAuth (GitHub, GitLab, OIDC)
- **Database Support**: PostgreSQL or MySQL with encrypted secrets storage
- **Background Processing**: RQ-based job queue for reliable deployment execution
- **Git Integration**: Support for GitHub, GitLab, and generic Git repositories
- **Retention Policy**: Automatic cleanup of old deployments
- **Modern UI**: Bootstrap-based responsive web interface

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd capistack
   cp env.example .env
