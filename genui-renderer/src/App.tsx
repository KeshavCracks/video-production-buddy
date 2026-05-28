import { EventType } from "@ag-ui/core";
import { JSONUIProvider, Renderer } from "@json-render/react";
import { useEffect, useMemo, useState } from "react";
import { registry } from "./registry";
import { A2UISessionRenderer } from "./a2uiAdapter";
import { extractReactSpec, isA2UISessionSpec, isJsonRenderSurfaceSpec, type VideoProductionBuddyViewSpec } from "./payload";

export function App() {
  const [viewSpec, setViewSpec] = useState<VideoProductionBuddyViewSpec | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/spec.json")
      .then((response) => {
        if (!response.ok) throw new Error(`Unable to load /spec.json (${response.status})`);
        return response.json() as Promise<VideoProductionBuddyViewSpec>;
      })
      .then((spec) => {
        if (cancelled) return;
        (window as typeof window & { __VIDEO_PRODUCTION_BUDDY_VIEW_SPEC__?: VideoProductionBuddyViewSpec }).__VIDEO_PRODUCTION_BUDDY_VIEW_SPEC__ = spec;
        setViewSpec(spec);
      })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof Error ? caught.message : String(caught));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const reactSpec = useMemo(() => viewSpec && isJsonRenderSurfaceSpec(viewSpec) ? extractReactSpec(viewSpec) : null, [viewSpec]);

  useEffect(() => {
    if (!viewSpec || (!isA2UISessionSpec(viewSpec) && !isJsonRenderSurfaceSpec(viewSpec))) return;
    const events = new EventSource("/events");
    const seenEvents: unknown[] = [];
    const rememberEvent = (event: MessageEvent<string>) => {
      try {
        seenEvents.push(JSON.parse(event.data));
        (window as typeof window & { __VIDEO_PRODUCTION_BUDDY_AG_UI_EVENTS__?: unknown[] }).__VIDEO_PRODUCTION_BUDDY_AG_UI_EVENTS__ = seenEvents;
      } catch {
        // AG-UI event telemetry is advisory; rendering must not fail if it is malformed.
      }
    };
    events.addEventListener(EventType.RUN_STARTED, rememberEvent);
    events.addEventListener(EventType.STATE_SNAPSHOT, rememberEvent);
    events.addEventListener(EventType.ACTIVITY_SNAPSHOT, rememberEvent);
    events.addEventListener(EventType.RUN_FINISHED, rememberEvent);
    events.onerror = () => {
      events.close();
    };
    return () => {
      events.close();
    };
  }, [viewSpec]);

  if (error) {
    return <main className="om-shell"><div className="om-error">GenUI renderer failed: {error}</div></main>;
  }
  if (!viewSpec) {
    return <main className="om-shell"><div className="om-status">Loading Video Production Buddy GenUI interface...</div></main>;
  }
  if (isA2UISessionSpec(viewSpec)) {
    return <A2UISessionRenderer spec={viewSpec} />;
  }
  if (!reactSpec || !isJsonRenderSurfaceSpec(viewSpec)) {
    return <main className="om-shell"><div className="om-error">Unsupported GenUI renderer spec.</div></main>;
  }

  return (
    <JSONUIProvider
      key={(viewSpec.metadata?.surface_id ?? viewSpec.metadata?.config_id) as string | undefined}
      registry={registry}
      initialState={reactSpec.state}
    >
      <Renderer spec={reactSpec} registry={registry} />
    </JSONUIProvider>
  );
}
