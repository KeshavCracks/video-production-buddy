"""Small local GSAP-compatible shim for generated HyperFrames fixtures."""

from __future__ import annotations


def gsap_shim_script() -> str:
    """Return an inline script implementing the GSAP subset we generate.

    HyperFrames can drive any object registered in ``window.__timelines`` when
    it exposes the GSAP-like
    ``duration/totalDuration/time/totalTime/seek/timeScale/play/pause/paused``
    methods. HyperFrames also inspects timelines with ``getChildren()`` during
    capture. The generated Video Production Buddy compositions only use a small
    subset of GSAP, so this avoids a remote CDN dependency for local validation
    and test renders.
    """
    return """<script>
(function () {
  if (window.gsap) return;
  const CONTROL = new Set([
    "duration", "ease", "repeat", "repeatDelay", "yoyo",
    "transformOrigin", "svgOrigin"
  ]);
  const DEFAULTS = {
    opacity: 1, x: 0, y: 0, scale: 1, scaleX: 1, scaleY: 1, rotation: 0
  };
  function toArray(targets) {
    if (!targets) return [];
    if (typeof targets === "string") return Array.from(document.querySelectorAll(targets));
    if (targets instanceof Element || targets === window || targets === document) return [targets];
    return Array.from(targets);
  }
  function selector(scope) {
    return function (query) { return Array.from(scope.querySelectorAll(query)); };
  }
  function px(value) {
    return typeof value === "number" ? value + "px" : String(value);
  }
  function setTransform(node, prop, value) {
    const state = node.__hfTransform || {
      x: 0, y: 0, scale: 1, scaleX: 1, scaleY: 1, rotation: 0
    };
    state[prop] = Number(value) || 0;
    if (prop === "scale" && !Number.isFinite(Number(value))) state[prop] = 1;
    node.__hfTransform = state;
    node.style.transform =
      "translate(" + state.x + "px, " + state.y + "px) " +
      "rotate(" + state.rotation + "deg) " +
      "scale(" + state.scale + ") scale(" + state.scaleX + ", " + state.scaleY + ")";
  }
  function applyProp(node, prop, value) {
    if (prop === "x" || prop === "y" || prop === "scale" ||
        prop === "scaleX" || prop === "scaleY" || prop === "rotation") {
      setTransform(node, prop, value);
    } else if (prop === "opacity") {
      node.style.opacity = String(value);
    } else if (prop === "width" || prop === "height") {
      node.style[prop] = px(value);
    } else if (prop === "visibility") {
      node.style.visibility = String(value);
    }
  }
  function applyOrigin(node, vars) {
    const origin = vars.transformOrigin || vars.svgOrigin;
    if (!origin) return;
    const parts = String(origin).trim().split(/\\s+/);
    if (vars.svgOrigin && parts.length >= 2) {
      node.style.transformOrigin = parts[0] + "px " + parts[1] + "px";
      node.style.transformBox = "fill-box";
    } else {
      node.style.transformOrigin = String(origin);
    }
  }
  function interpolate(start, end, progress) {
    if (typeof end !== "number") return progress >= 1 ? end : start;
    const from = typeof start === "number" ? start : DEFAULTS.opacity;
    return from + (end - from) * progress;
  }
  function timeline(options) {
    const tweens = [];
    let cursor = 0;
    let lastStart = 0;
    let currentTime = 0;
    let playbackScale = 1;
    let isPaused = !(options && options.paused === false);
    function position(value) {
      if (typeof value === "number") return value;
      if (value === "<") return lastStart;
      return cursor;
    }
    function add(kind, targets, vars, at) {
      vars = vars || {};
      const start = position(at);
      const duration = Math.max(0, Number(vars.duration || 0));
      const repeat = Math.max(0, Number(vars.repeat || 0));
      const total = duration * (repeat + 1);
      tweens.push({ kind, nodes: toArray(targets), vars, start, duration, repeat });
      lastStart = start;
      cursor = Math.max(cursor, start + total + Number(vars.repeatDelay || 0) * repeat);
      return api;
    }
    function addChild(child, at) {
      const start = position(at);
      const duration = child && typeof child.duration === "function" ? child.duration() : 0;
      tweens.push({ kind: "child", child: child, start, duration, repeat: 0 });
      lastStart = start;
      cursor = Math.max(cursor, start + duration);
      return api;
    }
    function endpoints(kind, prop, vars) {
      const target = vars[prop];
      const base = prop in DEFAULTS ? DEFAULTS[prop] : target;
      if (kind === "from") return [target, base];
      return [base, target];
    }
    function seek(time) {
      currentTime = Math.max(0, Number(time || 0));
      for (const tween of tweens) {
        if (tween.kind === "child") {
          if (tween.child && typeof tween.child.seek === "function") {
            const childDuration = tween.duration || 0;
            const childTime = Math.max(0, Math.min(childDuration, currentTime - tween.start));
            tween.child.seek(childTime);
          }
          continue;
        }
        if (currentTime < tween.start) continue;
        const local = currentTime - tween.start;
        const duration = tween.duration;
        const repeatDelay = Number(tween.vars.repeatDelay || 0);
        let progress = duration > 0 ? Math.min(1, local / duration) : 1;
        if (duration > 0 && tween.repeat > 0) {
          const cycle = duration + repeatDelay;
          const iteration = Math.min(tween.repeat, Math.floor(local / cycle));
          const cycleTime = Math.max(0, local - iteration * cycle);
          progress = Math.min(1, cycleTime / duration);
          if (tween.vars.yoyo && iteration % 2 === 1) progress = 1 - progress;
        }
        for (const node of tween.nodes) {
          applyOrigin(node, tween.vars);
          for (const prop of Object.keys(tween.vars)) {
            if (CONTROL.has(prop)) continue;
            const pair = endpoints(tween.kind, prop, tween.vars);
            applyProp(node, prop, interpolate(pair[0], pair[1], progress));
          }
        }
      }
      return api;
    }
    const api = {
      set: function (targets, vars, at) { return add("set", targets, vars, at); },
      to: function (targets, vars, at) { return add("to", targets, vars, at); },
      from: function (targets, vars, at) { return add("from", targets, vars, at); },
      add: addChild,
      fromTo: function (targets, fromVars, toVars, at) {
        add("from", targets, fromVars, at);
        return add("to", targets, toVars, at);
      },
      duration: function () { return cursor; },
      totalDuration: function () { return cursor; },
      getChildren: function () { return []; },
      time: function () { return currentTime; },
      totalTime: function (value) {
        if (arguments.length === 0) return currentTime;
        return seek(value);
      },
      seek: seek,
      timeScale: function (value) {
        if (arguments.length === 0) return playbackScale;
        playbackScale = Number(value);
        if (!Number.isFinite(playbackScale)) playbackScale = 1;
        return api;
      },
      play: function () { isPaused = false; return api; },
      pause: function () { isPaused = true; return api; },
      paused: function (value) {
        if (arguments.length === 0) return isPaused;
        isPaused = Boolean(value);
        return api;
      }
    };
    if (options && options.paused === false) api.play();
    return api;
  }
  window.gsap = {
    timeline: timeline,
    set: function (targets, vars) { return timeline({ paused: true }).set(targets, vars, 0); },
    utils: { toArray: toArray, selector: selector }
  };
})();
</script>"""
