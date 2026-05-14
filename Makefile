.PHONY: setup install install-dev install-gpu install-remotion test test-contracts genui-verify lint clean preflight preflight-full demo demo-list hyperframes-doctor hyperframes-warm

# ---- One-command setup ----

setup:
	@echo "==> Installing Python dependencies..."
	pip install -r requirements.txt
	@echo ""
	@echo "==> Installing Remotion composer..."
	$(MAKE) install-remotion
	@echo ""
	@echo "==> Installing free offline TTS (Piper)..."
	pip install piper-tts || echo "  [skip] piper-tts install failed — TTS will use cloud providers instead"
	@echo ""
	@echo "==> Installing HyperFrames runtime (cache-warm via npx)..."
	@echo "    Pulls the 'hyperframes' npm package into the local npx cache so the"
	@echo "    first render doesn't pay a 30-60s cold-fetch penalty. ~20MB of disk."
	@npx --yes hyperframes --version >/dev/null 2>&1 && echo "    HyperFrames CLI cached (npx)" || echo "  [skip] HyperFrames cache-warm failed — offline or npm unavailable; first render will fetch on demand"
	@python -c "from tools.video.hyperframes_compose import HyperFramesCompose; HyperFramesCompose._npm_resolve_cache=None; c=HyperFramesCompose()._runtime_check(); print(f'    HyperFrames runtime_available={c[\"runtime_available\"]}, npm={c.get(\"npm_package_version\") or c.get(\"npm_resolve_error\")}'); [print(f'    note: {r}') for r in c['reasons']]" || echo "  [skip] HyperFrames check failed — runtime can be set up later"
	@echo ""
	python -c "import shutil, os; e=os.path.exists('.env'); shutil.copy('.env.example','.env') if not e else None; print('==> Created .env from .env.example — add your API keys there.' if not e else '==> .env already exists — skipping.')"
	@echo ""
	@echo "Done! Open this project in your AI coding assistant and start creating."
	@echo "  Optional: add API keys to .env to unlock cloud providers."
	@echo "  Optional: run 'make install-gpu' if you have an NVIDIA GPU."
	@echo "  Optional: run 'make hyperframes-doctor' to fully validate the HyperFrames runtime."
	@echo "  Optional: run 'make hyperframes-warm' anytime to refresh the npx cache to the latest hyperframes version."

# ---- Individual installs ----

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

install-gpu:
	pip install -r requirements-gpu.txt
	pip install diffusers transformers accelerate

install-remotion:
	@if [ -f remotion-composer/pnpm-lock.yaml ]; then \
		echo "Using pnpm-lock.yaml for Remotion dependencies..."; \
		if command -v pnpm >/dev/null 2>&1; then \
			cd remotion-composer && pnpm install --frozen-lockfile; \
		elif command -v corepack >/dev/null 2>&1; then \
			cd remotion-composer && corepack pnpm install --frozen-lockfile; \
		else \
			cd remotion-composer && npx --yes pnpm install --frozen-lockfile; \
		fi; \
	else \
		cd remotion-composer && npm install; \
	fi

# ---- Testing ----

test:
	python -m pytest tests/ -v

test-contracts:
	python -m pytest tests/contracts/ -v

genui-verify:
	python -m pytest -q tests/contracts/test_genui_session_contract.py tests/contracts/test_genui_dynamic_interaction.py tests/contracts/test_genui_interaction_contract.py tests/contracts/test_genui_surface_contract.py
	python -m pytest -q tests/contracts/test_genui_session_hardening.py
	python -m pytest -q tests/contracts/test_genui_product_contract.py
	python -m pytest -q tests/tools/test_genui_surface_browser.py
	pnpm --dir genui-renderer test
	pnpm --dir genui-renderer typecheck
	@before=$$(mktemp); after=$$(mktemp); \
		status=0; \
		git diff -- lib/genui/static/renderer > $$before; \
		pnpm --dir genui-renderer build; \
		git diff -- lib/genui/static/renderer > $$after; \
		if ! cmp -s $$before $$after; then \
			echo "genui renderer static bundle is stale; rerun pnpm --dir genui-renderer build and include lib/genui/static/renderer"; \
			git diff --exit-code -- lib/genui/static/renderer || status=$$?; \
		fi; \
		rm -f $$before $$after; \
		exit $$status

# ---- Utilities ----

preflight:
	python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu_summary(), indent=2))"

preflight-full:
	python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu(), indent=2))"

hyperframes-doctor:
	@echo "==> Probing HyperFrames runtime (node/ffmpeg/npx + hyperframes doctor)..."
	python -c "from tools.video.hyperframes_compose import HyperFramesCompose; r=HyperFramesCompose().execute({'operation':'doctor'}); import json; print(json.dumps(r.data, indent=2)); print('OK' if r.success else f'FAIL: {r.error}')"

hyperframes-warm:
	@echo "==> Refreshing the HyperFrames npx cache to latest..."
	@echo "    Uses --prefer-online so npx picks up new releases since your last run."
	npx --yes --prefer-online hyperframes --version
	@echo "==> Cache warm complete."

demo:
	@echo "==> Rendering zero-key demo videos (no API keys needed)..."
	@echo "    These use only Remotion components — animated charts, text, data viz."
	@echo ""
	python render_demo.py

demo-list:
	@python render_demo.py --list

lint:
	python -m py_compile tools/base_tool.py
	python -m py_compile tools/tool_registry.py
	python -m py_compile tools/cost_tracker.py
	python -m py_compile tools/analysis/composition_validator.py

clean:
	python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"
