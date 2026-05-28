import { defineRegistry, useBoundProp, useStateStore } from "@json-render/react";
import { useState } from "react";
import { catalog } from "./catalog";
import {
  buildSubmissionPayload,
  isJsonRenderSurfaceSpec,
  resolveSameOriginSubmitUrl,
  safeMediaSrc,
  type VideoProductionBuddyViewSpec
} from "./payload";

type Choice = {
  value: string;
  label: string;
  description?: string | null;
  recommended?: boolean;
  preview?: Record<string, unknown>;
};

type FieldProps = {
  fieldId: string;
  label: string;
  value?: unknown;
  required?: boolean;
  helpText?: string | null;
  recommended?: string | null;
  placeholder?: string | null;
  choices?: Choice[];
  multiple?: boolean;
  min?: number;
  max?: number;
};

type SurfaceOption = {
  id?: string;
  value?: string;
  label?: string;
  summary?: string;
  description?: string;
  tradeoff?: string;
  recommended?: boolean;
};

type VisibleIf = {
  field: string;
  operator: "equals" | "not_equals" | "not_empty" | "empty";
  value?: unknown;
};

type SurfaceRef = {
  id?: string;
  title?: string;
  label?: string;
  kind?: string;
  path?: string;
  text?: string;
  alt?: string;
  artifact?: string;
  source?: string;
  summary?: string;
  status?: string;
};

type SurfaceField = {
  id: string;
  label: string;
  type: string;
  required?: boolean;
  placeholder?: string | null;
  choices?: SurfaceOption[];
  min?: number;
  max?: number;
  target_ref?: string;
  help_text?: string;
  recommended?: string;
  visible_if?: VisibleIf;
};

type SurfaceBlockProps = {
  blockId: string;
  title: string;
  description?: string | null;
  value?: unknown;
  valueFieldId?: string;
  valueFieldIds?: string[];
  multiple?: boolean;
  options?: SurfaceOption[];
  fields?: SurfaceField[];
  annotationFields?: SurfaceField[];
  items?: Array<Record<string, unknown>>;
  mediaRefs?: SurfaceRef[];
  artifactRefs?: SurfaceRef[];
  traceRefs?: SurfaceRef[];
};

function toText(value: unknown): string {
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function FieldFrame({ props, children }: { props: FieldProps; children: React.ReactNode }) {
  return (
    <label className="om-field" data-field-id={props.fieldId}>
      <span className="om-field-label">
        {props.label}
        {props.required ? <span className="om-required">required</span> : null}
      </span>
      {children}
      {props.recommended ? <span className="om-recommendation">Recommended: {props.recommended}</span> : null}
      {props.helpText ? <span className="om-help">{props.helpText}</span> : null}
    </label>
  );
}

function TextInputField({ props, bindings }: { props: FieldProps; bindings?: Record<string, string> }) {
  const [value, setValue] = useBoundProp(props.value, bindings?.value);
  return (
    <FieldFrame props={props}>
      <input
        className="om-control"
        type="text"
        required={props.required}
        placeholder={props.placeholder ?? ""}
        value={toText(value)}
        onChange={(event) => setValue(event.target.value)}
      />
    </FieldFrame>
  );
}

function TextAreaField({ props, bindings }: { props: FieldProps; bindings?: Record<string, string> }) {
  const [value, setValue] = useBoundProp(props.value, bindings?.value);
  return (
    <FieldFrame props={props}>
      <textarea
        className="om-control om-textarea"
        required={props.required}
        placeholder={props.placeholder ?? ""}
        value={toText(value)}
        onChange={(event) => setValue(event.target.value)}
      />
    </FieldFrame>
  );
}

function SelectField({ props, bindings }: { props: FieldProps; bindings?: Record<string, string> }) {
  const [value, setValue] = useBoundProp(props.value, bindings?.value);
  return (
    <FieldFrame props={props}>
      <select
        className="om-control"
        required={props.required}
        value={toText(value)}
        onChange={(event) => setValue(event.target.value)}
      >
        <option value="" disabled={props.required}>Select...</option>
        {(props.choices ?? []).map((choice) => (
          <option key={choice.value} value={choice.value}>{choice.label}</option>
        ))}
      </select>
    </FieldFrame>
  );
}

function ChoiceGroupField({ props, bindings }: { props: FieldProps; bindings?: Record<string, string> }) {
  const [value, setValue] = useBoundProp(props.value, bindings?.value);
  const selectedValues = new Set(Array.isArray(value) ? value.map(String) : [toText(value)]);
  const multiple = Boolean(props.multiple);

  return (
    <div className="om-field" data-field-id={props.fieldId}>
      <span className="om-field-label">
        {props.label}
        {props.required ? <span className="om-required">required</span> : null}
      </span>
      <div className="om-choice-grid">
        {(props.choices ?? []).map((choice) => {
          const checked = selectedValues.has(choice.value);
          return (
            <label className="om-choice-card" key={choice.value}>
              <input
                type={multiple ? "checkbox" : "radio"}
                name={props.fieldId}
                checked={checked}
                onChange={(event) => {
                  if (multiple) {
                    const next = new Set(selectedValues);
                    if (event.target.checked) next.add(choice.value);
                    else next.delete(choice.value);
                    setValue(Array.from(next));
                  } else {
                    setValue(choice.value);
                  }
                }}
              />
              <span>
                <strong>{choice.label}</strong>
                {choice.recommended ? <span className="om-choice-badge">recommended</span> : null}
                {choice.description ? <small>{choice.description}</small> : null}
                {typeof choice.preview?.text === "string" ? <small className="om-preview-text">{choice.preview.text}</small> : null}
              </span>
            </label>
          );
        })}
      </div>
      {props.recommended ? <span className="om-recommendation">Recommended: {props.recommended}</span> : null}
      {props.helpText ? <span className="om-help">{props.helpText}</span> : null}
    </div>
  );
}

function CheckboxField({ props, bindings }: { props: FieldProps; bindings?: Record<string, string> }) {
  const [value, setValue] = useBoundProp(props.value, bindings?.value);
  return (
    <FieldFrame props={props}>
      <span className="om-inline-check">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => setValue(event.target.checked)}
        />
        Confirm
      </span>
    </FieldFrame>
  );
}

function NumberField({ props, bindings }: { props: FieldProps; bindings?: Record<string, string> }) {
  const [value, setValue] = useBoundProp(props.value, bindings?.value);
  return (
    <FieldFrame props={props}>
      <input
        className="om-control"
        type="number"
        min={props.min}
        max={props.max}
        required={props.required}
        value={toText(value)}
        onChange={(event) => setValue(event.target.value)}
      />
    </FieldFrame>
  );
}

function UrlField({ props, bindings }: { props: FieldProps; bindings?: Record<string, string> }) {
  const [value, setValue] = useBoundProp(props.value, bindings?.value);
  return (
    <FieldFrame props={props}>
      <input
        className="om-control"
        type="url"
        required={props.required}
        placeholder={props.placeholder ?? ""}
        value={toText(value)}
        onChange={(event) => setValue(event.target.value)}
      />
    </FieldFrame>
  );
}

function FilePathField(props: { props: FieldProps; bindings?: Record<string, string> }) {
  return <TextInputField {...props} />;
}

function ApprovalField(props: { props: FieldProps; bindings?: Record<string, string> }) {
  return <CheckboxField {...props} />;
}

function InfoCard({ props }: { props: { label: string; helpText?: string | null; recommended?: string | null } }) {
  return (
    <section className="om-info-card">
      <h3>{props.label}</h3>
      {props.recommended ? <p className="om-recommendation">Recommended: {props.recommended}</p> : null}
      {props.helpText ? <p>{props.helpText}</p> : null}
    </section>
  );
}

function MediaPreviewCard({ props }: { props: { title: string; kind: string; text?: string | null; path?: string | null; alt?: string | null } }) {
  const mediaSrc = safeMediaSrc(props.path);
  return (
    <section className="om-preview-card">
      <h3>{props.title}</h3>
      {props.text ? <p>{props.text}</p> : null}
      {props.path ? <code>{props.path}</code> : null}
      {props.kind === "image" && mediaSrc ? <img src={mediaSrc} alt={props.alt ?? props.title} /> : null}
      {props.kind === "video" && mediaSrc ? <video src={mediaSrc} controls /> : null}
      {props.kind === "audio" && mediaSrc ? <audio src={mediaSrc} controls /> : null}
    </section>
  );
}

function ReviewGrid({ props }: { props: { title: string; items: Array<Record<string, unknown>> } }) {
  const columns = Array.from(new Set(props.items.flatMap((item) => Object.keys(item))));
  return (
    <section className="om-review-grid">
      <h3>{props.title}</h3>
      <div className="om-review-table" role="table">
        <div className="om-review-row om-review-head" role="row">
          {columns.map((column) => <span role="columnheader" key={column}>{column}</span>)}
        </div>
        {props.items.map((item, index) => (
          <div className="om-review-row" role="row" key={index}>
            {columns.map((column) => <span role="cell" key={column}>{toText(item[column])}</span>)}
          </div>
        ))}
      </div>
    </section>
  );
}

function ShellFrame({
  props,
  variant,
  children
}: {
  props: {
    title: string;
    description?: string | null;
    surfaceId?: string;
    configId?: string;
    projectId?: string;
    pipelineType?: string;
    stage?: string;
    gate?: string;
    mode?: string;
  };
  variant: "workspace" | "cockpit";
  children?: React.ReactNode;
}) {
  const { state } = useStateStore();
  const status = typeof state.status === "object" && state.status !== null
    ? (state.status as Record<string, unknown>).message
    : "";
  const eyebrow = variant === "cockpit"
    ? "Video Production Buddy GenUI compatibility · Project Cockpit"
    : "Video Production Buddy GenUI compatibility · AG-UI + json-render";
  return (
    <main className={`om-shell om-shell-${variant}`}>
      <header className="om-header">
        <div>
          <p className="om-eyebrow">{eyebrow}</p>
          <h1>{props.title}</h1>
          {props.description ? <p>{props.description}</p> : null}
        </div>
        <dl className="om-meta">
          {(props.surfaceId || props.configId) ? <div><dt>{props.surfaceId ? "Surface" : "Config"}</dt><dd>{props.surfaceId ?? props.configId}</dd></div> : null}
          {props.pipelineType ? <div><dt>Pipeline</dt><dd>{props.pipelineType}</dd></div> : null}
          {props.stage ? <div><dt>Stage</dt><dd>{props.stage}</dd></div> : null}
          {props.gate ? <div><dt>Gate</dt><dd>{props.gate}</dd></div> : null}
        </dl>
      </header>
      {variant === "workspace" || variant === "cockpit" ? <div className="om-workspace-grid">{children}</div> : children}
      <div id="status" className="om-status" role="status" aria-live="polite" tabIndex={-1}>
        {toText(status)}
      </div>
    </main>
  );
}

function optionValue(option: SurfaceOption): string {
  return String(option.value ?? option.id ?? option.label ?? "");
}

function surfaceSlug(value: unknown, fallback: string): string {
  const raw = String(value ?? fallback);
  let next = raw.replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^[-_.]+|[-_.]+$/g, "");
  if (!next) next = fallback;
  if (!/^[A-Za-z0-9]/.test(next)) next = `surface-${next}`;
  return next.slice(0, 64);
}

function useSurfaceValue(fieldId: string): [unknown, (value: unknown) => void] {
  const store = useStateStore();
  const snapshot = store.getSnapshot();
  const values = typeof snapshot.values === "object" && snapshot.values !== null
    ? snapshot.values as Record<string, unknown>
    : {};
  return [
    values[fieldId],
    (value: unknown) => store.set(`/values/${fieldId}`, value)
  ];
}

function isEmpty(value: unknown): boolean {
  if (value === undefined || value === null) return true;
  if (typeof value === "string") return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "boolean") return value === false;
  return false;
}

function resolveVisibleFieldId(blockId: string, field: SurfaceField, values: Record<string, unknown>): string | null {
  const visibleIf = field.visible_if;
  if (!visibleIf) return null;
  if (visibleIf.field in values) return visibleIf.field;

  const sameBlock = `${blockId}.${visibleIf.field}`;
  if (sameBlock in values) return sameBlock;

  const suffixMatches = Object.keys(values).filter((fieldId) => fieldId.endsWith(`.${visibleIf.field}`));
  return suffixMatches.length === 1 ? suffixMatches[0] : null;
}

function useSurfaceFieldVisible(blockId: string, field: SurfaceField): boolean {
  const visibleIf = field.visible_if;
  const store = useStateStore();
  const snapshot = store.getSnapshot();
  const values = typeof snapshot.values === "object" && snapshot.values !== null
    ? snapshot.values as Record<string, unknown>
    : {};
  const referenceId = resolveVisibleFieldId(blockId, field, values);
  const [referenceValue] = useSurfaceValue(referenceId ?? "__video_production_buddy_missing_visibility_reference__");
  if (!visibleIf || !referenceId) return true;
  if (visibleIf.operator === "not_empty") return !isEmpty(referenceValue);
  if (visibleIf.operator === "empty") return isEmpty(referenceValue);
  if (visibleIf.operator === "equals") return referenceValue === visibleIf.value;
  if (visibleIf.operator === "not_equals") return referenceValue !== visibleIf.value;
  return true;
}

function SurfaceFieldControl({ blockId, field }: { blockId: string; field: SurfaceField }) {
  const fieldId = `${blockId}.${field.id}`;
  const visible = useSurfaceFieldVisible(blockId, field);
  const [value, setValue] = useSurfaceValue(fieldId);
  const choices = field.choices ?? [];
  if (!visible) return null;
  if (field.type === "approval" || field.type === "checkbox") {
    return (
      <label className="om-inline-check om-surface-control">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => setValue(event.target.checked)}
        />
        {field.label}
      </label>
    );
  }
  if (field.type === "select") {
    return (
      <label className="om-field om-surface-control">
        <span className="om-field-label">{field.label}</span>
        <select
          className="om-control"
          required={field.required}
          value={toText(value)}
          onChange={(event) => setValue(event.target.value)}
        >
          <option value="" disabled={field.required}>Select...</option>
          {choices.map((choice) => {
            const currentValue = optionValue(choice);
            return <option key={currentValue} value={currentValue}>{choice.label ?? currentValue}</option>;
          })}
        </select>
      </label>
    );
  }
  if (field.type === "radio" || field.type === "multiselect") {
    const selectedValues = new Set(Array.isArray(value) ? value.map(String) : [toText(value)]);
    const multiple = field.type === "multiselect";
    return (
      <div className="om-field om-surface-control">
        <span className="om-field-label">{field.label}</span>
        <div className="om-choice-grid">
          {choices.map((choice) => {
            const currentValue = optionValue(choice);
            const checked = selectedValues.has(currentValue);
            return (
              <label className={checked ? "om-choice-card om-choice-card-selected" : "om-choice-card"} key={currentValue}>
                <input
                  type={multiple ? "checkbox" : "radio"}
                  name={fieldId}
                  checked={checked}
                  onChange={(event) => {
                    if (multiple) {
                      const next = new Set(selectedValues);
                      if (event.target.checked) next.add(currentValue);
                      else next.delete(currentValue);
                      setValue(Array.from(next));
                    } else {
                      setValue(currentValue);
                    }
                  }}
                />
                <span>
                  <strong>{choice.label ?? currentValue}</strong>
                  {choice.recommended ? <span className="om-choice-badge">recommended</span> : null}
                  {choice.summary ?? choice.description ? <small>{choice.summary ?? choice.description}</small> : null}
                </span>
              </label>
            );
          })}
        </div>
      </div>
    );
  }
  if (field.type === "textarea") {
    return (
      <label className="om-field om-surface-control">
        <span className="om-field-label">{field.label}</span>
        <textarea
          className="om-control om-textarea"
          required={field.required}
          placeholder={field.placeholder ?? ""}
          value={toText(value)}
          onChange={(event) => setValue(event.target.value)}
        />
      </label>
    );
  }
  return (
    <label className="om-field om-surface-control">
      <span className="om-field-label">{field.label}</span>
      <input
        className="om-control"
        type={field.type === "number" ? "number" : "text"}
        min={field.min}
        max={field.max}
        required={field.required}
        placeholder={field.placeholder ?? ""}
        value={toText(value)}
        onChange={(event) => setValue(event.target.value)}
      />
    </label>
  );
}

function SurfaceMedia({ refs }: { refs: SurfaceRef[] }) {
  if (!refs.length) return null;
  return (
    <div className="om-surface-media">
      {refs.map((ref) => {
        const mediaSrc = safeMediaSrc(ref.path);
        const title = ref.title ?? ref.label ?? ref.id ?? "Media";
        return (
          <section className="om-preview-card" key={ref.id ?? title}>
            <h3>{title}</h3>
            {ref.text ? <p>{ref.text}</p> : null}
            {ref.path ? <code>{ref.path}</code> : null}
            {ref.kind === "image" && mediaSrc ? <img src={mediaSrc} alt={ref.alt ?? title} /> : null}
            {ref.kind === "video" && mediaSrc ? <video src={mediaSrc} controls /> : null}
            {ref.kind === "audio" && mediaSrc ? <audio src={mediaSrc} controls /> : null}
          </section>
        );
      })}
    </div>
  );
}

function SurfaceItems({ items }: { items: Array<Record<string, unknown>> }) {
  if (!items.length) return null;
  const columns = Array.from(new Set(items.flatMap((item) => Object.keys(item))));
  if (!columns.length) return null;
  return (
    <div className="om-review-table om-surface-table" role="table">
      <div className="om-review-row om-review-head" role="row">
        {columns.map((column) => <span role="columnheader" key={column}>{column}</span>)}
      </div>
      {items.map((item, index) => (
        <div className="om-review-row" role="row" key={index}>
          {columns.map((column) => <span role="cell" key={column}>{toText(item[column])}</span>)}
        </div>
      ))}
    </div>
  );
}

function SurfaceOptions({ props, valueBinding }: { props: SurfaceBlockProps; valueBinding?: string }) {
  const options = props.options ?? [];
  const fieldId = props.valueFieldId ?? `${props.blockId}.selection`;
  const [value, setValue] = useBoundProp(props.value, valueBinding ?? `/values/${fieldId}`);
  const selectedValues = new Set(Array.isArray(value) ? value.map(String) : [toText(value)]);
  const multiple = Boolean(props.multiple);
  if (!options.length) return null;
  return (
    <div className="om-choice-grid om-surface-options">
      {options.map((option) => {
        const currentValue = optionValue(option);
        const checked = selectedValues.has(currentValue);
        return (
          <label className={checked ? "om-choice-card om-choice-card-selected" : "om-choice-card"} key={currentValue}>
            <input
              type={multiple ? "checkbox" : "radio"}
              name={fieldId}
              checked={checked}
              onChange={(event) => {
                if (multiple) {
                  const next = new Set(selectedValues);
                  if (event.target.checked) next.add(currentValue);
                  else next.delete(currentValue);
                  setValue(Array.from(next));
                } else {
                  setValue(currentValue);
                }
              }}
            />
            <span>
              <strong>{option.label ?? currentValue}</strong>
              {option.recommended ? <span className="om-choice-badge">recommended</span> : null}
              {option.summary ? <small>{option.summary}</small> : null}
              {option.description && option.description !== option.summary ? <small>{option.description}</small> : null}
              {option.tradeoff ? <small className="om-tradeoff">{option.tradeoff}</small> : null}
            </span>
          </label>
        );
      })}
    </div>
  );
}

function TraceRefs({ artifactRefs = [], traceRefs = [] }: { artifactRefs?: SurfaceRef[]; traceRefs?: SurfaceRef[] }) {
  if (!artifactRefs.length && !traceRefs.length) return null;
  return (
    <div className="om-trace-list">
      {artifactRefs.map((ref) => (
        <div className="om-trace-item" key={`artifact-${ref.id ?? ref.label}`}>
          <strong>{ref.label ?? ref.artifact ?? ref.id}</strong>
          {ref.artifact ? <small>{ref.artifact}{ref.summary ? ` · ${ref.summary}` : ""}</small> : null}
        </div>
      ))}
      {traceRefs.map((ref) => (
        <div className="om-trace-item" key={`trace-${ref.id ?? ref.label}`}>
          <strong>{ref.label ?? ref.id}</strong>
          <small>{ref.source}{ref.summary ? ` · ${ref.summary}` : ""}</small>
        </div>
      ))}
    </div>
  );
}

function SurfaceBlock({
  props,
  bindings,
  tone = "default"
}: {
  props: SurfaceBlockProps;
  bindings?: Record<string, string>;
  tone?: "default" | "trace" | "cockpit";
}) {
  return (
    <section className={`om-surface-block om-surface-${tone}`} data-block-id={props.blockId}>
      <header>
        <h2>{props.title}</h2>
        {props.description ? <p>{props.description}</p> : null}
      </header>
      <SurfaceOptions props={props} valueBinding={bindings?.value} />
      <SurfaceMedia refs={props.mediaRefs ?? []} />
      <SurfaceItems items={props.items ?? []} />
      {[...(props.fields ?? []), ...(props.annotationFields ?? [])].map((field) => (
        <SurfaceFieldControl blockId={props.blockId} field={field} key={field.id} />
      ))}
      <TraceRefs artifactRefs={props.artifactRefs} traceRefs={props.traceRefs} />
    </section>
  );
}

function WorkspaceShell({ props, children }: { props: Parameters<typeof ShellFrame>[0]["props"]; children?: React.ReactNode }) {
  return <ShellFrame props={props} variant="workspace">{children}</ShellFrame>;
}

function CockpitShell({ props, children }: { props: Parameters<typeof ShellFrame>[0]["props"]; children?: React.ReactNode }) {
  return <ShellFrame props={props} variant="cockpit">{children}</ShellFrame>;
}

function BriefWorksheet({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function EvidenceAlignment({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function ConceptComparison({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function RuntimeComparison({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function ScriptReview({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function ScenePlanReview({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function ProductReferencePicker({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function MediaCompare({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function AssetAnnotation({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function MusicReview({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function ApprovalChecklistItem({
  blockId,
  item
}: {
  blockId: string;
  item: Record<string, unknown>;
}) {
  const itemId = surfaceSlug(item.id ?? item.label, "approval");
  const [value, setValue] = useSurfaceValue(`${blockId}.${itemId}`);
  const label = toText(item.label ?? item.id ?? "Approval");
  return (
    <label className="om-inline-check om-surface-control" data-field-id={`${blockId}.${itemId}`}>
      <input
        type="checkbox"
        checked={Boolean(value)}
        onChange={(event) => setValue(event.target.checked)}
      />
      <span>
        {label}
        {item.required === false ? null : <span className="om-required">required</span>}
      </span>
    </label>
  );
}

function ApprovalChecklist({ props }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return (
    <section className="om-surface-block om-surface-default" data-block-id={props.blockId}>
      <header>
        <h2>{props.title}</h2>
        {props.description ? <p>{props.description}</p> : null}
      </header>
      <div className="om-approval-list">
        {(props.items ?? []).map((item, index) => (
          <ApprovalChecklistItem blockId={props.blockId} item={item} key={toText(item.id ?? item.label ?? index)} />
        ))}
      </div>
      {[...(props.fields ?? []), ...(props.annotationFields ?? [])].map((field) => (
        <SurfaceFieldControl blockId={props.blockId} field={field} key={field.id} />
      ))}
      <TraceRefs artifactRefs={props.artifactRefs} traceRefs={props.traceRefs} />
    </section>
  );
}

function RevisionPatch({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} />;
}

function ArtifactTracePanel({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} tone="trace" />;
}

function CockpitTimeline({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} tone="cockpit" />;
}

function CockpitArtifactGallery({ props, bindings }: { props: SurfaceBlockProps; bindings?: Record<string, string> }) {
  return <SurfaceBlock props={props} bindings={bindings} tone="cockpit" />;
}

function Section({ props, children }: { props: { title: string; description?: string | null }; children?: React.ReactNode }) {
  return (
    <section className="om-section">
      <header>
        <h2>{props.title}</h2>
        {props.description ? <p>{props.description}</p> : null}
      </header>
      {children}
    </section>
  );
}

function ActionBar({ props }: { props: { actions: Array<{ id: string; label: string; kind: string; recommended?: boolean }>; submitUrl?: string | null; previewOnly?: boolean } }) {
  const store = useStateStore();
  const [submitting, setSubmitting] = useState(false);

  async function submit(action: string) {
    const submitUrl = resolveSameOriginSubmitUrl(window.location.href);
    if (!submitUrl || props.previewOnly) {
      store.set("/status/message", "Preview only. Start GenUI in serve mode to submit this surface.");
      document.getElementById("status")?.focus();
      return;
    }
    const viewSpec = (window as typeof window & { __VIDEO_PRODUCTION_BUDDY_VIEW_SPEC__?: VideoProductionBuddyViewSpec }).__VIDEO_PRODUCTION_BUDDY_VIEW_SPEC__;
    if (!isJsonRenderSurfaceSpec(viewSpec)) return;
    setSubmitting(true);
    store.set("/status/message", "Submitting...");
    try {
      const response = await fetch(submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildSubmissionPayload(action, viewSpec, store.getSnapshot()))
      });
      const text = await response.text();
      const result = text ? JSON.parse(text) as { error?: string; response_path?: string } : {};
      if (!response.ok) throw new Error(result.error || text || response.statusText);
      store.set("/status/message", `Submitted. Response saved to ${result.response_path ?? "response.json"}. Return to the agent to continue.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      store.set("/status/message", `Submission failed: ${message}`);
      setSubmitting(false);
    } finally {
      document.getElementById("status")?.focus();
    }
  }

  return (
    <div className="om-action-bar">
      {props.actions.map((action) => (
        <button
          type="button"
          key={action.id}
          className={action.recommended ? "om-action om-action-primary" : "om-action"}
          disabled={submitting}
          onClick={() => void submit(action.kind)}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}

export const { registry } = defineRegistry(catalog, {
  components: {
    WorkspaceShell,
    CockpitShell,
    Section,
    InfoCard,
    TextInputField,
    TextAreaField,
    SelectField,
    ChoiceGroupField,
    CheckboxField,
    NumberField,
    UrlField,
    FilePathField,
    ApprovalField,
    MediaPreviewCard,
    ReviewGrid,
    BriefWorksheet,
    EvidenceAlignment,
    ConceptComparison,
    RuntimeComparison,
    ScriptReview,
    ScenePlanReview,
    ProductReferencePicker,
    MediaCompare,
    AssetAnnotation,
    MusicReview,
    ApprovalChecklist,
    RevisionPatch,
    ArtifactTracePanel,
    CockpitTimeline,
    CockpitArtifactGallery,
    ActionBar
  }
});
