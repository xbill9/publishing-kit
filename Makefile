# Root Makefile for the publishing kit.
#
# There is no test suite: the regression test is the kit run against its own
# dogfood article (see CLAUDE.md, "Verifying a change").

SKILL_NAME := publishing
SKILL_DIR  := skills/$(SKILL_NAME)
SCRIPTS    := $(SKILL_DIR)/scripts
DOGFOOD    := articles/publishing-kit-skill/devto-publishing-kit.md
DIST_DIR   := dist

.PHONY: all help lint test live pinned manifest footprint install skill-install skill-package clean

all: help

help:
	@echo "========================================================="
	@echo " Publishing Kit - Root Makefile"
	@echo "========================================================="
	@echo "Available commands:"
	@echo "  make lint          - ruff on scripts/, node --check on browser helpers,"
	@echo "                       bash -n on hooks, manifest copy check"
	@echo "  make test          - preflight against the dogfood article (local state only)"
	@echo "  make live          - preflight --live: fetch published URLs, compare to disk"
	@echo "  make pinned        - preflight --live --pinned: resolve at HEAD's sha"
	@echo "  make manifest      - fail if root plugin.json differs from .claude-plugin/plugin.json"
	@echo "  make footprint     - print the skill's line counts and token cost"
	@echo "  make install       - reinstall the $(SKILL_NAME)@publishing-kit plugin from the"
	@echo "                       working tree (no version bump needed)"
	@echo "  make skill-install - copy $(SKILL_DIR) to ~/.claude/skills/$(SKILL_NAME)"
	@echo "  make skill-package - build $(DIST_DIR)/$(SKILL_NAME)-skill.zip"
	@echo "  make clean         - remove $(DIST_DIR)/, __pycache__ and .ruff_cache"
	@echo "========================================================="

lint: manifest
	@command -v ruff >/dev/null || { echo "ruff not found; install with: pip install ruff"; exit 1; }
	ruff check $(SCRIPTS)
	@command -v node >/dev/null && for f in $(SCRIPTS)/browser/*.js; do node --check $$f || exit 1; done \
		|| echo "node not found; skipped browser helper syntax check"
	@for s in .claude/hooks/*.sh; do bash -n $$s || exit 1; done
	@echo "lint OK"

test:
	python3 $(SCRIPTS)/preflight.py $(DOGFOOD)

live:
	python3 $(SCRIPTS)/preflight.py $(DOGFOOD) --live

pinned:
	python3 $(SCRIPTS)/preflight.py $(DOGFOOD) --live --pinned

# The root plugin.json is a generated copy (a PostToolUse hook keeps it in step).
manifest:
	@cmp -s .claude-plugin/plugin.json plugin.json \
		|| { echo "plugin.json differs from .claude-plugin/plugin.json; run: cp .claude-plugin/plugin.json plugin.json"; exit 1; }

footprint:
	python3 $(SCRIPTS)/skill-footprint.py

# The plugin is installed from this directory as a marketplace. `claude plugin
# update` compares version numbers only, so an edit without a version bump never
# reaches the installed copy; uninstall + install snapshots the working tree every
# time. skill-install is the plain-copy route for hosts without the plugin; using
# both loads the skill twice.
install: manifest
	claude plugin validate .
	claude plugin marketplace update publishing-kit
	-claude plugin uninstall --keep-data --scope user $(SKILL_NAME)@publishing-kit
	claude plugin install --scope user $(SKILL_NAME)@publishing-kit

skill-install:
	mkdir -p $(HOME)/.claude/skills
	rm -rf $(HOME)/.claude/skills/$(SKILL_NAME)
	cp -r $(SKILL_DIR) $(HOME)/.claude/skills/$(SKILL_NAME)
	find $(HOME)/.claude/skills/$(SKILL_NAME) -name __pycache__ -type d -prune -exec rm -rf {} +
	@echo "Installed to $(HOME)/.claude/skills/$(SKILL_NAME)"

# zip is not assumed installed; python3 -m zipfile is.
skill-package:
	mkdir -p $(DIST_DIR)
	rm -f $(DIST_DIR)/$(SKILL_NAME)-skill.zip
	find $(SKILL_DIR) -name __pycache__ -type d -prune -exec rm -rf {} +
	cd skills && python3 -m zipfile -c $(CURDIR)/$(DIST_DIR)/$(SKILL_NAME)-skill.zip $(SKILL_NAME)
	@echo "Packaged $(DIST_DIR)/$(SKILL_NAME)-skill.zip"
	@python3 -m zipfile -l $(DIST_DIR)/$(SKILL_NAME)-skill.zip

clean:
	rm -rf $(DIST_DIR) .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
