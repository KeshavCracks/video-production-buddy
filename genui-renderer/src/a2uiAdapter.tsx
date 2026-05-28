import { createCatalog, extractSchema } from "@copilotkit/a2ui-renderer";
import {
  A2UIProvider,
  A2UIRenderer,
  ComponentNode,
  ComponentRegistry,
  type A2UIComponentProps,
  type ServerToClientMessage,
  useA2UIActions
} from "@a2ui/react";
import type { MessageProcessor } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  buildA2UISubmissionPayload,
  extractA2UISessionSpec,
  resolveSameOriginDraftUrl,
  resolveSameOriginSubmitUrl,
  safeMediaSrc,
  type BrowserEvent,
  type A2UIComponentNode,
  type VideoProductionBuddySessionViewSpec
} from "./payload";

type DataModel = Record<string, unknown>;
type MediaRef = {
  id: string;
  kind: string;
  title: string;
  path?: string;
  text?: string;
  alt?: string;
};

type RefItem = {
  id: string;
  label?: string;
  title?: string;
  artifact?: string;
  path?: string;
  source?: string;
  summary?: string;
};

type ChoiceItem = {
  value: string;
  label: string;
  description?: string;
  recommended?: boolean;
};

type VisibleIf = {
  field: string;
  operator: "equals" | "not_equals" | "not_empty" | "empty";
  value?: unknown;
};

type FieldItem = {
  id: string;
  label: string;
  type: string;
  required?: boolean;
  default?: unknown;
  help_text?: string;
  placeholder?: string;
  min?: number;
  max?: number;
  binding?: {
    artifact: string;
    path: string;
  };
  visible_if?: VisibleIf;
  choices?: ChoiceItem[];
};

const surfacePropsSchema = z.object({
  title: z.string(),
  description: z.string().optional(),
  mediaRefs: z.array(z.record(z.string(), z.unknown())).optional(),
  artifactRefs: z.array(z.record(z.string(), z.unknown())).optional(),
  traceRefs: z.array(z.record(z.string(), z.unknown())).optional(),
  fields: z.array(z.record(z.string(), z.unknown())).optional(),
  choices: z.array(z.record(z.string(), z.unknown())).optional(),
  reviewItems: z.array(z.record(z.string(), z.unknown())).optional(),
  selection: z.record(z.string(), z.unknown()).optional(),
  requiredEvidence: z.array(z.string()).optional(),
  allowedTargets: z.array(z.string()).optional(),
  allowedStatuses: z.array(z.string()).optional()
});

const productPanelPropsSchema = z.object({
  title: z.string(),
  description: z.string().optional(),
  mediaRefs: z.array(z.record(z.string(), z.unknown())).optional(),
  artifactRefs: z.array(z.record(z.string(), z.unknown())).optional(),
  traceRefs: z.array(z.record(z.string(), z.unknown())).optional(),
  timelineItems: z.array(z.record(z.string(), z.unknown())).optional(),
  artifactItems: z.array(z.record(z.string(), z.unknown())).optional(),
  decisionItems: z.array(z.record(z.string(), z.unknown())).optional(),
  budgetCostItems: z.array(z.record(z.string(), z.unknown())).optional(),
  pendingResponses: z.array(z.record(z.string(), z.unknown())).optional(),
  staleSessions: z.array(z.record(z.string(), z.unknown())).optional(),
  validationBlockers: z.array(z.record(z.string(), z.unknown())).optional(),
  journalItems: z.array(z.record(z.string(), z.unknown())).optional(),
  operationEvents: z.array(z.record(z.string(), z.unknown())).optional(),
  reviewItems: z.array(z.record(z.string(), z.unknown())).optional(),
  choices: z.array(z.record(z.string(), z.unknown())).optional(),
  requiredEvidence: z.array(z.string()).optional(),
  allowedTargets: z.array(z.string()).optional(),
  allowedStatuses: z.array(z.string()).optional(),
  session: z.record(z.string(), z.unknown()).optional(),
  decision: z.record(z.string(), z.unknown()).optional(),
  routingDecisionId: z.string().optional(),
  sourceRequestId: z.string().optional(),
  journalPath: z.string().optional()
});

const catalogDefinitions = {
  SessionShell: {
    description: "Video Production Buddy GenUI session shell.",
    props: z.object({
      title: z.string(),
      description: z.string().optional(),
      mode: z.string(),
      projectId: z.string().optional(),
      stage: z.string().optional(),
      gate: z.string().optional()
    })
  },
  GateWorkspace: {
    description: "Approval gate workspace with trace, artifact, and attestation controls.",
    props: surfacePropsSchema
  },
  MediaReviewRoom: {
    description: "Media-native review room with anchored annotation evidence.",
    props: surfacePropsSchema
  },
  IssueTracker: {
    description: "Structured issue lifecycle tracker for human review feedback.",
    props: surfacePropsSchema
  },
  ProjectCockpit: {
    description: "Read-only project cockpit for status, artifacts, decisions, and blockers.",
    props: surfacePropsSchema
  },
  BackgroundStatus: {
    description: "Passive progress surface for long-running local work.",
    props: surfacePropsSchema
  },
  MediaTimeline: {
    description: "GenUI media timeline panel backed by session evidence.",
    props: productPanelPropsSchema
  },
  MediaComparison: {
    description: "GenUI side-by-side media and option comparison panel.",
    props: productPanelPropsSchema
  },
  RegionAnnotation: {
    description: "GenUI normalized region annotation guidance panel.",
    props: productPanelPropsSchema
  },
  IssueBoard: {
    description: "GenUI issue lifecycle board backed by session issues.",
    props: productPanelPropsSchema
  },
  ArtifactTrace: {
    description: "GenUI artifact and traceability panel.",
    props: productPanelPropsSchema
  },
  RevisionPatchPreview: {
    description: "GenUI pending patch preview for agent validation.",
    props: productPanelPropsSchema
  },
  ApprovalAttestation: {
    description: "GenUI approval evidence panel.",
    props: productPanelPropsSchema
  },
  LiveStatusPanel: {
    description: "GenUI AG-UI event and lifecycle status panel.",
    props: productPanelPropsSchema
  },
  InteractionJournalPanel: {
    description: "GenUI journal and routing decision panel.",
    props: productPanelPropsSchema
  },
  OperationTimeline: {
    description: "GenUI lifecycle and tool-operation timeline panel.",
    props: productPanelPropsSchema
  },
  ReviewCompletionPanel: {
    description: "GenUI required-evidence and completion status panel.",
    props: productPanelPropsSchema
  },
  DurableDecisionPanel: {
    description: "GenUI interrupt/resume decision metadata panel.",
    props: productPanelPropsSchema
  },
  ProposalLock: {
    description: "Proposal-stage approval workspace.",
    props: surfacePropsSchema
  },
  ScriptReviewWorkspace: {
    description: "Script-stage structured review workspace.",
    props: surfacePropsSchema
  },
  ScenePlanWorkspace: {
    description: "Scene-plan structured review workspace.",
    props: surfacePropsSchema
  },
  ProductReferenceApproval: {
    description: "Product-reference approval workspace.",
    props: surfacePropsSchema
  },
  SampleReview: {
    description: "Generated sample review workspace.",
    props: surfacePropsSchema
  },
  AssetReview: {
    description: "Asset review workspace.",
    props: surfacePropsSchema
  },
  MusicReview: {
    description: "Music review workspace.",
    props: surfacePropsSchema
  },
  PublishReview: {
    description: "Publish readiness review workspace.",
    props: surfacePropsSchema
  },
  ActionBar: {
    description: "Submit actions that write only ui_session_response.",
    props: z.object({
      actions: z.array(z.record(z.string(), z.unknown())),
      previewOnly: z.boolean().optional()
    })
  }
};

export const videoProductionBuddyA2UISchema = extractSchema(catalogDefinitions as never);
export type VideoProductionBuddyA2UIMessageProcessor = MessageProcessor<any>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function refItemsFromProps(props: Record<string, unknown>, key: "artifactRefs" | "traceRefs"): RefItem[] {
  const refs = props[key];
  if (!Array.isArray(refs)) return [];
  return refs
    .filter((item): item is Record<string, unknown> => isRecord(item))
    .map((item) => ({
      id: String(item.id ?? ""),
      label: typeof item.label === "string" ? item.label : undefined,
      title: typeof item.title === "string" ? item.title : undefined,
      artifact: typeof item.artifact === "string" ? item.artifact : undefined,
      path: typeof item.path === "string" ? item.path : undefined,
      source: typeof item.source === "string" ? item.source : undefined,
      summary: typeof item.summary === "string" ? item.summary : undefined
    }))
    .filter((item) => item.id);
}

function mediaRefsFromProps(props: Record<string, unknown>): MediaRef[] {
  const mediaRefs = props.mediaRefs;
  if (!Array.isArray(mediaRefs)) return [];
  return mediaRefs
    .filter((item): item is Record<string, unknown> => isRecord(item))
    .map((item) => ({
      id: String(item.id ?? ""),
      kind: String(item.kind ?? "path"),
      title: String(item.title ?? item.id ?? "Media"),
      path: typeof item.path === "string" ? item.path : undefined,
      text: typeof item.text === "string" ? item.text : undefined,
      alt: typeof item.alt === "string" ? item.alt : undefined
    }))
    .filter((item) => item.id);
}

function choicesFromProps(props: Record<string, unknown>): ChoiceItem[] {
  const choices = props.choices;
  if (!Array.isArray(choices)) return [];
  return choices
    .filter((item): item is Record<string, unknown> => isRecord(item))
    .map((item) => ({
      value: String(item.value ?? ""),
      label: String(item.label ?? item.value ?? ""),
      description: typeof item.description === "string" ? item.description : undefined,
      recommended: item.recommended === true
    }))
    .filter((item) => item.value && item.label);
}

function visibleIfFromValue(value: unknown): VisibleIf | undefined {
  if (!isRecord(value) || typeof value.field !== "string" || typeof value.operator !== "string") return undefined;
  if (!["equals", "not_equals", "not_empty", "empty"].includes(value.operator)) return undefined;
  return {
    field: value.field,
    operator: value.operator as VisibleIf["operator"],
    value: value.value
  };
}

function fieldsFromProps(props: Record<string, unknown>): FieldItem[] {
  const fields = props.fields;
  if (!Array.isArray(fields)) return [];
  return fields
    .filter((item): item is Record<string, unknown> => isRecord(item))
    .map((item) => {
      const binding = isRecord(item.binding) && typeof item.binding.artifact === "string" && typeof item.binding.path === "string"
        ? { artifact: item.binding.artifact, path: item.binding.path }
        : undefined;
      return {
        id: String(item.id ?? ""),
        label: String(item.label ?? item.id ?? ""),
        type: String(item.type ?? "text"),
        required: item.required === true,
        default: item.default,
        help_text: typeof item.help_text === "string" ? item.help_text : undefined,
        placeholder: typeof item.placeholder === "string" ? item.placeholder : undefined,
        min: typeof item.min === "number" ? item.min : undefined,
        max: typeof item.max === "number" ? item.max : undefined,
        binding,
        visible_if: visibleIfFromValue(item.visible_if),
        choices: isRecord(item) ? choicesFromProps({ choices: item.choices }) : []
      };
    })
    .filter((item) => item.id && item.label);
}

function dataArray(model: DataModel, key: string): unknown[] {
  const value = model[key];
  return Array.isArray(value) ? value : [];
}

function updateArray(model: DataModel, key: string, next: unknown[]): DataModel {
  return { ...model, [key]: next };
}

function modelValues(model: DataModel): Record<string, unknown> {
  return isRecord(model.values) ? model.values : {};
}

function fieldValueIsEmpty(value: unknown): boolean {
  if (value === undefined || value === null) return true;
  if (typeof value === "string") return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "boolean") return value === false;
  return false;
}

function resolveVisibleIfFieldId(field: FieldItem, fields: FieldItem[]): string | null {
  const reference = field.visible_if?.field;
  if (!reference) return null;
  if (fields.some((candidate) => candidate.id === reference)) return reference;
  const suffixMatches = fields.map((candidate) => candidate.id).filter((fieldId) => fieldId.endsWith(`.${reference}`));
  return suffixMatches.length === 1 ? suffixMatches[0] : null;
}

function fieldIsVisible(field: FieldItem, fields: FieldItem[], model: DataModel): boolean {
  const visibleIf = field.visible_if;
  if (!visibleIf) return true;
  const referenceId = resolveVisibleIfFieldId(field, fields);
  if (!referenceId) return true;
  const value = modelValues(model)[referenceId];
  if (visibleIf.operator === "not_empty") return !fieldValueIsEmpty(value);
  if (visibleIf.operator === "empty") return fieldValueIsEmpty(value);
  if (visibleIf.operator === "equals") return value === visibleIf.value;
  if (visibleIf.operator === "not_equals") return value !== visibleIf.value;
  return true;
}

function updateRevisionPatch(model: DataModel, field: FieldItem, value: unknown): DataModel {
  if (!field.binding) return model;
  const previous = dataArray(model, "revision_patches").filter(isRecord);
  const next = [
    ...previous.filter((item) => item.artifact !== field.binding?.artifact || item.path !== field.binding?.path),
    { artifact: field.binding.artifact, path: field.binding.path, value }
  ];
  return updateArray(model, "revision_patches", next);
}

function updateFieldValue(model: DataModel, field: FieldItem, value: unknown): DataModel {
  const nextModel = {
    ...model,
    values: {
      ...modelValues(model),
      [field.id]: value
    }
  };
  return updateRevisionPatch(nextModel, field, value);
}

function updateSelectionValue(
  model: DataModel,
  fieldId: string,
  value: string | string[],
  binding?: { artifact: string; path: string }
): DataModel {
  const selected = Array.isArray(value) ? value : value ? [value] : [];
  const selectionField: FieldItem = {
    id: fieldId,
    label: fieldId,
    type: Array.isArray(value) ? "multiselect" : "radio",
    binding
  };
  return {
    ...updateRevisionPatch(
      {
        ...model,
        selected_refs: selected,
        values: {
          ...modelValues(model),
          [fieldId]: value
        }
      },
      selectionField,
      value
    )
  };
}

function updateEvidence(model: DataModel, key: "media_opened" | "timeline_inspected", mediaId: string): DataModel {
  const evidence = isRecord(model.interaction_evidence) ? model.interaction_evidence : {};
  const previous = asStringArray(evidence[key]);
  return {
    ...model,
    interaction_evidence: {
      media_opened: key === "media_opened" ? Array.from(new Set([...previous, mediaId])) : asStringArray(evidence.media_opened),
      timeline_inspected: key === "timeline_inspected" ? Array.from(new Set([...previous, mediaId])) : asStringArray(evidence.timeline_inspected),
      seconds_watched: typeof evidence.seconds_watched === "number" ? evidence.seconds_watched : 0
    }
  };
}

function addWatchedSeconds(model: DataModel, seconds: number): DataModel {
  const evidence = isRecord(model.interaction_evidence) ? model.interaction_evidence : {};
  return {
    ...model,
    interaction_evidence: {
      media_opened: asStringArray(evidence.media_opened),
      timeline_inspected: asStringArray(evidence.timeline_inspected),
      seconds_watched: Math.max(Number(evidence.seconds_watched ?? 0), seconds)
    }
  };
}

function setApprovalAttestation(model: DataModel, surfaceId: string, label: string, approved: boolean): DataModel {
  const previous = dataArray(model, "approval_attestations").filter(isRecord);
  const next = [
    ...previous.filter((item) => item.id !== surfaceId),
    { id: surfaceId, label, approved }
  ];
  return updateArray(model, "approval_attestations", next);
}

const workspaceSurfaceTypes = new Set([
  "GateWorkspace",
  "ProposalLock",
  "ScriptReviewWorkspace",
  "ScenePlanWorkspace",
  "ProductReferenceApproval",
  "SampleReview",
  "AssetReview",
  "MusicReview",
  "PublishReview"
]);

type SessionRendererContextValue = {
  spec: VideoProductionBuddySessionViewSpec;
  model: DataModel;
  setModel: React.Dispatch<React.SetStateAction<DataModel>>;
  status: string;
  setStatus: React.Dispatch<React.SetStateAction<string>>;
  eventLog: BrowserEvent[];
  registry: ComponentRegistry;
};

const SessionRendererContext = createContext<SessionRendererContextValue | null>(null);

function useSessionRendererContext(): SessionRendererContextValue {
  const context = useContext(SessionRendererContext);
  if (!context) throw new Error("Video Production Buddy A2UI components must be rendered inside SessionRendererContext");
  return context;
}

function nodeFromA2UI(node: A2UIComponentProps["node"]): A2UIComponentNode {
  return {
    id: String(node.id),
    type: String(node.type),
    props: isRecord(node.properties) ? node.properties : {},
    children: []
  };
}

function childNodesFromProps(props: Record<string, unknown>): A2UIComponentProps["node"][] {
  const children = props.children;
  return Array.isArray(children)
    ? children.filter((child): child is A2UIComponentProps["node"] => isRecord(child) && typeof child.id === "string" && typeof child.type === "string")
    : [];
}

function SessionShellView({
  node,
  children
}: {
  node: A2UIComponentNode;
  children: React.ReactNode;
}) {
  const props = node.props;
  return (
    <main className="om-shell om-shell-workspace om-session-shell">
      <header className="om-header om-session-header">
        <div>
          <p className="om-eyebrow">Video Production Buddy GenUI · A2UI + AG-UI</p>
          <h1>{String(props.title ?? "GenUI session")}</h1>
          {typeof props.description === "string" ? <p>{props.description}</p> : null}
        </div>
        <dl className="om-meta">
          <div><dt>Mode</dt><dd>{String(props.mode ?? "session")}</dd></div>
          <div><dt>Stage</dt><dd>{String(props.stage ?? "unknown")}</dd></div>
          <div><dt>Gate</dt><dd>{String(props.gate ?? "unknown")}</dd></div>
          <div><dt>Framework</dt><dd>A2UI</dd></div>
        </dl>
      </header>
      <div className="om-session-workspace">{children}</div>
    </main>
  );
}

function ReferenceList({ title, refs }: { title: string; refs: RefItem[] }) {
  return (
    <div className="om-session-ref-section">
      <h3>{title}</h3>
      {refs.length ? (
        <div className="om-session-ref-list">
          {refs.map((ref) => (
            <article className="om-trace-item" key={ref.id}>
              <strong>{ref.label ?? ref.title ?? ref.id}</strong>
              {ref.artifact || ref.path ? <small>{[ref.artifact, ref.path].filter(Boolean).join(" · ")}</small> : null}
              {ref.source ? <small>{ref.source}</small> : null}
              {ref.summary ? <p>{ref.summary}</p> : null}
            </article>
          ))}
        </div>
      ) : <p className="om-help">No linked {title.toLowerCase()}.</p>}
    </div>
  );
}

function ChoiceSelector({
  props,
  model,
  setModel
}: {
  props: Record<string, unknown>;
  model: DataModel;
  setModel: React.Dispatch<React.SetStateAction<DataModel>>;
}) {
  const choices = choicesFromProps(props);
  const selection = isRecord(props.selection) ? props.selection : {};
  if (!choices.length) return null;
  const fieldId = typeof selection.fieldId === "string" ? selection.fieldId : "selection";
  const allowMultiple = selection.allowMultiple === true;
  const binding = isRecord(selection.binding) && typeof selection.binding.artifact === "string" && typeof selection.binding.path === "string"
    ? { artifact: selection.binding.artifact, path: selection.binding.path }
    : undefined;
  const currentValue = modelValues(model)[fieldId];
  const selectedValues = Array.isArray(currentValue)
    ? currentValue.filter((item): item is string => typeof item === "string")
    : typeof currentValue === "string" && currentValue
      ? [currentValue]
      : [];

  function toggle(value: string, checked: boolean) {
    const next = allowMultiple
      ? checked
        ? Array.from(new Set([...selectedValues, value]))
        : selectedValues.filter((item) => item !== value)
      : value;
    setModel((current) => updateSelectionValue(current, fieldId, next, binding));
  }

  return (
    <div className="om-session-choice-panel">
      <h3>{String(selection.label ?? "Select an option")}</h3>
      <div className="om-choice-grid">
        {choices.map((choice) => (
          <label className={selectedValues.includes(choice.value) ? "om-choice-card om-choice-card-selected" : "om-choice-card"} key={choice.value}>
            <input
              type={allowMultiple ? "checkbox" : "radio"}
              name={fieldId}
              value={choice.value}
              checked={selectedValues.includes(choice.value)}
              onChange={(event) => toggle(choice.value, event.target.checked)}
            />
            <span>
              <strong>{choice.label}</strong>
              {choice.recommended ? <span className="om-choice-badge">Recommended</span> : null}
              {choice.description ? <small>{choice.description}</small> : null}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

function FieldControl({
  field,
  model,
  setModel
}: {
  field: FieldItem;
  model: DataModel;
  setModel: React.Dispatch<React.SetStateAction<DataModel>>;
}) {
  const values = modelValues(model);
  const value = values[field.id] ?? field.default ?? (field.type === "checkbox" ? false : field.type === "multiselect" ? [] : "");
  const choices = field.choices ?? [];

  function setValue(next: unknown) {
    setModel((current) => updateFieldValue(current, field, next));
  }

  let control: React.ReactNode;
  if (field.type === "textarea") {
    control = (
      <textarea
        className="om-control om-textarea"
        value={typeof value === "string" ? value : ""}
        placeholder={field.placeholder}
        onChange={(event) => setValue(event.target.value)}
      />
    );
  } else if (field.type === "select" || field.type === "radio") {
    control = (
      <select className="om-control" value={typeof value === "string" ? value : ""} onChange={(event) => setValue(event.target.value)}>
        <option value="">Select...</option>
        {choices.map((choice) => <option value={choice.value} key={choice.value}>{choice.label}</option>)}
      </select>
    );
  } else if (field.type === "multiselect") {
    const selected = Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
    control = (
      <div className="om-choice-grid">
        {choices.map((choice) => (
          <label className="om-inline-check" key={choice.value}>
            <input
              type="checkbox"
              checked={selected.includes(choice.value)}
              onChange={(event) => {
                const next = event.target.checked
                  ? Array.from(new Set([...selected, choice.value]))
                  : selected.filter((item) => item !== choice.value);
                setValue(next);
              }}
            />
            <span>{choice.label}</span>
          </label>
        ))}
      </div>
    );
  } else if (field.type === "checkbox" || field.type === "approval") {
    control = (
      <label className="om-inline-check">
        <input type="checkbox" checked={value === true} onChange={(event) => setValue(event.target.checked)} />
        <span>{field.help_text ?? field.label}</span>
      </label>
    );
  } else if (field.type === "number") {
    control = (
      <input
        className="om-control"
        type="number"
        min={field.min}
        max={field.max}
        value={typeof value === "number" || typeof value === "string" ? value : ""}
        onChange={(event) => setValue(event.target.value === "" ? "" : Number(event.target.value))}
      />
    );
  } else {
    control = (
      <input
        className="om-control"
        type={field.type === "url" ? "url" : "text"}
        value={typeof value === "string" ? value : ""}
        placeholder={field.placeholder}
        onChange={(event) => setValue(event.target.value)}
      />
    );
  }

  return (
    <label className="om-field">
      <span className="om-field-label">
        {field.label}
        {field.required ? <span className="om-required">Required</span> : null}
      </span>
      {control}
      {field.help_text && field.type !== "checkbox" && field.type !== "approval" ? <small className="om-help">{field.help_text}</small> : null}
    </label>
  );
}

function GateWorkspaceView({
  node,
  model,
  setModel
}: {
  node: A2UIComponentNode;
  model: DataModel;
  setModel: React.Dispatch<React.SetStateAction<DataModel>>;
}) {
  const requiredEvidence = asStringArray(node.props.requiredEvidence);
  const requiresApproval = requiredEvidence.includes("approval_attested");
  const attestations = dataArray(model, "approval_attestations").filter(isRecord);
  const approved = attestations.some((item) => item.id === node.id && item.approved === true);
  const artifacts = refItemsFromProps(node.props, "artifactRefs");
  const traces = refItemsFromProps(node.props, "traceRefs");
  const mediaRefs = mediaRefsFromProps(node.props);
  const fields = fieldsFromProps(node.props);
  const visibleFields = fields.filter((field) => fieldIsVisible(field, fields, model));
  const approvalLabel = `I reviewed and approve ${String(node.props.title ?? "this workspace")}.`;

  return (
    <section className="om-surface-block om-session-gate-workspace">
      <header>
        <h2>{String(node.props.title ?? "Gate workspace")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-session-workspace-summary">
        <div>
          <span className="om-session-kicker">Surface</span>
          <strong>{node.type}</strong>
        </div>
        <div>
          <span className="om-session-kicker">Required Evidence</span>
          <strong>{requiredEvidence.length ? requiredEvidence.join(", ") : "none"}</strong>
        </div>
        <div>
          <span className="om-session-kicker">Media Refs</span>
          <strong>{mediaRefs.length}</strong>
        </div>
      </div>
      {requiresApproval ? (
        <label className="om-inline-check om-session-attestation">
          <input
            type="checkbox"
            checked={approved}
            onChange={(event) => setModel((current) => setApprovalAttestation(current, node.id, approvalLabel, event.target.checked))}
          />
          <span>
            <strong>Approval attestation</strong>
            <small>{approvalLabel}</small>
          </span>
        </label>
      ) : null}
      <ChoiceSelector props={node.props} model={model} setModel={setModel} />
      {visibleFields.length ? (
        <div className="om-session-field-panel">
          <h3>Structured Inputs</h3>
          {visibleFields.map((field) => <FieldControl field={field} model={model} setModel={setModel} key={field.id} />)}
        </div>
      ) : null}
      <div className="om-session-ref-grid">
        <ReferenceList title="Artifact Links" refs={artifacts} />
        <ReferenceList title="Trace Links" refs={traces} />
      </div>
    </section>
  );
}

function MediaElement({
  media,
  onEvidence,
  onCurrentTime,
  onRegion
}: {
  media: MediaRef;
  onEvidence: (kind: "media_opened" | "timeline_inspected", id: string) => void;
  onCurrentTime?: (seconds: number) => void;
  onRegion?: (region: { x: number; y: number; width: number; height: number }) => void;
}) {
  const src = safeMediaSrc(media.path);
  if (media.kind === "text") {
    return <pre className="om-session-media-text">{media.text}</pre>;
  }
  if (!src) {
    return <div className="om-error">Unsafe or unavailable media path for {media.title}</div>;
  }
  if (media.kind === "video" || src.endsWith(".mp4") || src.endsWith(".webm") || src.endsWith(".mov")) {
    return (
      <video
        className="om-session-player"
        controls
        src={src}
        onLoadedMetadata={() => onEvidence("media_opened", media.id)}
        onSeeked={(event) => {
          onEvidence("timeline_inspected", media.id);
          onCurrentTime?.(event.currentTarget.currentTime);
        }}
        onTimeUpdate={(event) => onCurrentTime?.(event.currentTarget.currentTime)}
        onPlay={() => onEvidence("media_opened", media.id)}
      />
    );
  }
  if (media.kind === "audio" || src.endsWith(".mp3") || src.endsWith(".wav") || src.endsWith(".m4a")) {
    return (
      <audio
        controls
        src={src}
        onLoadedMetadata={() => onEvidence("media_opened", media.id)}
        onTimeUpdate={(event) => onCurrentTime?.(event.currentTarget.currentTime)}
        onSeeked={(event) => {
          onEvidence("timeline_inspected", media.id);
          onCurrentTime?.(event.currentTarget.currentTime);
        }}
      />
    );
  }
  return (
    <img
      className="om-session-image"
      src={src}
      alt={media.alt ?? media.title}
      onLoad={() => onEvidence("media_opened", media.id)}
      onClick={(event) => {
        const rect = event.currentTarget.getBoundingClientRect();
        const x = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
        const y = Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height));
        onRegion?.({
          x: Number(x.toFixed(3)),
          y: Number(y.toFixed(3)),
          width: 0.12,
          height: 0.12
        });
      }}
    />
  );
}

function MediaReviewRoomView({
  node,
  model,
  setModel
}: {
  node: A2UIComponentNode;
  model: DataModel;
  setModel: React.Dispatch<React.SetStateAction<DataModel>>;
}) {
  const mediaRefs = mediaRefsFromProps(node.props);
  const requiredEvidence = asStringArray(node.props.requiredEvidence);
  const requiresApproval = requiredEvidence.includes("approval_attested");
  const approvalLabel = `I reviewed and approve ${String(node.props.title ?? "this media review")}.`;
  const approved = dataArray(model, "approval_attestations")
    .filter(isRecord)
    .some((item) => item.id === node.id && item.approved === true);
  const [targetRef, setTargetRef] = useState(mediaRefs[0]?.id ?? "");
  const [comment, setComment] = useState("");
  const [timestamp, setTimestamp] = useState("");
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");
  const [regionX, setRegionX] = useState("");
  const [regionY, setRegionY] = useState("");
  const [regionWidth, setRegionWidth] = useState("");
  const [regionHeight, setRegionHeight] = useState("");
  const [currentPlaybackSeconds, setCurrentPlaybackSeconds] = useState<number | null>(null);

  function markEvidence(kind: "media_opened" | "timeline_inspected", mediaId: string) {
    setModel((current) => addWatchedSeconds(updateEvidence(current, kind, mediaId), 1));
  }

  function addAnnotation() {
    if (!targetRef || !comment.trim()) return;
    const timestampSeconds = Number(timestamp);
    const startSeconds = Number(rangeStart);
    const endSeconds = Number(rangeEnd);
    const x = Number(regionX);
    const y = Number(regionY);
    const width = Number(regionWidth);
    const height = Number(regionHeight);
    const hasRange = Number.isFinite(startSeconds) && Number.isFinite(endSeconds) && startSeconds >= 0 && endSeconds >= startSeconds;
    const hasRegion = [x, y, width, height].every((value) => Number.isFinite(value) && value >= 0 && value <= 1);
    const annotation = {
      surface_id: node.id,
      target_ref: targetRef,
      comment: comment.trim(),
      ...(Number.isFinite(timestampSeconds) && timestampSeconds >= 0 ? { timestamp_seconds: timestampSeconds } : {}),
      ...(hasRange ? { time_range: { start_seconds: startSeconds, end_seconds: endSeconds } } : {}),
      ...(hasRegion ? { region: { x, y, width, height } } : {})
    };
    setModel((current) => updateArray(current, "annotations", [...dataArray(current, "annotations"), annotation]));
    setComment("");
  }

  return (
    <section className="om-surface-block om-session-media-room">
      <header>
        <h2>{String(node.props.title ?? "Media review")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-session-media-grid">
        <div className="om-session-media-stage">
          {mediaRefs.map((media) => (
            <article className="om-session-media-card" key={media.id}>
              <h3>{media.title}</h3>
              <MediaElement
                media={media}
                onEvidence={markEvidence}
                onCurrentTime={(seconds) => setCurrentPlaybackSeconds(Number(seconds.toFixed(2)))}
                onRegion={(region) => {
                  setTargetRef(media.id);
                  setRegionX(String(region.x));
                  setRegionY(String(region.y));
                  setRegionWidth(String(region.width));
                  setRegionHeight(String(region.height));
                }}
              />
              <div className="om-product-keyframe-strip" aria-label={`${media.title} review markers`}>
                {[0, 25, 50, 75, 100].map((percent) => (
                  <button
                    type="button"
                    key={`${media.id}-${percent}`}
                    onClick={() => {
                      setTargetRef(media.id);
                      setTimestamp(percent === 0 ? "0" : "");
                      markEvidence("timeline_inspected", media.id);
                    }}
                  >
                    <span>{percent}%</span>
                  </button>
                ))}
              </div>
              <div className="om-session-evidence-buttons">
                <button type="button" onClick={() => markEvidence("media_opened", media.id)}>Mark opened</button>
                <button type="button" onClick={() => markEvidence("timeline_inspected", media.id)}>Mark timeline checked</button>
              </div>
            </article>
          ))}
        </div>
        <div className="om-session-review-panel">
          {requiresApproval ? (
            <label className="om-inline-check om-session-attestation">
              <input
                type="checkbox"
                checked={approved}
                onChange={(event) => setModel((current) => setApprovalAttestation(current, node.id, approvalLabel, event.target.checked))}
              />
              <span>
                <strong>Approval attestation</strong>
                <small>{approvalLabel}</small>
              </span>
            </label>
          ) : null}
          <label className="om-field">
            <span className="om-field-label">Target</span>
            <select className="om-control" value={targetRef} onChange={(event) => setTargetRef(event.target.value)}>
              {mediaRefs.map((media) => <option key={media.id} value={media.id}>{media.title}</option>)}
            </select>
          </label>
          <label className="om-field">
            <span className="om-field-label">Timestamp seconds</span>
            <input className="om-control" value={timestamp} onChange={(event) => setTimestamp(event.target.value)} inputMode="decimal" />
          </label>
          <button
            type="button"
            className="om-action"
            disabled={currentPlaybackSeconds === null}
            onClick={() => currentPlaybackSeconds !== null && setTimestamp(String(currentPlaybackSeconds))}
          >
            Use current time
          </button>
          <div className="om-session-inline-grid">
            <label className="om-field">
              <span className="om-field-label">Range start seconds</span>
              <input className="om-control" value={rangeStart} onChange={(event) => setRangeStart(event.target.value)} inputMode="decimal" />
            </label>
            <label className="om-field">
              <span className="om-field-label">Range end seconds</span>
              <input className="om-control" value={rangeEnd} onChange={(event) => setRangeEnd(event.target.value)} inputMode="decimal" />
            </label>
          </div>
          <div className="om-session-evidence-buttons">
            <button
              type="button"
              disabled={currentPlaybackSeconds === null}
              onClick={() => currentPlaybackSeconds !== null && setRangeStart(String(currentPlaybackSeconds))}
            >
              Set range start
            </button>
            <button
              type="button"
              disabled={currentPlaybackSeconds === null}
              onClick={() => currentPlaybackSeconds !== null && setRangeEnd(String(currentPlaybackSeconds))}
            >
              Set range end
            </button>
          </div>
          <div className="om-session-region-grid">
            <label className="om-field">
              <span className="om-field-label">Region x</span>
              <input className="om-control" value={regionX} onChange={(event) => setRegionX(event.target.value)} inputMode="decimal" />
            </label>
            <label className="om-field">
              <span className="om-field-label">Region y</span>
              <input className="om-control" value={regionY} onChange={(event) => setRegionY(event.target.value)} inputMode="decimal" />
            </label>
            <label className="om-field">
              <span className="om-field-label">Region width</span>
              <input className="om-control" value={regionWidth} onChange={(event) => setRegionWidth(event.target.value)} inputMode="decimal" />
            </label>
            <label className="om-field">
              <span className="om-field-label">Region height</span>
              <input className="om-control" value={regionHeight} onChange={(event) => setRegionHeight(event.target.value)} inputMode="decimal" />
            </label>
          </div>
          <label className="om-field">
            <span className="om-field-label">Annotation</span>
            <textarea className="om-control om-textarea" value={comment} onChange={(event) => setComment(event.target.value)} />
          </label>
          <button type="button" className="om-action" onClick={addAnnotation}>Add annotation</button>
          <EvidenceSummary model={model} />
        </div>
      </div>
    </section>
  );
}

function EvidenceSummary({ model }: { model: DataModel }) {
  const evidence = isRecord(model.interaction_evidence) ? model.interaction_evidence : {};
  return (
    <div className="om-session-evidence">
      <strong>Evidence</strong>
      <span>Opened: {asStringArray(evidence.media_opened).join(", ") || "none"}</span>
      <span>Timeline: {asStringArray(evidence.timeline_inspected).join(", ") || "none"}</span>
      <span>Watched: {String(evidence.seconds_watched ?? 0)}s</span>
    </div>
  );
}

function IssueTrackerView({
  node,
  model,
  setModel
}: {
  node: A2UIComponentNode;
  model: DataModel;
  setModel: React.Dispatch<React.SetStateAction<DataModel>>;
}) {
  const allowedTargets = asStringArray(node.props.allowedTargets);
  const allowedStatuses = asStringArray(node.props.allowedStatuses);
  const defaultStatus = allowedStatuses.includes("open") ? "open" : allowedStatuses[0] ?? "open";
  const issues = dataArray(model, "issues").filter(isRecord);
  const [requestedChange, setRequestedChange] = useState("");
  const [targetRef, setTargetRef] = useState(allowedTargets[0] ?? "");
  const [severity, setSeverity] = useState("blocking");
  const [status, setStatus] = useState(defaultStatus);

  function addIssue() {
    if (!targetRef || !requestedChange.trim()) return;
    const nextIssue = {
      id: `issue-${Date.now()}`,
      target_ref: targetRef,
      status,
      severity,
      requested_change: requestedChange.trim()
    };
    setModel((current) => updateArray(current, "issues", [...dataArray(current, "issues"), nextIssue]));
    setRequestedChange("");
  }

  function updateIssue(issueId: unknown, updates: Record<string, unknown>) {
    setModel((current) => updateArray(
      current,
      "issues",
      dataArray(current, "issues").map((issue) => (
        isRecord(issue) && issue.id === issueId ? { ...issue, ...updates } : issue
      ))
    ));
  }

  return (
    <section className="om-surface-block om-session-issues">
      <header>
        <h2>{String(node.props.title ?? "Issues")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-session-issue-list">
        {issues.length ? issues.map((issue) => (
          <article className="om-trace-item" key={String(issue.id)}>
            <strong>{String(issue.id)}</strong>
            <small>{String(issue.status)} · {String(issue.severity)} · {String(issue.target_ref)}</small>
            <p>{String(issue.requested_change)}</p>
            <div className="om-product-issue-actions">
              <button type="button" onClick={() => updateIssue(issue.id, { status: "resolved" })}>Resolve</button>
              <button type="button" onClick={() => updateIssue(issue.id, { status: "needs_recheck" })}>Needs recheck</button>
              <button type="button" onClick={() => updateIssue(issue.id, { status: "open" })}>Reopen</button>
              <button type="button" onClick={() => updateIssue(issue.id, { severity: "note" })}>Mark note</button>
            </div>
          </article>
        )) : <p className="om-help">No review issues captured yet.</p>}
      </div>
      <div className="om-session-issue-form">
        <label className="om-field">
          <span className="om-field-label">Issue target</span>
          <select className="om-control" value={targetRef} onChange={(event) => setTargetRef(event.target.value)}>
            {allowedTargets.map((target) => <option key={target} value={target}>{target}</option>)}
          </select>
        </label>
        <label className="om-field">
          <span className="om-field-label">Issue status</span>
          <select className="om-control" value={status} onChange={(event) => setStatus(event.target.value)}>
            {(allowedStatuses.length ? allowedStatuses : ["open", "accepted", "rejected", "resolved", "needs_recheck", "waived"]).map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="om-field">
          <span className="om-field-label">Issue severity</span>
          <select className="om-control" value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="blocking">Blocking</option>
            <option value="major">Major</option>
            <option value="minor">Minor</option>
            <option value="note">Note</option>
          </select>
        </label>
        <label className="om-field">
          <span className="om-field-label">Requested change</span>
          <textarea className="om-control om-textarea" value={requestedChange} onChange={(event) => setRequestedChange(event.target.value)} />
        </label>
        <button type="button" className="om-action" onClick={addIssue}>Add issue</button>
      </div>
    </section>
  );
}

function ProjectCockpitView({ node, model }: { node: A2UIComponentNode; model: DataModel }) {
  const session = isRecord(model.session) ? model.session : {};
  const artifacts = recordListFromProps(node.props, "artifactItems");
  const mediaRefs = mediaRefsFromProps(node.props).length ? mediaRefsFromProps(node.props) : dataArray(model, "media_refs").filter(isRecord);
  const traceRefs = dataArray(model, "trace_refs").filter(isRecord);
  const issues = recordListFromProps(node.props, "validationBlockers");
  const timelineItems = recordListFromProps(node.props, "timelineItems");
  const decisionItems = recordListFromProps(node.props, "decisionItems");
  const budgetCostItems = recordListFromProps(node.props, "budgetCostItems");
  const pendingResponses = recordListFromProps(node.props, "pendingResponses");
  const staleSessions = recordListFromProps(node.props, "staleSessions");

  return (
    <section className="om-surface-block om-session-cockpit">
      <header>
        <h2>{String(node.props.title ?? "Project cockpit")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-session-readonly-banner">Read-only overview. Stage advancement and artifact writes stay with the agent.</div>
      <div className="om-session-cockpit-grid">
        <article>
          <span className="om-session-kicker">Project</span>
          <strong>{String(session.project_id ?? "unknown")}</strong>
          <small>{String(session.pipeline_type ?? "pipeline")}</small>
        </article>
        <article>
          <span className="om-session-kicker">Active Stage</span>
          <strong>{String(session.stage ?? "unknown")}</strong>
          <small>{String(session.gate ?? "gate")}</small>
        </article>
        <article>
          <span className="om-session-kicker">Artifacts</span>
          <strong>{artifacts.length}</strong>
          <small>linked for inspection</small>
        </article>
        <article>
          <span className="om-session-kicker">Media</span>
          <strong>{mediaRefs.length}</strong>
          <small>outputs and references</small>
        </article>
        <article>
          <span className="om-session-kicker">Issues</span>
          <strong>{issues.length}</strong>
          <small>validation blockers</small>
        </article>
        <article>
          <span className="om-session-kicker">Trace</span>
          <strong>{traceRefs.length}</strong>
          <small>decision references</small>
        </article>
      </div>
      <div className="om-product-cockpit-sections">
        <CompactRecordList
          title="Timeline"
          items={timelineItems}
          primaryKey="label"
          secondaryKeys={[
            "status",
            "active_sub_stage_label",
            "active_stage",
            "checkpoint"
          ]}
        />
        <CompactRecordList title="Decisions" items={decisionItems} primaryKey="category" secondaryKeys={["selected", "status", "stage"]} />
        <CompactRecordList title="Budget" items={budgetCostItems} primaryKey="artifact" secondaryKeys={["approved_budget_usd", "estimated_cost_usd"]} />
        <CompactRecordList title="Pending Responses" items={pendingResponses} primaryKey="session_id" secondaryKeys={["response_path"]} />
        <CompactRecordList title="Stale Sessions" items={staleSessions} primaryKey="session_id" secondaryKeys={["url", "response_path"]} />
      </div>
    </section>
  );
}

function CompactRecordList({
  title,
  items,
  primaryKey,
  secondaryKeys
}: {
  title: string;
  items: Record<string, unknown>[];
  primaryKey: string;
  secondaryKeys: string[];
}) {
  return (
    <div className="om-product-list">
      <h3>{title}</h3>
      {items.length ? items.slice(0, 8).map((item, index) => (
        <article className="om-trace-item" key={`${title}-${index}`}>
          <strong>{String(item[primaryKey] ?? item.id ?? `${title} ${index + 1}`)}</strong>
          <small>{secondaryKeys.filter((key) => item[key] !== undefined).map((key) => `${key}: ${String(item[key])}`).join(" · ")}</small>
        </article>
      )) : <p className="om-help">No {title.toLowerCase()}.</p>}
    </div>
  );
}

function BackgroundStatusView({ node, model }: { node: A2UIComponentNode; model: DataModel }) {
  const session = isRecord(model.session) ? model.session : {};
  const traceRefs = refItemsFromProps(node.props, "traceRefs");
  return (
    <section className="om-surface-block om-session-background-status">
      <header>
        <h2>{String(node.props.title ?? "Background status")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <ol className="om-session-status-list">
        <li><strong>Session</strong><span>{String(session.id ?? "pending")}</span></li>
        <li><strong>Mode</strong><span>{String(session.mode ?? "background_status")}</span></li>
        <li><strong>Stage</strong><span>{String(session.stage ?? "unknown")}</span></li>
      </ol>
      <ReferenceList title="Trace Links" refs={traceRefs} />
    </section>
  );
}

function recordListFromProps(props: Record<string, unknown>, key: string): Record<string, unknown>[] {
  const value = props[key];
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => isRecord(item)) : [];
}

function MediaTimelineView({
  node,
  model,
  setModel
}: {
  node: A2UIComponentNode;
  model: DataModel;
  setModel: React.Dispatch<React.SetStateAction<DataModel>>;
}) {
  const mediaRefs = mediaRefsFromProps(node.props);
  const evidence = isRecord(model.interaction_evidence) ? model.interaction_evidence : {};
  const opened = new Set(asStringArray(evidence.media_opened));
  const inspected = new Set(asStringArray(evidence.timeline_inspected));

  return (
    <section className="om-surface-block om-panel-panel om-panel-timeline">
      <header>
        <h2>{String(node.props.title ?? "Media timeline")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-panel-timeline-list">
        {mediaRefs.map((media) => (
          <article className="om-panel-timeline-row" key={media.id}>
            <div>
              <strong>{media.title}</strong>
              <small>{media.kind} · {media.id}</small>
            </div>
            <div className="om-panel-status-chips">
              <span className={opened.has(media.id) ? "om-panel-chip om-panel-chip-ok" : "om-panel-chip"}>opened</span>
              <span className={inspected.has(media.id) ? "om-panel-chip om-panel-chip-ok" : "om-panel-chip"}>timeline</span>
            </div>
            <div className="om-product-waveform" aria-hidden="true">
              {Array.from({ length: 18 }, (_, index) => (
                <span key={index} style={{ height: `${20 + ((index * 17) % 45)}%` }} />
              ))}
            </div>
            <div className="om-product-keyframe-strip">
              {["Start", "25%", "50%", "75%", "End"].map((label) => (
                <button
                  type="button"
                  key={`${media.id}-${label}`}
                  onClick={() => setModel((current) => updateEvidence(current, "timeline_inspected", media.id))}
                >
                  <span>{label}</span>
                </button>
              ))}
            </div>
            <div className="om-session-evidence-buttons">
              <button type="button" onClick={() => setModel((current) => updateEvidence(current, "media_opened", media.id))}>Record opened</button>
              <button type="button" onClick={() => setModel((current) => updateEvidence(current, "timeline_inspected", media.id))}>Record timeline checked</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function MediaComparisonView({ node }: { node: A2UIComponentNode }) {
  const mediaRefs = mediaRefsFromProps(node.props);
  const choices = choicesFromProps(node.props);
  const reviewItems = recordListFromProps(node.props, "reviewItems");

  return (
    <section className="om-surface-block om-panel-panel om-panel-comparison">
      <header>
        <h2>{String(node.props.title ?? "Media comparison")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-panel-comparison-grid">
        {mediaRefs.map((media) => (
          <article className="om-trace-item" key={media.id}>
            <strong>{media.title}</strong>
            <small>{media.kind} · {media.path ?? media.text ?? media.id}</small>
          </article>
        ))}
        {choices.map((choice) => (
          <article className="om-trace-item" key={choice.value}>
            <strong>{choice.label}</strong>
            <small>{choice.recommended ? "recommended" : "option"}</small>
            {choice.description ? <p>{choice.description}</p> : null}
          </article>
        ))}
      </div>
      {reviewItems.length ? (
        <div className="om-panel-review-items">
          {reviewItems.map((item, index) => (
            <article className="om-trace-item" key={String(item.id ?? item.scene_id ?? item.option_id ?? index)}>
              <strong>{String(item.label ?? item.scene_id ?? item.option_id ?? `Item ${index + 1}`)}</strong>
              <small>{Object.entries(item).map(([key, value]) => `${key}: ${String(value)}`).join(" · ")}</small>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function RegionAnnotationView({ node, model }: { node: A2UIComponentNode; model: DataModel }) {
  const annotations = dataArray(model, "annotations").filter(isRecord);
  return (
    <section className="om-surface-block om-panel-panel">
      <header>
        <h2>{String(node.props.title ?? "Region annotation")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-panel-status-chips">
        <span className="om-panel-chip">x/y/width/height use 0-1 coordinates</span>
        <span className="om-panel-chip">{annotations.length} captured</span>
      </div>
      {annotations.slice(-3).map((annotation, index) => (
        <article className="om-trace-item" key={`${String(annotation.target_ref)}-${index}`}>
          <strong>{String(annotation.target_ref ?? "target")}</strong>
          <small>{annotation.time_range ? JSON.stringify(annotation.time_range) : "no range"} · {annotation.region ? JSON.stringify(annotation.region) : "no region"}</small>
          <p>{String(annotation.comment ?? "")}</p>
        </article>
      ))}
    </section>
  );
}

function IssueBoardView({ node, model }: { node: A2UIComponentNode; model: DataModel }) {
  const issues = dataArray(model, "issues").filter(isRecord);
  const allowedStatuses = asStringArray(node.props.allowedStatuses);
  const statuses = allowedStatuses.length ? allowedStatuses : ["open", "accepted", "rejected", "resolved", "needs_recheck", "waived"];
  return (
    <section className="om-surface-block om-panel-panel om-panel-issue-board">
      <header>
        <h2>{String(node.props.title ?? "Issue board")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-panel-board">
        {statuses.map((status) => {
          const matching = issues.filter((issue) => issue.status === status);
          return (
            <article className="om-panel-board-column" key={status}>
              <strong>{status}</strong>
              <span>{matching.length}</span>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ArtifactTraceView({ node }: { node: A2UIComponentNode }) {
  return (
    <section className="om-surface-block om-panel-panel">
      <ReferenceList title="Artifact Links" refs={refItemsFromProps(node.props, "artifactRefs")} />
      <ReferenceList title="Trace Links" refs={refItemsFromProps(node.props, "traceRefs")} />
    </section>
  );
}

function RevisionPatchPreviewView({ node, model }: { node: A2UIComponentNode; model: DataModel }) {
  const patches = dataArray(model, "revision_patches").filter(isRecord);
  return (
    <section className="om-surface-block om-panel-panel">
      <header>
        <h2>{String(node.props.title ?? "Revision patch preview")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      {patches.length ? patches.map((patch, index) => (
        <article className="om-trace-item" key={`${String(patch.artifact)}-${String(patch.path)}-${index}`}>
          <strong>{String(patch.artifact)}.{String(patch.path)}</strong>
          <small>pending agent validation</small>
          <p>{typeof patch.value === "string" ? patch.value : JSON.stringify(patch.value)}</p>
        </article>
      )) : <p className="om-help">No response patches captured yet.</p>}
    </section>
  );
}

function ApprovalAttestationView({ node, model }: { node: A2UIComponentNode; model: DataModel }) {
  const attestations = dataArray(model, "approval_attestations").filter(isRecord);
  return (
    <section className="om-surface-block om-panel-panel">
      <header>
        <h2>{String(node.props.title ?? "Approval attestation")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-panel-status-chips">
        <span className="om-panel-chip">{attestations.filter((item) => item.approved === true).length} approved</span>
        <span className="om-panel-chip">{attestations.length} captured</span>
      </div>
    </section>
  );
}

function LiveStatusPanelView({ node, model, eventLog }: { node: A2UIComponentNode; model: DataModel; eventLog: BrowserEvent[] }) {
  const session = isRecord(model.session) ? model.session : {};
  const responseReady = dataArray(model, "revision_patches").length || dataArray(model, "issues").length || Object.keys(modelValues(model)).length;
  const cursor = latestEventCursor(eventLog);
  return (
    <section className="om-surface-block om-panel-panel om-panel-live-status">
      <header>
        <h2>{String(node.props.title ?? "Live session status")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-session-cockpit-grid">
        <article><span className="om-session-kicker">Contract</span><strong>{String(session.genui_contract ?? "genui")}</strong><small>product interaction</small></article>
        <article><span className="om-session-kicker">Events</span><strong>{eventLog.length}</strong><small>AG-UI snapshots</small></article>
        <article><span className="om-session-kicker">Cursor</span><strong>{cursor ?? "pending"}</strong><small>resumable stream</small></article>
        <article><span className="om-session-kicker">Response State</span><strong>{responseReady ? "pending input" : "empty"}</strong><small>response-only writes</small></article>
      </div>
      {eventLog.slice(-4).map((event, index) => (
        <article className="om-trace-item" key={`${event.type}-${index}`}>
          <strong>{event.type}</strong>
          <small>{String(event.cursor ?? event.sequence ?? "")} {String(event.threadId ?? "")} {String(event.runId ?? "")}</small>
        </article>
      ))}
    </section>
  );
}

function InteractionJournalPanelView({ node }: { node: A2UIComponentNode }) {
  return (
    <section className="om-surface-block om-panel-panel">
      <header>
        <h2>{String(node.props.title ?? "Interaction journal")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <dl className="om-panel-journal-dl">
        <div><dt>Routing</dt><dd>{String(node.props.routingDecisionId ?? "recorded by agent")}</dd></div>
        <div><dt>Request</dt><dd>{String(node.props.sourceRequestId ?? "session")}</dd></div>
        <div><dt>Journal</dt><dd>{String(node.props.journalPath ?? "artifacts/ui/interaction_journal.json")}</dd></div>
      </dl>
    </section>
  );
}

function OperationTimelineView({ node, eventLog }: { node: A2UIComponentNode; eventLog: BrowserEvent[] }) {
  const operationEvents = recordListFromProps(node.props, "operationEvents");
  const visibleEvents = operationEvents.length ? operationEvents : eventLog.filter(isRecord);
  return (
    <section className="om-surface-block om-panel-panel om-product-operation-timeline">
      <header>
        <h2>{String(node.props.title ?? "Operation timeline")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-product-timeline">
        {visibleEvents.slice(0, 10).map((event, index) => (
          <article className="om-trace-item" key={`${String(event.id ?? event.type ?? "event")}-${index}`}>
            <strong>{String(event.label ?? event.tool ?? event.type ?? "operation")}</strong>
            <small>{[
              event.status ?? event.toolCallName ?? event.tool ?? "recorded",
              event.cursor ?? event.sequence,
            ].filter((item) => item !== undefined && item !== null && String(item)).map(String).join(" · ")}</small>
          </article>
        ))}
      </div>
    </section>
  );
}

function ReviewCompletionPanelView({ node, model }: { node: A2UIComponentNode; model: DataModel }) {
  const requiredEvidence = asStringArray(node.props.requiredEvidence);
  const evidence = isRecord(model.interaction_evidence) ? model.interaction_evidence : {};
  const approvals = dataArray(model, "approval_attestations").filter(isRecord);
  const issues = dataArray(model, "issues").filter(isRecord);
  const openedCount = asStringArray(evidence.media_opened).length;
  const inspectedCount = asStringArray(evidence.timeline_inspected).length;
  const blockingCount = issues.filter((issue) => issue.severity === "blocking" && ["open", "accepted", "needs_recheck"].includes(String(issue.status))).length;
  return (
    <section className="om-surface-block om-panel-panel om-product-review-completion">
      <header>
        <h2>{String(node.props.title ?? "Review completion")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <div className="om-panel-status-chips">
        <span className={openedCount ? "om-panel-chip om-panel-chip-ok" : "om-panel-chip"}>opened {openedCount}</span>
        <span className={inspectedCount ? "om-panel-chip om-panel-chip-ok" : "om-panel-chip"}>timeline {inspectedCount}</span>
        <span className={approvals.some((item) => item.approved === true) ? "om-panel-chip om-panel-chip-ok" : "om-panel-chip"}>approvals {approvals.length}</span>
        <span className={blockingCount ? "om-panel-chip" : "om-panel-chip om-panel-chip-ok"}>blocking {blockingCount}</span>
      </div>
      <small>{requiredEvidence.length ? `Required: ${requiredEvidence.join(", ")}` : "No evidence required for this surface."}</small>
    </section>
  );
}

function DurableDecisionPanelView({ node }: { node: A2UIComponentNode }) {
  const decision = isRecord(node.props.decision) ? node.props.decision : {};
  return (
    <section className="om-surface-block om-panel-panel om-product-decision">
      <header>
        <h2>{String(node.props.title ?? "Durable decision")}</h2>
        {typeof node.props.description === "string" ? <p>{node.props.description}</p> : null}
      </header>
      <dl className="om-panel-journal-dl">
        <div><dt>Decision</dt><dd>{String(decision.decisionId ?? "pending")}</dd></div>
        <div><dt>Policy</dt><dd>{String(decision.stagePolicyId ?? "dynamic")}</dd></div>
        <div><dt>Schema</dt><dd>{String(decision.schemaStrategy ?? "fixed")}</dd></div>
        <div><dt>Expires</dt><dd>{String(decision.expiresAt ?? "not set")}</dd></div>
      </dl>
    </section>
  );
}

function ActionBarView({
  node,
  spec,
  model,
  setStatus
}: {
  node: A2UIComponentNode;
  spec: VideoProductionBuddySessionViewSpec;
  model: DataModel;
  setStatus: React.Dispatch<React.SetStateAction<string>>;
}) {
  const [submitting, setSubmitting] = useState(false);
  const actions = Array.isArray(node.props.actions) ? node.props.actions.filter(isRecord) : [];
  const previewOnly = node.props.previewOnly === true;

  async function submit(action: string) {
    const submitUrl = resolveSameOriginSubmitUrl(window.location.href);
    if (!submitUrl || previewOnly) {
      setStatus("Preview only. Start GenUI in serve mode to submit this session.");
      return;
    }
    setSubmitting(true);
    setStatus("Submitting...");
    try {
      const response = await fetch(submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildA2UISubmissionPayload(action, spec, model))
      });
      const text = await response.text();
      const result = text ? JSON.parse(text) as { error?: string; response_path?: string } : {};
      if (!response.ok) throw new Error(result.error || text || response.statusText);
      setStatus(`Submitted. Response saved to ${result.response_path ?? "response.json"}. Return to the agent to continue.`);
    } catch (error) {
      setStatus(`Submission failed: ${error instanceof Error ? error.message : String(error)}`);
      setSubmitting(false);
    }
  }

  return (
    <div className="om-action-bar">
      {actions.map((action) => (
        <button
          type="button"
          key={String(action.id ?? action.kind)}
          className={action.recommended ? "om-action om-action-primary" : "om-action"}
          disabled={submitting}
          onClick={() => void submit(String(action.kind ?? "submit"))}
        >
          {String(action.label ?? action.kind ?? "Submit")}
        </button>
      ))}
    </div>
  );
}

function SessionShellComponent({ node, surfaceId }: A2UIComponentProps) {
  const { registry } = useSessionRendererContext();
  const localNode = nodeFromA2UI(node);
  const children = childNodesFromProps(localNode.props).map((child) => (
    <ComponentNode node={child} surfaceId={surfaceId} registry={registry} key={String(child.id)} />
  ));
  return <SessionShellView node={localNode}>{children}</SessionShellView>;
}

function GateWorkspaceComponent({ node }: A2UIComponentProps) {
  const { model, setModel } = useSessionRendererContext();
  return <GateWorkspaceView node={nodeFromA2UI(node)} model={model} setModel={setModel} />;
}

function MediaReviewRoomComponent({ node }: A2UIComponentProps) {
  const { model, setModel } = useSessionRendererContext();
  return <MediaReviewRoomView node={nodeFromA2UI(node)} model={model} setModel={setModel} />;
}

function IssueTrackerComponent({ node }: A2UIComponentProps) {
  const { model, setModel } = useSessionRendererContext();
  return <IssueTrackerView node={nodeFromA2UI(node)} model={model} setModel={setModel} />;
}

function ProjectCockpitComponent({ node }: A2UIComponentProps) {
  const { model } = useSessionRendererContext();
  return <ProjectCockpitView node={nodeFromA2UI(node)} model={model} />;
}

function BackgroundStatusComponent({ node }: A2UIComponentProps) {
  const { model } = useSessionRendererContext();
  return <BackgroundStatusView node={nodeFromA2UI(node)} model={model} />;
}

function MediaTimelineComponent({ node }: A2UIComponentProps) {
  const { model, setModel } = useSessionRendererContext();
  return <MediaTimelineView node={nodeFromA2UI(node)} model={model} setModel={setModel} />;
}

function MediaComparisonComponent({ node }: A2UIComponentProps) {
  return <MediaComparisonView node={nodeFromA2UI(node)} />;
}

function RegionAnnotationComponent({ node }: A2UIComponentProps) {
  const { model } = useSessionRendererContext();
  return <RegionAnnotationView node={nodeFromA2UI(node)} model={model} />;
}

function IssueBoardComponent({ node }: A2UIComponentProps) {
  const { model } = useSessionRendererContext();
  return <IssueBoardView node={nodeFromA2UI(node)} model={model} />;
}

function ArtifactTraceComponent({ node }: A2UIComponentProps) {
  return <ArtifactTraceView node={nodeFromA2UI(node)} />;
}

function RevisionPatchPreviewComponent({ node }: A2UIComponentProps) {
  const { model } = useSessionRendererContext();
  return <RevisionPatchPreviewView node={nodeFromA2UI(node)} model={model} />;
}

function ApprovalAttestationComponent({ node }: A2UIComponentProps) {
  const { model } = useSessionRendererContext();
  return <ApprovalAttestationView node={nodeFromA2UI(node)} model={model} />;
}

function LiveStatusPanelComponent({ node }: A2UIComponentProps) {
  const { model, eventLog } = useSessionRendererContext();
  return <LiveStatusPanelView node={nodeFromA2UI(node)} model={model} eventLog={eventLog} />;
}

function InteractionJournalPanelComponent({ node }: A2UIComponentProps) {
  return <InteractionJournalPanelView node={nodeFromA2UI(node)} />;
}

function OperationTimelineComponent({ node }: A2UIComponentProps) {
  const { eventLog } = useSessionRendererContext();
  return <OperationTimelineView node={nodeFromA2UI(node)} eventLog={eventLog} />;
}

function ReviewCompletionPanelComponent({ node }: A2UIComponentProps) {
  const { model } = useSessionRendererContext();
  return <ReviewCompletionPanelView node={nodeFromA2UI(node)} model={model} />;
}

function DurableDecisionPanelComponent({ node }: A2UIComponentProps) {
  return <DurableDecisionPanelView node={nodeFromA2UI(node)} />;
}

function ActionBarComponent({ node }: A2UIComponentProps) {
  const { spec, model, setStatus } = useSessionRendererContext();
  return <ActionBarView node={nodeFromA2UI(node)} spec={spec} model={model} setStatus={setStatus} />;
}

export function createVideoProductionBuddyA2UIRegistry(): ComponentRegistry {
  const registry = new ComponentRegistry();
  const workspaceComponent = { component: GateWorkspaceComponent };
  registry.register("SessionShell", { component: SessionShellComponent });
  registry.register("GateWorkspace", workspaceComponent);
  for (const type of workspaceSurfaceTypes) {
    registry.register(type, workspaceComponent);
  }
  registry.register("MediaReviewRoom", { component: MediaReviewRoomComponent });
  registry.register("IssueTracker", { component: IssueTrackerComponent });
  registry.register("ProjectCockpit", { component: ProjectCockpitComponent });
  registry.register("BackgroundStatus", { component: BackgroundStatusComponent });
  registry.register("MediaTimeline", { component: MediaTimelineComponent });
  registry.register("MediaComparison", { component: MediaComparisonComponent });
  registry.register("RegionAnnotation", { component: RegionAnnotationComponent });
  registry.register("IssueBoard", { component: IssueBoardComponent });
  registry.register("ArtifactTrace", { component: ArtifactTraceComponent });
  registry.register("RevisionPatchPreview", { component: RevisionPatchPreviewComponent });
  registry.register("ApprovalAttestation", { component: ApprovalAttestationComponent });
  registry.register("LiveStatusPanel", { component: LiveStatusPanelComponent });
  registry.register("InteractionJournalPanel", { component: InteractionJournalPanelComponent });
  registry.register("OperationTimeline", { component: OperationTimelineComponent });
  registry.register("ReviewCompletionPanel", { component: ReviewCompletionPanelComponent });
  registry.register("DurableDecisionPanel", { component: DurableDecisionPanelComponent });
  registry.register("ActionBar", { component: ActionBarComponent });
  return registry;
}

const catalogRenderers = {
  SessionShell: SessionShellComponent,
  GateWorkspace: GateWorkspaceComponent,
  MediaReviewRoom: MediaReviewRoomComponent,
  IssueTracker: IssueTrackerComponent,
  ProjectCockpit: ProjectCockpitComponent,
  BackgroundStatus: BackgroundStatusComponent,
  MediaTimeline: MediaTimelineComponent,
  MediaComparison: MediaComparisonComponent,
  RegionAnnotation: RegionAnnotationComponent,
  IssueBoard: IssueBoardComponent,
  ArtifactTrace: ArtifactTraceComponent,
  RevisionPatchPreview: RevisionPatchPreviewComponent,
  ApprovalAttestation: ApprovalAttestationComponent,
  LiveStatusPanel: LiveStatusPanelComponent,
  InteractionJournalPanel: InteractionJournalPanelComponent,
  OperationTimeline: OperationTimelineComponent,
  ReviewCompletionPanel: ReviewCompletionPanelComponent,
  DurableDecisionPanel: DurableDecisionPanelComponent,
  ProposalLock: GateWorkspaceComponent,
  ScriptReviewWorkspace: GateWorkspaceComponent,
  ScenePlanWorkspace: GateWorkspaceComponent,
  ProductReferenceApproval: GateWorkspaceComponent,
  SampleReview: GateWorkspaceComponent,
  AssetReview: GateWorkspaceComponent,
  MusicReview: GateWorkspaceComponent,
  PublishReview: GateWorkspaceComponent,
  ActionBar: ActionBarComponent
};

export const videoProductionBuddyA2UICatalog = createCatalog(
  catalogDefinitions as never,
  catalogRenderers as never,
  { catalogId: "video-production-buddy-genui", includeBasicCatalog: true }
);

type ValueMap = {
  key: string;
  valueString?: string;
  valueNumber?: number;
  valueBoolean?: boolean;
  valueMap?: ValueMap[];
};

function valueToValueMap(key: string, value: unknown): ValueMap {
  if (typeof value === "string") return { key, valueString: value };
  if (typeof value === "number") return { key, valueNumber: value };
  if (typeof value === "boolean") return { key, valueBoolean: value };
  if (Array.isArray(value)) return { key, valueMap: value.map((item, index) => valueToValueMap(String(index), item)) };
  if (isRecord(value)) return { key, valueMap: Object.entries(value).map(([childKey, childValue]) => valueToValueMap(childKey, childValue)) };
  return { key, valueString: "" };
}

function objectToValueMaps(value: Record<string, unknown>): ValueMap[] {
  return Object.entries(value)
    .filter(([, item]) => item !== undefined && item !== null)
    .map(([key, item]) => valueToValueMap(key, item));
}

function componentToA2UIInstance(component: A2UIComponentNode): { id: string; component: Record<string, Record<string, unknown>> } {
  const props = {
    ...component.props,
    ...(component.children?.length ? { children: { explicitList: component.children } } : {})
  };
  return {
    id: component.id,
    component: {
      [component.type]: props
    }
  };
}

function buildA2UIMessages(spec: VideoProductionBuddySessionViewSpec): ServerToClientMessage[] {
  const extracted = extractA2UISessionSpec(spec);
  const messages: ServerToClientMessage[] = [
    { beginRendering: { surfaceId: extracted.surfaceId, root: spec.root, styles: {} } },
    {
      surfaceUpdate: {
        surfaceId: extracted.surfaceId,
        components: extracted.components.map(componentToA2UIInstance)
      }
    }
  ];
  if (Object.keys(extracted.dataModel).length) {
    messages.push({
      dataModelUpdate: {
        surfaceId: extracted.surfaceId,
        path: "/",
        contents: objectToValueMaps(extracted.dataModel)
      }
    });
  }
  return messages;
}

function A2UISessionBootstrap({ spec }: { spec: VideoProductionBuddySessionViewSpec }) {
  const { processMessages } = useA2UIActions();
  const messages = useMemo(() => buildA2UIMessages(spec), [spec]);
  useEffect(() => {
    processMessages(messages);
  }, [processMessages, messages]);
  return null;
}

function buildInitialModel(spec: VideoProductionBuddySessionViewSpec): DataModel {
  const extracted = extractA2UISessionSpec(spec);
  return {
    values: {},
    annotations: [],
    selected_refs: [],
    issues: [],
    revision_patches: [],
    approval_attestations: [],
    interaction_evidence: { media_opened: [], timeline_inspected: [], seconds_watched: 0 },
    ...extracted.dataModel
  };
}

function parseEventStream(text: string): BrowserEvent[] {
  return text
    .split(/\n\n+/)
    .map((chunk) => chunk.split("\n").find((line) => line.startsWith("data: ")))
    .filter((line): line is string => typeof line === "string")
    .map((line) => line.replace(/^data:\s*/, ""))
    .map((raw) => {
      try {
        const parsed = JSON.parse(raw);
        if (isRecord(parsed) && typeof parsed.type === "string") return parsed as BrowserEvent;
      } catch {
        return null;
      }
      return null;
    })
    .filter((event): event is BrowserEvent => event !== null);
}

function browserEventKey(event: BrowserEvent, fallbackIndex: number): string {
  if (typeof event.cursor === "string") return event.cursor;
  if (typeof event.sequence === "number") return `sequence:${event.sequence}`;
  return `${event.type}:${String(event.threadId ?? "")}:${String(event.runId ?? "")}:${fallbackIndex}`;
}

function latestEventCursor(events: BrowserEvent[]): string | null {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const cursor = events[index].cursor;
    if (typeof cursor === "string" && cursor) return cursor;
  }
  return null;
}

export function A2UISessionRenderer({ spec }: { spec: VideoProductionBuddySessionViewSpec }) {
  const extracted = useMemo(() => extractA2UISessionSpec(spec), [spec]);
  const registry = useMemo(() => createVideoProductionBuddyA2UIRegistry(), []);
  const [model, setModel] = useState<DataModel>(() => buildInitialModel(spec));
  const [status, setStatus] = useState("Ready for review.");
  const [eventLog, setEventLog] = useState<BrowserEvent[]>([]);
  const draftReadyRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    let cursor: string | null = null;
    const seen = new Set<string>();
    async function refreshEvents() {
      if (cancelled || inFlight) return;
      inFlight = true;
      try {
        const path = cursor ? `/events?after=${encodeURIComponent(cursor)}` : "/events";
        const response = await fetch(path, {
          headers: {
            Accept: "text/event-stream",
            ...(cursor ? { "Last-Event-ID": cursor } : {})
          }
        });
        if (!response.ok) return;
        const text = await response.text();
        if (cancelled) return;
        const events = parseEventStream(text);
        const uniqueEvents: BrowserEvent[] = [];
        events.forEach((event, index) => {
          const key = browserEventKey(event, seen.size + index);
          if (seen.has(key)) return;
          seen.add(key);
          uniqueEvents.push(event);
        });
        const headerCursor = response.headers.get("X-GenUI-Event-Cursor");
        cursor = latestEventCursor(uniqueEvents) ?? headerCursor ?? cursor;
        if (uniqueEvents.length) {
          setEventLog((previous) => [...previous, ...uniqueEvents].slice(-100));
        }
      } catch {
        if (!cancelled) setEventLog((previous) => previous);
      } finally {
        inFlight = false;
      }
    }
    void refreshEvents();
    const intervalId = window.setInterval(() => {
      void refreshEvents();
    }, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function restoreDraft() {
      const draftUrl = resolveSameOriginDraftUrl(window.location.href);
      if (!draftUrl || spec.metadata?.preview_only === true) {
        draftReadyRef.current = true;
        return;
      }
      try {
        const response = await fetch(draftUrl, { headers: { Accept: "application/json" } });
        if (!response.ok) return;
        const payload = await response.json() as { draft?: { model?: unknown } | null };
        if (cancelled) return;
        const draftModel = payload.draft && isRecord(payload.draft.model) ? payload.draft.model : null;
        if (draftModel) {
          setModel((current) => ({ ...current, ...draftModel }));
          setStatus("Restored saved draft.");
        }
      } catch {
        if (!cancelled) setStatus((current) => current);
      } finally {
        draftReadyRef.current = true;
      }
    }
    void restoreDraft();
    return () => {
      cancelled = true;
    };
  }, [spec]);

  useEffect(() => {
    if (!draftReadyRef.current || spec.metadata?.preview_only === true) return;
    const draftUrl = resolveSameOriginDraftUrl(window.location.href);
    const nonce = typeof spec.metadata?.submit_nonce === "string" ? spec.metadata.submit_nonce : undefined;
    if (!draftUrl || !nonce) return;
    const timeoutId = window.setTimeout(() => {
      void fetch(draftUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nonce,
          saved_at: new Date().toISOString(),
          model,
          browser_events: [
            {
              type: "draft_autosave",
              timestamp: new Date().toISOString(),
              field_count: isRecord(model.values) ? Object.keys(model.values).length : 0
            }
          ]
        })
      }).catch(() => undefined);
    }, 800);
    return () => window.clearTimeout(timeoutId);
  }, [model, spec]);

  const contextValue = useMemo(
    () => ({ spec, model, setModel, status, setStatus, eventLog, registry }),
    [spec, model, status, eventLog, registry]
  );

  return (
    <A2UIProvider>
      <SessionRendererContext.Provider value={contextValue}>
        <A2UISessionBootstrap spec={spec} />
        <A2UIRenderer
          surfaceId={extracted.surfaceId}
          registry={registry}
          fallback={<main className="om-shell"><div className="om-status">Preparing GenUI session...</div></main>}
        />
        <div id="status" className="om-status om-session-status" tabIndex={-1} aria-live="polite">{status}</div>
      </SessionRendererContext.Provider>
    </A2UIProvider>
  );
}
