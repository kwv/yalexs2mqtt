# Contributing to **yalexs2mqtt**

Thanks for your interest in contributing to **yalexs2mqtt**!
This guide explains how to develop, build, test, and release new versions of the project.

------------------------------------------------------------------------

## 🛠️ Development Setup

### 1. Clone the Repository

``` sh
git clone https://github.com/kwv4/yalexs2mqtt.git
cd yalexs2mqtt
```

### 2. Local Development

``` sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio flake8
```

### 3. Linting and Testing

``` sh
# Run lint (E9, F63, F7, F82 checks)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Run tests
pytest
```

------------------------------------------------------------------------

## 🚀 Releasing a New Version

The project uses **Git tags** to trigger automated Docker image builds and releases.

### Steps to Publish a New Version

1.  Ensure your changes are committed to `main`.
2.  Tag the commit with a semantic version (e.g., `v1.2.3`):
    ``` sh
    git tag v1.2.3
    git push origin v1.2.3
    ```

### 🤖 CI/CD Automation

The GitHub Actions workflow triggers on every push and pull request:

- **Push to main / PRs**: Runs `pytest` and `flake8` linting.
- **Tag Push**: Decodes the version from the tag, runs tests, and then builds and publishes the multi-arch Docker image:
    - `kwv4/yalexs2mqtt:v1.2.3`
    - `kwv4/yalexs2mqtt:latest`

### 🧹 Tag Cleanup
The repository contains a weekly automated cleanup job (`docker-cleanup.yml`) that:
- Synchronizes Git tags and Docker Hub tags.
- Keeps the `latest` tag and the most recent semantic version tags (configured via `KEEP_RECENT`).
- Removes orphaned or old version tags from both systems.

------------------------------------------------------------------------

## 🧪 Testing Locally with Docker

To test the image before publishing:

``` sh
docker build -t yalexs2mqtt:test .
docker run --rm -v $(pwd)/config:/config yalexs2mqtt:test
```

------------------------------------------------------------------------

## 🔄 Contribution Workflow

1. Create a branch for your changes (e.g., `feature/name` or `bugfix/name`).
2. Commit your changes.
3. Open a pull request (PR) targeting the `main` branch.
4. Ensure your PR includes a clear description.

------------------------------------------------------------------------

## 🧩 Required Secrets for CI

Add these secrets in your GitHub repository settings:

| Secret Name | Value |
|-------------|-------|
| `DOCKERHUB_USER` | `kwv4` |
| `DOCKERHUB_TOKEN` | *Docker Hub access token* |

------------------------------------------------------------------------

## 💬 Questions?

Feel free to open an issue or start a discussion if you have questions or suggestions.
We welcome contributions of all kinds!
