DOCKERHUB_USER ?= kwv4
IMAGE_NAME ?= yalexs2mqtt
# VERSION is the strict, exact tag for releases
VERSION ?= $(shell git describe --tags --exact-match 2>/dev/null | sed 's/^v//' || git tag -l 'v*' | sort -V | tail -n1 | sed 's/^v//')

# DEV_VERSION gets a descriptive version for local builds (e.g., "1.2.3-1-gabcdef-dirty")
# Falls back to "local-dev" if no tags exist
DEV_VERSION := $(shell git describe --tags --dirty --always 2>/dev/null | sed 's/^v//' || echo "local-dev")

REMOTE_IMAGE := $(DOCKERHUB_USER)/$(IMAGE_NAME)

.PHONY: build build-dev tag push clean release test check-version show-version check-tag bump bump-minor bump-major

test:
	# Run tests using the virtual environment
	./venv/bin/pytest

# New target for local development builds
build-dev:
	@echo "Building dev image: $(IMAGE_NAME):$(DEV_VERSION)"
	docker build -t $(IMAGE_NAME):$(DEV_VERSION) .

# 🚀 New target: bump the version, create a new tag, and push it
bump:
	$(call bump_version,patch)

bump-minor:
	$(call bump_version,minor)

bump-major:
	$(call bump_version,major)

check-version:
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ No Git tag found. Please tag your commit (e.g., git tag v1.2.3)"; \
		exit 1; \
	else \
		echo "✅ Using version: $(VERSION)"; \
	fi
show-version:
	@echo "Release VERSION: $(VERSION)"
	@echo "Dev VERSION: $(DEV_VERSION)"

check-tag:
	@command -v jq >/dev/null || { echo "❌ jq is required"; exit 1; }
	@command -v curl >/dev/null || { echo "❌ curl is required"; exit 1; }
	@echo "🔍 Checking if Docker tag $(VERSION) already exists..."
	@TAG_EXISTS=$$(curl -s https://hub.docker.com/v2/repositories/$(REMOTE_IMAGE)/tags/$(VERSION)/ | jq -r '.name // empty'); \
	if [ "$$TAG_EXISTS" = "$(VERSION)" ]; then \
		echo "❌ Tag $(VERSION) already exists on Docker Hub. Aborting."; \
		exit 1; \
	else \
		echo "✅ Tag $(VERSION) is available."; \
	fi

# This 'build' is part of the 'release' pipeline and must use the strict VERSION
build:
	docker build -t $(IMAGE_NAME):$(VERSION) .

tag:
	docker tag $(IMAGE_NAME):$(VERSION) $(REMOTE_IMAGE):$(VERSION)
	docker tag $(IMAGE_NAME):$(VERSION) $(REMOTE_IMAGE):latest

push:
	docker push $(REMOTE_IMAGE):$(VERSION)
	docker push $(REMOTE_IMAGE):latest

clean:
	-docker rmi $(IMAGE_NAME):$(VERSION) || true
	-docker rmi $(REMOTE_IMAGE):$(VERSION) || true
	-docker rmi $(REMOTE_IMAGE):latest || true
	# Also clean up the dev image
	-docker rmi $(IMAGE_NAME):$(DEV_VERSION) || true


release: check-version check-tag test build tag push clean


define bump_version
	@LATEST_TAG=$$(git tag -l 'v*' | sort -V | tail -n1); \
	if [ -z "$$LATEST_TAG" ]; then \
		echo "❌ No existing tags found. Please create an initial tag first (e.g., git tag v1.0.0)"; \
		exit 1; \
	fi; \
	CURRENT_VERSION=$$(echo $$LATEST_TAG | sed 's/^v//'); \
	MAJOR=$$(echo $$CURRENT_VERSION | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT_VERSION | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT_VERSION | cut -d. -f3); \
	if [ "$(1)" = "patch" ]; then \
		NEW_MAJOR=$$MAJOR; \
		NEW_MINOR=$$MINOR; \
		NEW_PATCH=$$(expr $$PATCH + 1); \
	elif [ "$(1)" = "minor" ]; then \
		NEW_MAJOR=$$MAJOR; \
		NEW_MINOR=$$(expr $$MINOR + 1); \
		NEW_PATCH=0; \
	elif [ "$(1)" = "major" ]; then \
		NEW_MAJOR=$$(expr $$MAJOR + 1); \
		NEW_MINOR=0; \
		NEW_PATCH=0; \
	fi; \
	NEW_VERSION=$$NEW_MAJOR.$$NEW_MINOR.$$NEW_PATCH; \
	NEW_TAG=v$$NEW_VERSION; \
	echo "Incrementing version from $$LATEST_TAG to $$NEW_TAG"; \
	git tag -a $$NEW_TAG -m "Bumped version to $$NEW_TAG"; \
	git push origin $$NEW_TAG
endef
