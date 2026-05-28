import { describe, expect, it } from "vitest";
import {
  buildA2UISubmissionPayload,
  buildSubmissionPayload,
  extractA2UISessionSpec,
  extractReactSpec,
  isA2UISessionSpec,
  listConfiguredFieldIds,
  resolveSameOriginSubmitUrl,
  safeMediaSrc,
  type VideoProductionBuddyViewSpec
} from "./payload";

const viewSpec: VideoProductionBuddyViewSpec = {
  contract: "genui_surface_view",
  renderer: "json-render",
  root: "genui-root",
  elements: {
    "genui-root": {
      type: "WorkspaceShell",
      props: { title: "Gate", surfaceId: "cfg-demo" },
      children: ["field-product-model", "field-derivatives", "genui-actions"]
    },
    "field-product-model": {
      type: "TextInputField",
      props: { fieldId: "product_model", value: { $bindState: "/values/product_model" } },
      children: []
    },
    "field-derivatives": {
      type: "ChoiceGroupField",
      props: { fieldId: "derivatives", value: { $bindState: "/values/derivatives" }, multiple: true },
      children: []
    },
    "genui-actions": {
      type: "ActionBar",
      props: { actions: [{ id: "approve", label: "Approve", kind: "approve" }], submitUrl: "/submit" },
      children: []
    }
  },
  state: {
    values: {
      product_model: "OPPO Find X9 Pro",
      derivatives: ["9:16"],
      unconfigured: "must not submit"
    }
  },
  metadata: { surface_id: "cfg-demo", config_id: "cfg-demo", submit_url: "/submit" }
};

describe("payload helpers", () => {
  it("submits only configured field values with auditable browser events", () => {
    const payload = buildSubmissionPayload("approve", viewSpec, viewSpec.state);

    expect(payload.action).toBe("approve");
    expect(payload.values).toEqual({
      product_model: "OPPO Find X9 Pro",
      derivatives: ["9:16"]
    });
    expect(payload.browser_events.map((event) => event.type)).toEqual([
      "action_click",
      "submit_attempt"
    ]);
  });

  it("recognizes GenUI-compatible A2UI session specs and extracts framework operations", () => {
    const sessionSpec: VideoProductionBuddyViewSpec = {
      contract: "genui_session_view",
      renderer: "a2ui",
      root: "genui-session-root",
      a2ui: {
        surface_id: "asset-sample-review",
        operations: [
          { type: "surfaceUpdate", surfaceId: "asset-sample-review", components: [] },
          { type: "dataModelUpdate", surfaceId: "asset-sample-review", data: { values: {} } },
          { type: "beginRendering", surfaceId: "asset-sample-review", rootId: "genui-session-root" }
        ],
        components: [
          {
            id: "genui-session-root",
            type: "SessionShell",
            props: { title: "Review", mode: "media_review_room" },
            children: ["review-room", "issues"]
          },
          {
            id: "review-room",
            type: "MediaReviewRoom",
            props: {
              title: "Sample review room",
              mediaRefs: [{ id: "sample_clip", title: "Sample", kind: "video", path: "/media/renders/sample.mp4" }],
              requiredEvidence: ["media_opened", "timeline_inspected"]
            },
            children: []
          },
          {
            id: "issues",
            type: "IssueTracker",
            props: { title: "Issues", allowedTargets: ["sample_clip"], allowedStatuses: ["open", "resolved"] },
            children: []
          }
        ],
        data_model: {
          values: {},
          annotations: [],
          issues: [],
          interaction_evidence: { media_opened: [], timeline_inspected: [], seconds_watched: 0 }
        }
      },
      metadata: {
        session_id: "asset-sample-review",
        submit_nonce: "nonce",
        framework: { name: "a2ui", renderer: "@copilotkit/a2ui-renderer" }
      }
    };

    expect(isA2UISessionSpec(sessionSpec)).toBe(true);
    const extracted = extractA2UISessionSpec(sessionSpec);
    expect(extracted.surfaceId).toBe("asset-sample-review");
    expect(extracted.operations.map((operation) => operation.type)).toEqual([
      "surfaceUpdate",
      "dataModelUpdate",
      "beginRendering"
    ]);
    expect(extracted.components.map((component) => component.type)).toContain("MediaReviewRoom");
  });

  it("omits hidden A2UI fields and their stale patches from session submissions", () => {
    const sessionSpec: VideoProductionBuddyViewSpec = {
      contract: "genui_session_view",
      renderer: "a2ui",
      root: "genui-product-root",
      a2ui: {
        surface_id: "proposal-lock",
        operations: [],
        components: [
          {
            id: "genui-product-root",
            type: "SessionShell",
            props: {},
            children: ["proposal"]
          },
          {
            id: "proposal",
            type: "GateWorkspace",
            props: {
              title: "Proposal",
              selection: {
                fieldId: "decision",
                binding: { artifact: "production_proposal", path: "approval.decision" }
              },
              fields: [
                {
                  id: "revision_notes",
                  label: "Revision notes",
                  type: "textarea",
                  visible_if: { field: "decision", operator: "equals", value: "revise" },
                  binding: { artifact: "production_proposal", path: "human_feedback.notes" }
                }
              ]
            },
            children: []
          }
        ],
        data_model: {
          values: {
            decision: "approve",
            revision_notes: "stale hidden note"
          },
          revision_patches: [
            { artifact: "production_proposal", path: "approval.decision", value: "approve" },
            { artifact: "production_proposal", path: "human_feedback.notes", value: "stale hidden note" }
          ]
        }
      },
      metadata: { submit_nonce: "nonce" }
    };

    const hiddenPayload = buildA2UISubmissionPayload(
      "approve",
      sessionSpec,
      sessionSpec.a2ui.data_model
    );

    expect(hiddenPayload.values).toEqual({ decision: "approve" });
    expect(hiddenPayload.revision_patches).toEqual([
      { artifact: "production_proposal", path: "approval.decision", value: "approve" }
    ]);

    const visiblePayload = buildA2UISubmissionPayload("revise", sessionSpec, {
      values: {
        decision: "revise",
        revision_notes: "visible note"
      },
      revision_patches: [
        { artifact: "production_proposal", path: "approval.decision", value: "revise" },
        { artifact: "production_proposal", path: "human_feedback.notes", value: "visible note" }
      ]
    });

    expect(visiblePayload.values).toEqual({
      decision: "revise",
      revision_notes: "visible note"
    });
    expect(visiblePayload.revision_patches).toEqual([
      { artifact: "production_proposal", path: "approval.decision", value: "revise" },
      { artifact: "production_proposal", path: "human_feedback.notes", value: "visible note" }
    ]);
  });

  it("builds session submissions with media evidence, timecoded issues, and nonce", () => {
    const sessionSpec: VideoProductionBuddyViewSpec = {
      contract: "genui_session_view",
      renderer: "a2ui",
      root: "genui-session-root",
      a2ui: {
        surface_id: "asset-sample-review",
        operations: [
          { type: "surfaceUpdate", surfaceId: "asset-sample-review", components: [] },
          { type: "dataModelUpdate", surfaceId: "asset-sample-review", data: {} },
          { type: "beginRendering", surfaceId: "asset-sample-review", rootId: "genui-session-root" }
        ],
        components: [],
        data_model: {
          values: {
            "asset_manifest.human_feedback.product_fidelity_notes": "Logo reflection drifts."
          },
          annotations: [
            {
              surface_id: "review-room",
              target_ref: "sample_clip",
              comment: "Logo reflection changes shape.",
              timestamp_seconds: 1.4,
              time_range: { start_seconds: 1.1, end_seconds: 2.0 },
              region: { x: 0.4, y: 0.2, width: 0.2, height: 0.1 }
            }
          ],
          issues: [
            {
              id: "issue-logo-reflection",
              target_ref: "sample_clip",
              status: "open",
              severity: "blocking",
              requested_change: "Regenerate the first shot.",
              artifact: "asset_manifest",
              path: "human_feedback.product_fidelity_notes"
            }
          ],
          revision_patches: [
            {
              artifact: "asset_manifest",
              path: "human_feedback.product_fidelity_notes",
              value: "Logo reflection drifts."
            }
          ],
          approval_attestations: [
            { id: "reviewed-media", label: "I reviewed the sample media before submitting.", approved: true }
          ],
          interaction_evidence: {
            media_opened: ["sample_clip"],
            timeline_inspected: ["sample_clip"],
            seconds_watched: 2.5
          }
        }
      },
      metadata: { session_id: "asset-sample-review", submit_nonce: "nonce" }
    };

    const payload = buildA2UISubmissionPayload("revise", sessionSpec);

    expect(payload.action).toBe("revise");
    expect(payload.nonce).toBe("nonce");
    expect(payload.values).toEqual({
      "asset_manifest.human_feedback.product_fidelity_notes": "Logo reflection drifts."
    });
    expect(payload.annotations?.[0]).toMatchObject({ target_ref: "sample_clip", timestamp_seconds: 1.4 });
    expect(payload.issues?.[0]).toMatchObject({ id: "issue-logo-reflection", status: "open" });
    expect(payload.interaction_evidence).toEqual({
      media_opened: ["sample_clip"],
      timeline_inspected: ["sample_clip"],
      seconds_watched: 2.5
    });
    expect(payload.browser_events.map((event) => event.type)).toEqual([
      "action_click",
      "submit_attempt"
    ]);
  });

  it("lists configured fields from json-render elements", () => {
    expect(listConfiguredFieldIds(viewSpec)).toEqual(["product_model", "derivatives"]);
  });

  it("passes only the json-render spec shape to the library renderer", () => {
    const spec = extractReactSpec(viewSpec);

    expect(spec).toEqual({
      root: "genui-root",
      elements: viewSpec.elements,
      state: viewSpec.state
    });
  });

  it("resolves submissions to the current origin instead of trusting spec URLs", () => {
    expect(resolveSameOriginSubmitUrl("http://127.0.0.1:8123/form")).toBe("http://127.0.0.1:8123/submit");
  });

  it("rejects media sources that are not server-relative safe paths", () => {
    expect(safeMediaSrc("/media/product.png")).toBe("/media/product.png");
    expect(safeMediaSrc("/media/assets/images/ref.png")).toBe("/media/assets/images/ref.png");
    expect(safeMediaSrc("https://example.test/leak.png")).toBeNull();
    expect(safeMediaSrc("file:///etc/passwd")).toBeNull();
    expect(safeMediaSrc("//example.test/leak.png")).toBeNull();
    expect(safeMediaSrc("javascript:alert(1)")).toBeNull();
    expect(safeMediaSrc("/media/../secret.txt")).toBeNull();
    expect(safeMediaSrc("/media/%2e%2e/secret.txt")).toBeNull();
    expect(safeMediaSrc("/media/assets\\secret.txt")).toBeNull();
  });

  it("submits compatibility surface state with annotations, selected refs, patches, and attestations", () => {
    const surfaceSpec: VideoProductionBuddyViewSpec = {
      contract: "genui_surface_view",
      renderer: "json-render",
      root: "genui-root",
      elements: {
        "genui-root": {
          type: "WorkspaceShell",
          props: { title: "Workspace", surfaceId: "proposal-workspace" },
          children: ["runtime", "trace", "genui-actions"]
        },
        runtime: {
          type: "RuntimeComparison",
          props: {
            blockId: "runtime",
            valueFieldId: "runtime.selection",
            options: [
              { id: "remotion", label: "Remotion" },
              { id: "hyperframes", label: "HyperFrames" }
            ]
          },
          children: []
        },
        trace: {
          type: "ArtifactTracePanel",
          props: { blockId: "trace", artifactRefs: [], traceRefs: [] },
          children: []
        },
        "genui-actions": {
          type: "ActionBar",
          props: { actions: [{ id: "approve", label: "Approve", kind: "approve" }], submitUrl: "/submit" },
          children: []
        }
      },
      state: {
        values: {
          "runtime.selection": "remotion",
          unconfigured: "must not submit"
        },
        annotations: [
          { block_id: "sample", target_ref: "sample_clip", comment: "Use this pacing." }
        ],
        selected_refs: ["remotion", "sample_clip"],
        revision_patches: [
          { artifact: "production_proposal", path: "human_feedback.notes", value: "Keep sample pacing." }
        ],
        approval_attestations: [
          { id: "proposal-approval", label: "Proposal approval", approved: true }
        ]
      },
      metadata: { surface_id: "proposal-workspace", submit_nonce: "nonce" }
    };

    const payload = buildSubmissionPayload("approve", surfaceSpec, surfaceSpec.state);

    expect(payload.action).toBe("approve");
    expect(payload.nonce).toBe("nonce");
    expect(payload.values).toEqual({ "runtime.selection": "remotion" });
    expect(payload.annotations).toEqual(surfaceSpec.state?.annotations);
    expect(payload.selected_refs).toEqual(["remotion", "sample_clip"]);
    expect(payload.revision_patches).toEqual(surfaceSpec.state?.revision_patches);
    expect(payload.approval_attestations).toEqual(surfaceSpec.state?.approval_attestations);
  });

  it("derives compatibility surface review payloads from interactive workspace controls", () => {
    const surfaceSpec: VideoProductionBuddyViewSpec = {
      contract: "genui_surface_view",
      renderer: "json-render",
      root: "genui-root",
      elements: {
        "genui-root": {
          type: "WorkspaceShell",
          props: { title: "Workspace", surfaceId: "concept-workspace" },
          children: ["comparison", "media", "revisions", "approval", "genui-actions"]
        },
        comparison: {
          type: "ConceptComparison",
          props: {
            blockId: "comparison",
            valueFieldId: "comparison.selection",
            valueFieldIds: ["comparison.selection"],
            options: [
              { id: "c1", value: "concept_one", label: "Concept One" },
              { id: "c2", value: "concept_two", label: "Concept Two" }
            ]
          },
          children: []
        },
        media: {
          type: "MediaCompare",
          props: {
            blockId: "media",
            valueFieldIds: ["media.notes"],
            mediaRefs: [{ id: "sample_clip", title: "Sample", kind: "video", path: "/media/renders/sample.mp4" }],
            annotationFields: [{ id: "notes", label: "Notes", type: "textarea" }]
          },
          children: []
        },
        revisions: {
          type: "RevisionPatch",
          props: {
            blockId: "revisions",
            valueFieldIds: ["revisions.hook"],
            fields: [
              {
                id: "hook",
                label: "Hook revision",
                type: "textarea",
                binding: { artifact: "idea_options", path: "human_feedback.hook" }
              }
            ]
          },
          children: []
        },
        approval: {
          type: "ApprovalChecklist",
          props: {
            blockId: "approval",
            valueFieldIds: ["approval.reviewed", "approval.product-visible"],
            items: [
              { id: "reviewed", label: "I reviewed the visible evidence.", required: true },
              { id: "product visible", label: "Product remains visible.", required: true }
            ]
          },
          children: []
        },
        "genui-actions": {
          type: "ActionBar",
          props: { actions: [{ id: "approve", label: "Approve", kind: "approve" }], submitUrl: "/submit" },
          children: []
        }
      },
      state: {
        values: {
          "comparison.selection": "concept_two",
          "media.notes": "Use this pacing.",
          "revisions.hook": "Make the hook more immediate.",
          "approval.reviewed": true,
          "approval.product-visible": true
        }
      },
      metadata: { surface_id: "concept-workspace" }
    };

    const payload = buildSubmissionPayload("approve", surfaceSpec, surfaceSpec.state);

    expect(payload.selected_refs).toEqual(["concept_two"]);
    expect(payload.annotations).toEqual([
      { block_id: "media", target_ref: "sample_clip", comment: "Use this pacing." }
    ]);
    expect(payload.revision_patches).toEqual([
      { artifact: "idea_options", path: "human_feedback.hook", value: "Make the hook more immediate." }
    ]);
    expect(payload.approval_attestations).toEqual([
      { id: "reviewed", label: "I reviewed the visible evidence.", approved: true },
      { id: "product-visible", label: "Product remains visible.", approved: true }
    ]);
  });

  it("omits compatibility surface hidden fields from the submitted payload", () => {
    const surfaceSpec: VideoProductionBuddyViewSpec = {
      contract: "genui_surface_view",
      renderer: "json-render",
      root: "genui-root",
      elements: {
        "genui-root": {
          type: "WorkspaceShell",
          props: { title: "Workspace", surfaceId: "proposal-workspace" },
          children: ["comparison", "revisions", "genui-actions"]
        },
        comparison: {
          type: "ConceptComparison",
          props: {
            blockId: "comparison",
            valueFieldId: "comparison.selection",
            valueFieldIds: ["comparison.selection"],
            options: [
              { id: "approve", label: "Approve" },
              { id: "revise", label: "Revise" }
            ]
          },
          children: []
        },
        revisions: {
          type: "RevisionPatch",
          props: {
            blockId: "revisions",
            valueFieldIds: ["revisions.notes"],
            fields: [
              {
                id: "notes",
                label: "Notes",
                type: "textarea",
                visible_if: { field: "selection", operator: "equals", value: "revise" }
              }
            ]
          },
          children: []
        },
        "genui-actions": {
          type: "ActionBar",
          props: { actions: [{ id: "approve", label: "Approve", kind: "approve" }], submitUrl: "/submit" },
          children: []
        }
      },
      state: {
        values: {
          "comparison.selection": "approve",
          "revisions.notes": "stale hidden value"
        }
      },
      metadata: { surface_id: "proposal-workspace" }
    };

    const hiddenPayload = buildSubmissionPayload("approve", surfaceSpec, surfaceSpec.state);
    expect(hiddenPayload.values).toEqual({ "comparison.selection": "approve" });

    const visibleState = {
      values: {
        "comparison.selection": "revise",
        "revisions.notes": "visible revision"
      }
    };
    const visiblePayload = buildSubmissionPayload("approve", surfaceSpec, visibleState);
    expect(visiblePayload.values).toEqual({
      "comparison.selection": "revise",
      "revisions.notes": "visible revision"
    });
  });

  it("turns bound block selections and explicit false or empty field edits into semantic patches", () => {
    const surfaceSpec: VideoProductionBuddyViewSpec = {
      contract: "genui_surface_view",
      renderer: "json-render",
      root: "genui-root",
      elements: {
        "genui-root": {
          type: "WorkspaceShell",
          props: { title: "Workspace", surfaceId: "runtime-workspace" },
          children: ["runtime", "controls", "genui-actions"]
        },
        runtime: {
          type: "RuntimeComparison",
          props: {
            blockId: "runtime",
            binding: { artifact: "production_proposal", path: "visual_contract.render_runtime" },
            valueFieldId: "runtime.selection",
            valueFieldIds: ["runtime.selection"],
            options: [
              { id: "remotion", value: "remotion", label: "Remotion" },
              { id: "hyperframes", value: "hyperframes", label: "HyperFrames" }
            ]
          },
          children: []
        },
        controls: {
          type: "RevisionPatch",
          props: {
            blockId: "controls",
            valueFieldIds: ["controls.enable_music", "controls.tagline"],
            fields: [
              {
                id: "enable_music",
                label: "Enable music",
                type: "checkbox",
                binding: { artifact: "production_proposal", path: "audio.music_enabled" }
              },
              {
                id: "tagline",
                label: "Tagline",
                type: "textarea",
                binding: { artifact: "script", path: "human_feedback.tagline" }
              }
            ]
          },
          children: []
        },
        "genui-actions": {
          type: "ActionBar",
          props: { actions: [{ id: "approve", label: "Approve", kind: "approve" }], submitUrl: "/submit" },
          children: []
        }
      },
      state: {
        values: {
          "runtime.selection": "hyperframes",
          "controls.enable_music": false,
          "controls.tagline": ""
        }
      },
      metadata: { surface_id: "runtime-workspace" }
    };

    const payload = buildSubmissionPayload("approve", surfaceSpec, surfaceSpec.state);

    expect(payload.selected_refs).toEqual(["hyperframes"]);
    expect(payload.revision_patches).toEqual([
      {
        artifact: "production_proposal",
        path: "visual_contract.render_runtime",
        value: "hyperframes"
      },
      { artifact: "production_proposal", path: "audio.music_enabled", value: false },
      { artifact: "script", path: "human_feedback.tagline", value: "" }
    ]);
  });

  it("uses explicit annotation targets and avoids first-media misattribution for multi-media notes", () => {
    const surfaceSpec: VideoProductionBuddyViewSpec = {
      contract: "genui_surface_view",
      renderer: "json-render",
      root: "genui-root",
      elements: {
        "genui-root": {
          type: "WorkspaceShell",
          props: { title: "Workspace", surfaceId: "media-workspace" },
          children: ["media", "genui-actions"]
        },
        media: {
          type: "MediaCompare",
          props: {
            blockId: "media",
            valueFieldIds: ["media.overall_notes", "media.second_notes"],
            mediaRefs: [
              { id: "first_clip", title: "First", kind: "video", path: "/media/renders/first.mp4" },
              { id: "second_clip", title: "Second", kind: "video", path: "/media/renders/second.mp4" }
            ],
            annotationFields: [
              { id: "overall_notes", label: "Overall notes", type: "textarea" },
              { id: "second_notes", label: "Second clip notes", type: "textarea", target_ref: "second_clip" }
            ]
          },
          children: []
        },
        "genui-actions": {
          type: "ActionBar",
          props: { actions: [{ id: "approve", label: "Approve", kind: "approve" }], submitUrl: "/submit" },
          children: []
        }
      },
      state: {
        values: {
          "media.overall_notes": "The comparison needs a faster opener.",
          "media.second_notes": "Second clip has the stronger ending."
        }
      },
      metadata: { surface_id: "media-workspace" }
    };

    const payload = buildSubmissionPayload("approve", surfaceSpec, surfaceSpec.state);

    expect(payload.annotations).toEqual([
      {
        block_id: "media",
        target_ref: "media",
        comment: "The comparison needs a faster opener."
      },
      {
        block_id: "media",
        target_ref: "second_clip",
        comment: "Second clip has the stronger ending."
      }
    ]);
  });
});
