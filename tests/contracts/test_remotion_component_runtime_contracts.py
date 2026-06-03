"""Runtime checks for documented Remotion component contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
REMOTION_DIR = ROOT / "remotion-composer"


def _render_component(module_path: str, export_name: str, props: dict) -> str:
    """Render a Remotion TSX component with deterministic mocked frame hooks."""
    if shutil.which("node") is None:
        pytest.skip("node is required for Remotion component runtime checks")
    if not (REMOTION_DIR / "node_modules" / "typescript").exists():
        pytest.skip("remotion-composer/node_modules is required for component runtime checks")

    script = textwrap.dedent(
        f"""
        const fs = require("fs");
        const Module = require("module");
        const ts = require({json.dumps(str(REMOTION_DIR / "node_modules" / "typescript"))});
        const React = require({json.dumps(str(REMOTION_DIR / "node_modules" / "react"))});
        const ReactDOMServer = require({json.dumps(str(REMOTION_DIR / "node_modules" / "react-dom" / "server"))});

        function interpolate(input, inputRange, outputRange, options = {{}}) {{
          if (inputRange.length !== outputRange.length) {{
            throw new Error("mock interpolate expects matching range lengths");
          }}
          if (input <= inputRange[0]) {{
            return options.extrapolateLeft === "clamp" ? outputRange[0] : outputRange[0];
          }}
          for (let i = 0; i < inputRange.length - 1; i++) {{
            const left = inputRange[i];
            const right = inputRange[i + 1];
            if (input <= right || i === inputRange.length - 2) {{
              const span = right - left || 1;
              const t = Math.max(0, Math.min(1, (input - left) / span));
              return outputRange[i] + (outputRange[i + 1] - outputRange[i]) * t;
            }}
          }}
          return outputRange[outputRange.length - 1];
        }}

        const originalLoad = Module._load;
        Module._load = function(request, parent, isMain) {{
          if (request === "remotion") {{
            return {{
              AbsoluteFill: ({{children, style}}) => React.createElement("div", {{style}}, children),
              Audio: (props) => React.createElement("audio", props),
              Img: (props) => React.createElement("img", props),
              OffthreadVideo: (props) => React.createElement("video", props),
              Sequence: ({{children}}) => React.createElement(React.Fragment, null, children),
              Easing: {{
                ease: (t) => t,
                inOut: (fn) => fn,
              }},
              interpolate,
              random: () => 0.5,
              spring: (args = {{}}) => (args.frame || 0) < 0 ? 0 : 1,
              staticFile: (src) => `static:${{src}}`,
              useCurrentFrame: () => 0,
              useVideoConfig: () => ({{fps: 30, durationInFrames: 150, width: 1920, height: 1080}}),
            }};
          }}
          return originalLoad.apply(this, arguments);
        }};

        function transpileTypescriptModule(module, filename) {{
          const source = fs.readFileSync(filename, "utf8");
          const result = ts.transpileModule(source, {{
            compilerOptions: {{
              module: ts.ModuleKind.CommonJS,
              jsx: ts.JsxEmit.ReactJSX,
              esModuleInterop: true,
              target: ts.ScriptTarget.ES2020,
            }},
            fileName: filename,
          }});
          module._compile(result.outputText, filename);
        }}
        require.extensions[".ts"] = transpileTypescriptModule;
        require.extensions[".tsx"] = transpileTypescriptModule;

        const componentModule = require({json.dumps(str(REMOTION_DIR / module_path))});
        const Component = componentModule[{json.dumps(export_name)}];
        const markup = ReactDOMServer.renderToStaticMarkup(
          React.createElement(Component, {json.dumps(props)})
        );
        process.stdout.write(markup);
        """
    )

    result = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def test_browser_tabs_scene_only_counts_tabs_hidden_by_tab_count() -> None:
    """The overflow badge should not invent extra hidden browser tabs."""
    all_tabs_fit = _render_component(
        "src/components/BrowserTabsScene.tsx",
        "BrowserTabsScene",
        {"tabCount": 3},
    )
    assert "more" not in all_tabs_fit

    hidden_tabs = _render_component(
        "src/components/BrowserTabsScene.tsx",
        "BrowserTabsScene",
        {"tabCount": 15},
    )
    assert "+3 more" in hidden_tabs


def test_provider_chip_suppresses_empty_provider_lists() -> None:
    """Empty provider overlays should not render a blank pill."""
    empty_chip = _render_component(
        "src/components/ProviderChip.tsx",
        "ProviderChip",
        {"providers": []},
    )
    assert "generated with" not in empty_chip

    named_chip = _render_component(
        "src/components/ProviderChip.tsx",
        "ProviderChip",
        {"providers": ["Seedance"]},
    )
    assert "generated with" in named_chip
    assert "Seedance" in named_chip


def test_titled_video_uses_canonical_file_url_for_absolute_video_paths() -> None:
    """Absolute Unix paths should not grow an extra slash in file URLs."""
    markup = _render_component(
        "src/TitledVideo.tsx",
        "TitledVideo",
        {
            "videoSrc": "/tmp/video production buddy clip.mp4",
            "tagline": "A precise finish.",
            "taglineInSeconds": 0,
        },
    )

    assert 'src="file:///tmp/video%20production%20buddy%20clip.mp4"' in markup


def test_talking_head_uses_canonical_file_url_for_absolute_video_paths() -> None:
    """TalkingHead receives local source footage from tool outputs outside public/."""
    markup = _render_component(
        "src/TalkingHead.tsx",
        "TalkingHead",
        {
            "videoSrc": "/tmp/video production buddy talking head.mp4",
            "captions": [],
            "overlays": [],
        },
    )

    assert 'src="file:///tmp/video%20production%20buddy%20talking%20head.mp4"' in markup


def test_product_reveal_uses_canonical_file_url_for_absolute_product_images() -> None:
    """Standalone product reveal compositions should accept approved local product images."""
    markup = _render_component(
        "src/components/ProductReveal.tsx",
        "ProductReveal",
        {
            "productImage": "/tmp/video production buddy product.png",
            "productName": "Video Production Buddy Device",
            "price": "From $499",
            "tagline": "Production-ready motion.",
            "closer": "Ship the ad.",
        },
    )

    assert 'src="file:///tmp/video%20production%20buddy%20product.png"' in markup
    assert "static:/tmp/video production buddy" not in markup


def test_anime_scene_bypasses_static_file_for_absolute_image_paths() -> None:
    """Absolute image paths are outside public/ and must render as file URLs."""
    markup = _render_component(
        "src/components/AnimeScene.tsx",
        "AnimeScene",
        {"images": ["/tmp/video production buddy frame.png"]},
    )

    assert 'src="file:///tmp/video%20production%20buddy%20frame.png"' in markup
