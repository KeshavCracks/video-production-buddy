import type { Spec } from "@json-render/react";

export type BrowserEvent = {
  type: string;
  timestamp?: string;
  action?: string;
  field_count?: number;
  target_ref?: string;
  timestamp_seconds?: number;
  [key: string]: unknown;
};

export type SubmissionPayload = {
  action: string;
  nonce?: string;
  values: Record<string, unknown>;
  annotations?: unknown[];
  selected_refs?: unknown[];
  issues?: unknown[];
  revision_patches?: unknown[];
  approval_attestations?: unknown[];
  interaction_evidence?: {
    media_opened: string[];
    timeline_inspected: string[];
    seconds_watched: number;
  };
  browser_events: BrowserEvent[];
};

export type ViewElement = {
  type: string;
  props: Record<string, unknown>;
  children?: string[];
};

export type A2UIComponentNode = {
  id: string;
  type: string;
  props: Record<string, unknown>;
  children?: string[];
};

export type A2UIOperation = {
  type: string;
  surfaceId?: string;
  components?: A2UIComponentNode[];
  data?: Record<string, unknown>;
  rootId?: string;
};

export type A2UISessionSpec = {
  surface_id: string;
  operations: A2UIOperation[];
  components: A2UIComponentNode[];
  data_model?: Record<string, unknown>;
};

type VisibleIf = {
  field: string;
  operator: "equals" | "not_equals" | "not_empty" | "empty";
  value?: unknown;
};

type Binding = {
  artifact: string;
  path: string;
};

type FieldSpec = {
  fieldId: string;
  localId?: string;
  blockId?: string;
  label?: string;
  kind?: "field" | "annotation" | "selection" | "approval";
  binding?: Binding;
  targetRef?: string;
  visible_if?: VisibleIf;
};

export type VideoProductionBuddySurfaceViewSpec = {
  contract: "genui_surface_view";
  version?: "2.0";
  renderer: "json-render";
  root: string;
  elements: Record<string, ViewElement>;
  state?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type VideoProductionBuddySessionViewSpec = {
  contract: "genui_session_view";
  version?: "3.0";
  renderer: "a2ui";
  root: string;
  a2ui: A2UISessionSpec;
  state?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

export type VideoProductionBuddyViewSpec = VideoProductionBuddySurfaceViewSpec | VideoProductionBuddySessionViewSpec;

function nowIso(): string {
  return new Date().toISOString();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isEmpty(value: unknown): boolean {
  if (value === undefined || value === null) return true;
  if (typeof value === "string") return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "boolean") return value === false;
  return false;
}

function hasPatchValue(value: unknown): boolean {
  if (value === undefined || value === null) return false;
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

function asVisibleIf(value: unknown): VisibleIf | undefined {
  if (!isRecord(value)) return undefined;
  if (typeof value.field !== "string" || typeof value.operator !== "string") return undefined;
  if (!["equals", "not_equals", "not_empty", "empty"].includes(value.operator)) return undefined;
  return {
    field: value.field,
    operator: value.operator as VisibleIf["operator"],
    value: value.value
  };
}

function asBinding(value: unknown): Binding | undefined {
  if (!isRecord(value)) return undefined;
  if (typeof value.artifact !== "string" || typeof value.path !== "string") return undefined;
  return { artifact: value.artifact, path: value.path };
}

function slug(value: unknown, fallback: string): string {
  const raw = String(value ?? fallback);
  let next = raw.replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^[-_.]+|[-_.]+$/g, "");
  if (!next) next = fallback;
  if (!/^[A-Za-z0-9]/.test(next)) next = `surface-${next}`;
  return next.slice(0, 64);
}

function addFieldSpec(fields: Map<string, FieldSpec>, spec: FieldSpec): void {
  const previous = fields.get(spec.fieldId);
  fields.set(spec.fieldId, {
    ...previous,
    ...spec,
    localId: spec.localId ?? previous?.localId,
    blockId: spec.blockId ?? previous?.blockId,
    label: spec.label ?? previous?.label,
    kind: spec.kind ?? previous?.kind,
    binding: spec.binding ?? previous?.binding,
    targetRef: spec.targetRef ?? previous?.targetRef,
    visible_if: spec.visible_if ?? previous?.visible_if
  });
}

function collectFieldSpecs(viewSpec: VideoProductionBuddySurfaceViewSpec): FieldSpec[] {
  const fields = new Map<string, FieldSpec>();
  for (const element of Object.values(viewSpec.elements)) {
    const blockId = typeof element.props.blockId === "string" ? element.props.blockId : undefined;
    const mediaRefs = Array.isArray(element.props.mediaRefs) ? element.props.mediaRefs : [];
    const mediaRefIds = mediaRefs
      .filter((ref) => isRecord(ref) && typeof ref.id === "string")
      .map((ref) => String((ref as Record<string, unknown>).id));
    for (const key of ["fields", "annotationFields"] as const) {
      const rawFields = element.props[key];
      if (!Array.isArray(rawFields) || !blockId) continue;
      for (const rawField of rawFields) {
        if (!isRecord(rawField) || typeof rawField.id !== "string") continue;
        const explicitTargetRef = typeof rawField.target_ref === "string"
          ? rawField.target_ref
          : typeof rawField.targetRef === "string"
            ? rawField.targetRef
            : undefined;
        addFieldSpec(fields, {
          fieldId: `${blockId}.${rawField.id}`,
          localId: rawField.id,
          blockId,
          label: typeof rawField.label === "string" ? rawField.label : rawField.id,
          kind: key === "annotationFields" ? "annotation" : "field",
          binding: asBinding(rawField.binding),
          targetRef: explicitTargetRef ?? (mediaRefIds.length === 1 ? mediaRefIds[0] : blockId),
          visible_if: asVisibleIf(rawField.visible_if)
        });
      }
    }
    if (typeof element.props.fieldId === "string") {
      addFieldSpec(fields, { fieldId: element.props.fieldId });
    }
    if (typeof element.props.valueFieldId === "string") {
      addFieldSpec(fields, {
        fieldId: element.props.valueFieldId,
        blockId,
        localId: "selection",
        kind: "selection",
        binding: asBinding(element.props.binding)
      });
    }
    if (Array.isArray(element.props.valueFieldIds)) {
      for (const fieldId of element.props.valueFieldIds) {
        if (typeof fieldId === "string") {
          addFieldSpec(fields, { fieldId, blockId });
        }
      }
    }
    if (element.type === "ApprovalChecklist" && blockId && Array.isArray(element.props.items)) {
      for (const item of element.props.items) {
        if (!isRecord(item)) continue;
        const itemId = slug(item.id ?? item.label, "approval");
        addFieldSpec(fields, {
          fieldId: `${blockId}.${itemId}`,
          localId: itemId,
          blockId,
          label: typeof item.label === "string" ? item.label : itemId,
          kind: "approval"
        });
      }
    }
  }
  return Array.from(fields.values());
}

function collectA2UIFieldSpecs(viewSpec: VideoProductionBuddySessionViewSpec): FieldSpec[] {
  const fields = new Map<string, FieldSpec>();
  const sessionSpec = extractA2UISessionSpec(viewSpec);
  for (const component of sessionSpec.components) {
    const rawFields = component.props.fields;
    if (Array.isArray(rawFields)) {
      for (const rawField of rawFields) {
        if (!isRecord(rawField) || typeof rawField.id !== "string") continue;
        addFieldSpec(fields, {
          fieldId: rawField.id,
          localId: rawField.id,
          label: typeof rawField.label === "string" ? rawField.label : rawField.id,
          kind: "field",
          binding: asBinding(rawField.binding),
          visible_if: asVisibleIf(rawField.visible_if)
        });
      }
    }
    const selection = component.props.selection;
    if (isRecord(selection) && typeof selection.fieldId === "string") {
      addFieldSpec(fields, {
        fieldId: selection.fieldId,
        localId: selection.fieldId,
        kind: "selection",
        binding: asBinding(selection.binding)
      });
    }
  }
  return Array.from(fields.values());
}

export function listConfiguredFieldIds(viewSpec: VideoProductionBuddySurfaceViewSpec): string[] {
  return collectFieldSpecs(viewSpec).map((field) => field.fieldId);
}

function resolveVisibleFieldId(field: FieldSpec, configuredFieldIds: string[]): string | null {
  if (!field.visible_if) return null;
  const reference = field.visible_if.field;
  if (configuredFieldIds.includes(reference)) return reference;

  if (field.blockId) {
    const sameBlock = `${field.blockId}.${reference}`;
    if (configuredFieldIds.includes(sameBlock)) return sameBlock;
  }

  const suffixMatches = configuredFieldIds.filter((fieldId) => fieldId.endsWith(`.${reference}`));
  return suffixMatches.length === 1 ? suffixMatches[0] : null;
}

function fieldIsVisible(
  field: FieldSpec,
  values: Record<string, unknown>,
  configuredFieldIds: string[]
): boolean {
  const visibleIf = field.visible_if;
  if (!visibleIf) return true;
  const referenceId = resolveVisibleFieldId(field, configuredFieldIds);
  if (!referenceId) return true;
  const value = values[referenceId];
  if (visibleIf.operator === "not_empty") return !isEmpty(value);
  if (visibleIf.operator === "empty") return isEmpty(value);
  if (visibleIf.operator === "equals") return value === visibleIf.value;
  if (visibleIf.operator === "not_equals") return value !== visibleIf.value;
  return true;
}

export function listVisibleConfiguredFieldIds(
  viewSpec: VideoProductionBuddySurfaceViewSpec,
  state: Record<string, unknown> | undefined
): string[] {
  const sourceValues = state?.values;
  const values = isRecord(sourceValues) ? sourceValues : {};
  const fields = collectFieldSpecs(viewSpec);
  const configuredFieldIds = fields.map((field) => field.fieldId);
  return fields
    .filter((field) => fieldIsVisible(field, values, configuredFieldIds))
    .map((field) => field.fieldId);
}

export function extractReactSpec(viewSpec: VideoProductionBuddySurfaceViewSpec): Spec {
  return {
    root: viewSpec.root,
    elements: viewSpec.elements,
    state: viewSpec.state
  };
}

export function buildSubmissionPayload(
  action: string,
  viewSpec: VideoProductionBuddySurfaceViewSpec,
  state: Record<string, unknown> | undefined
): SubmissionPayload {
  const sourceValues = state?.values;
  const values = isRecord(sourceValues) ? sourceValues : {};
  const configuredFieldIds = listVisibleConfiguredFieldIds(viewSpec, state);
  const submittedValues = Object.fromEntries(
    configuredFieldIds.map((fieldId) => [fieldId, values[fieldId]])
  );

  const payload: SubmissionPayload = {
    action,
    nonce: typeof viewSpec.metadata?.submit_nonce === "string"
      ? viewSpec.metadata.submit_nonce
      : undefined,
    values: submittedValues,
    browser_events: [
      {
        type: "action_click",
        timestamp: nowIso(),
        action,
        field_count: configuredFieldIds.length
      },
      {
        type: "submit_attempt",
        timestamp: nowIso(),
        action
      }
    ]
  };
  const fieldSpecs = collectFieldSpecs(viewSpec).filter((field) => configuredFieldIds.includes(field.fieldId));
  const existingAnnotations = Array.isArray(state?.annotations) ? state.annotations : [];
  const existingSelectedRefs = Array.isArray(state?.selected_refs) ? state.selected_refs : [];
  const existingRevisionPatches = Array.isArray(state?.revision_patches) ? state.revision_patches : [];
  const existingApprovalAttestations = Array.isArray(state?.approval_attestations)
    ? state.approval_attestations
    : [];
  const selectedRefs: unknown[] = [];
  const annotations: unknown[] = [];
  const revisionPatches: unknown[] = [];
  const approvalAttestations: unknown[] = [];

  for (const field of fieldSpecs) {
    const value = submittedValues[field.fieldId];
    if (field.kind === "selection" && !isEmpty(value)) {
      if (Array.isArray(value)) selectedRefs.push(...value);
      else selectedRefs.push(value);
    }
    if (field.kind === "annotation" && !isEmpty(value)) {
      annotations.push({
        block_id: field.blockId,
        target_ref: field.targetRef ?? field.blockId,
        comment: typeof value === "string" ? value : JSON.stringify(value)
      });
    }
    if (field.binding && hasPatchValue(value)) {
      revisionPatches.push({
        artifact: field.binding.artifact,
        path: field.binding.path,
        value
      });
    }
    if (field.kind === "approval") {
      approvalAttestations.push({
        id: field.localId ?? field.fieldId,
        label: field.label ?? field.localId ?? field.fieldId,
        approved: value === true
      });
    }
  }

  const uniqueSelectedRefs = Array.from(new Set([...selectedRefs, ...existingSelectedRefs]));
  if (annotations.length || existingAnnotations.length) {
    payload.annotations = [...annotations, ...existingAnnotations];
  }
  if (uniqueSelectedRefs.length) {
    payload.selected_refs = uniqueSelectedRefs;
  }
  if (revisionPatches.length || existingRevisionPatches.length) {
    payload.revision_patches = [...revisionPatches, ...existingRevisionPatches];
  }
  if (approvalAttestations.length || existingApprovalAttestations.length) {
    payload.approval_attestations = [...approvalAttestations, ...existingApprovalAttestations];
  }
  return payload;
}

export function isA2UISessionSpec(viewSpec: VideoProductionBuddyViewSpec | null | undefined): viewSpec is VideoProductionBuddySessionViewSpec {
  const candidate = viewSpec as ({ contract?: string; version?: string; renderer?: string; a2ui?: unknown } | null | undefined);
  return (
    (candidate?.contract === "genui_session_view" || candidate?.version === "3.0") &&
    candidate.renderer === "a2ui" &&
    isRecord(candidate.a2ui)
  );
}

export function isJsonRenderSurfaceSpec(viewSpec: VideoProductionBuddyViewSpec | null | undefined): viewSpec is VideoProductionBuddySurfaceViewSpec {
  const candidate = viewSpec as ({ contract?: string; version?: string; renderer?: string; elements?: unknown } | null | undefined);
  return (
    (candidate?.contract === "genui_surface_view" || candidate?.version === "2.0") &&
    candidate.renderer === "json-render" &&
    isRecord(candidate.elements)
  );
}

function asComponentNode(value: unknown): A2UIComponentNode | null {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.type !== "string") return null;
  return {
    id: value.id,
    type: value.type,
    props: isRecord(value.props) ? value.props : {},
    children: Array.isArray(value.children) ? value.children.filter((child): child is string => typeof child === "string") : []
  };
}

export function extractA2UISessionSpec(viewSpec: VideoProductionBuddySessionViewSpec): {
  surfaceId: string;
  operations: A2UIOperation[];
  components: A2UIComponentNode[];
  dataModel: Record<string, unknown>;
} {
  const a2ui = viewSpec.a2ui;
  const components = Array.isArray(a2ui.components)
    ? a2ui.components.map(asComponentNode).filter((component): component is A2UIComponentNode => component !== null)
    : [];
  const operations = Array.isArray(a2ui.operations)
    ? a2ui.operations.filter((operation): operation is A2UIOperation => isRecord(operation) && typeof operation.type === "string")
    : [];
  return {
    surfaceId: String(a2ui.surface_id),
    operations,
    components,
    dataModel: isRecord(a2ui.data_model) ? a2ui.data_model : {}
  };
}

function stateDataModel(viewSpec: VideoProductionBuddySessionViewSpec): Record<string, unknown> {
  const state = isRecord(viewSpec.state) ? viewSpec.state : {};
  if (Object.keys(state).length) return state;
  return extractA2UISessionSpec(viewSpec).dataModel;
}

export function buildA2UISubmissionPayload(
  action: string,
  viewSpec: VideoProductionBuddySessionViewSpec,
  state?: Record<string, unknown>
): SubmissionPayload {
  const dataModel = state ?? stateDataModel(viewSpec);
  const values = isRecord(dataModel.values) ? dataModel.values : {};
  const fieldSpecs = collectA2UIFieldSpecs(viewSpec);
  const configuredFieldIds = fieldSpecs.map((field) => field.fieldId);
  const visibleFieldSpecs = fieldSpecs.filter((field) => fieldIsVisible(field, values, configuredFieldIds));
  const visibleFieldIds = new Set(visibleFieldSpecs.map((field) => field.fieldId));
  const submittedValues = fieldSpecs.length
    ? Object.fromEntries(visibleFieldSpecs.map((field) => [field.fieldId, values[field.fieldId]]))
    : values;
  const hiddenBindingKeys = new Set(
    fieldSpecs
      .filter((field) => !visibleFieldIds.has(field.fieldId) && field.binding)
      .map((field) => `${field.binding?.artifact}\u0000${field.binding?.path}`)
  );
  const interactionEvidence = isRecord(dataModel.interaction_evidence)
    ? dataModel.interaction_evidence
    : {};
  const mediaOpened = Array.isArray(interactionEvidence.media_opened)
    ? interactionEvidence.media_opened.filter((item): item is string => typeof item === "string")
    : [];
  const timelineInspected = Array.isArray(interactionEvidence.timeline_inspected)
    ? interactionEvidence.timeline_inspected.filter((item): item is string => typeof item === "string")
    : [];
  const secondsWatched = typeof interactionEvidence.seconds_watched === "number"
    ? interactionEvidence.seconds_watched
    : 0;
  const payload: SubmissionPayload = {
    action,
    nonce: typeof viewSpec.metadata?.submit_nonce === "string"
      ? viewSpec.metadata.submit_nonce
      : undefined,
    values: submittedValues,
    browser_events: [
      {
        type: "action_click",
        timestamp: nowIso(),
        action,
        field_count: fieldSpecs.length ? visibleFieldSpecs.length : Object.keys(values).length
      },
      {
        type: "submit_attempt",
        timestamp: nowIso(),
        action
      }
    ],
    interaction_evidence: {
      media_opened: mediaOpened,
      timeline_inspected: timelineInspected,
      seconds_watched: secondsWatched
    }
  };

  for (const [sourceKey, payloadKey] of [
    ["annotations", "annotations"],
    ["selected_refs", "selected_refs"],
    ["issues", "issues"],
    ["revision_patches", "revision_patches"],
    ["approval_attestations", "approval_attestations"]
  ] as const) {
    const value = dataModel[sourceKey];
    if (Array.isArray(value) && value.length) {
      if (sourceKey === "revision_patches") {
        const filteredPatches = value.filter((item) => {
          if (!isRecord(item) || typeof item.artifact !== "string" || typeof item.path !== "string") return true;
          return !hiddenBindingKeys.has(`${item.artifact}\u0000${item.path}`);
        });
        if (filteredPatches.length) {
          payload[payloadKey] = filteredPatches;
        }
      } else {
        payload[payloadKey] = value;
      }
    }
  }
  return payload;
}

export function resolveSameOriginSubmitUrl(currentHref: string): string | null {
  try {
    const current = new URL(currentHref);
    if (!["http:", "https:"].includes(current.protocol)) return null;
    return new URL("/submit", current.origin).toString();
  } catch {
    return null;
  }
}

export function resolveSameOriginDraftUrl(currentHref: string): string | null {
  try {
    const current = new URL(currentHref);
    if (!["http:", "https:"].includes(current.protocol)) return null;
    return new URL("/draft", current.origin).toString();
  } catch {
    return null;
  }
}

export function safeMediaSrc(rawPath: unknown): string | null {
  if (typeof rawPath !== "string") return null;
  const path = rawPath.trim();
  if (path !== rawPath) return null;
  if (!path.startsWith("/") || path.startsWith("//")) return null;
  if (path.includes("\u0000")) return null;
  const lower = path.toLowerCase();
  if (
    lower.startsWith("http:") ||
    lower.startsWith("https:") ||
    lower.startsWith("file:") ||
    lower.startsWith("data:") ||
    lower.startsWith("javascript:")
  ) {
    return null;
  }
  const safeMediaPath = /^\/media\/(?:[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)(?:\/(?:[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*))*$/;
  if (!safeMediaPath.test(path)) return null;
  return path;
}
