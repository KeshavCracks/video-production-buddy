import { defineCatalog } from "@json-render/core";
import { schema } from "@json-render/react/schema";
import { z } from "zod";

const nullableString = z.string().nullable().optional();
const choiceSchema = z.object({
  value: z.string(),
  label: z.string(),
  description: nullableString,
  recommended: z.boolean().optional(),
  preview: z.record(z.string(), z.unknown()).optional()
});

const bindingSchema = z.object({
  artifact: z.string(),
  path: z.string()
}).optional();

const layoutHintSchema = z.object({
  columns: z.number().int().min(1).max(4).optional(),
  density: z.enum(["compact", "normal", "spacious"]).optional(),
  grouping: z.string().optional()
}).nullable().optional();

const displayHintSchema = z.object({
  component: z.string().optional(),
  width: z.enum(["full", "half", "third"]).optional(),
  emphasis: z.enum(["normal", "recommended", "warning"]).optional()
}).nullable().optional();

const baseFieldProps = {
  fieldId: z.string(),
  label: z.string(),
  value: z.unknown(),
  required: z.boolean().optional(),
  helpText: nullableString,
  recommended: nullableString,
  placeholder: nullableString,
  binding: bindingSchema,
  display: displayHintSchema
};

const actionSchema = z.object({
  id: z.string(),
  label: z.string(),
  kind: z.enum(["submit", "approve", "revise", "abort", "open_gate", "refresh"]),
  recommended: z.boolean().optional()
});

export const VIDEO_PRODUCTION_BUDDY_COMPONENTS = [
  "WorkspaceShell",
  "CockpitShell",
  "Section",
  "InfoCard",
  "TextInputField",
  "TextAreaField",
  "SelectField",
  "ChoiceGroupField",
  "CheckboxField",
  "NumberField",
  "UrlField",
  "FilePathField",
  "ApprovalField",
  "MediaPreviewCard",
  "ReviewGrid",
  "BriefWorksheet",
  "EvidenceAlignment",
  "ConceptComparison",
  "RuntimeComparison",
  "ScriptReview",
  "ScenePlanReview",
  "ProductReferencePicker",
  "MediaCompare",
  "AssetAnnotation",
  "MusicReview",
  "ApprovalChecklist",
  "RevisionPatch",
  "ArtifactTracePanel",
  "CockpitTimeline",
  "CockpitArtifactGallery",
  "ActionBar"
] as const;

const refSchema = z.object({
  id: z.string().optional(),
  title: z.string().optional(),
  label: z.string().optional(),
  kind: z.string().optional(),
  path: z.string().optional(),
  text: z.string().optional(),
  alt: z.string().optional(),
  artifact: z.string().optional(),
  source: z.string().optional(),
  summary: z.string().optional(),
  status: z.string().optional()
});
const surfaceOptionSchema = z.object({
  id: z.string().optional(),
  value: z.string().optional(),
  label: z.string().optional(),
  summary: z.string().optional(),
  description: z.string().optional(),
  tradeoff: z.string().optional(),
  recommended: z.boolean().optional()
});
const visibleIfSchema = z.object({
  field: z.string(),
  operator: z.enum(["equals", "not_equals", "not_empty", "empty"]),
  value: z.unknown().optional()
}).optional();
const surfaceFieldSchema = z.object({
  id: z.string(),
  label: z.string(),
  type: z.string(),
  required: z.boolean().optional(),
  placeholder: nullableString,
  choices: z.array(surfaceOptionSchema).optional(),
  min: z.number().optional(),
  max: z.number().optional(),
  target_ref: z.string().optional(),
  help_text: z.string().optional(),
  recommended: z.string().optional(),
  binding: bindingSchema,
  display: displayHintSchema,
  visible_if: visibleIfSchema
});
const surfaceBlockProps = z.object({
  blockId: z.string(),
  title: z.string(),
  description: nullableString,
  binding: bindingSchema,
  value: z.unknown().optional(),
  valueFieldId: z.string().optional(),
  valueFieldIds: z.array(z.string()).optional(),
  multiple: z.boolean().optional(),
  options: z.array(surfaceOptionSchema).optional(),
  fields: z.array(surfaceFieldSchema).optional(),
  annotationFields: z.array(surfaceFieldSchema).optional(),
  items: z.array(z.record(z.string(), z.unknown())).optional(),
  mediaRefs: z.array(refSchema).optional(),
  artifactRefs: z.array(refSchema).optional(),
  traceRefs: z.array(refSchema).optional()
});

export const componentDefinitions = {
    WorkspaceShell: {
      props: z.object({
        title: z.string(),
        description: nullableString,
        surfaceId: z.string(),
        projectId: z.string().optional(),
        pipelineType: z.string().optional(),
        stage: z.string().optional(),
        gate: z.string().optional(),
        mode: z.string().optional(),
        mediaRefs: z.array(refSchema).optional(),
        artifactRefs: z.array(refSchema).optional(),
        traceRefs: z.array(refSchema).optional()
      }),
      description: "GenUI compatibility product workspace shell for one human gate."
    },
    CockpitShell: {
      props: z.object({
        title: z.string(),
        description: nullableString,
        surfaceId: z.string(),
        projectId: z.string().optional(),
        pipelineType: z.string().optional(),
        stage: z.string().optional(),
        gate: z.string().optional(),
        mode: z.string().optional(),
        mediaRefs: z.array(refSchema).optional(),
        artifactRefs: z.array(refSchema).optional(),
        traceRefs: z.array(refSchema).optional()
      }),
      description: "Read-only GenUI compatibility project cockpit shell."
    },
    Section: {
      props: z.object({
        sectionId: z.string(),
        title: z.string(),
        description: nullableString,
        layout: layoutHintSchema
      }),
      description: "A grouped worksheet section."
    },
    InfoCard: {
      props: z.object({
        label: z.string(),
        helpText: nullableString,
        recommended: nullableString
      }),
      description: "Read-only contextual information."
    },
    TextInputField: {
      props: z.object(baseFieldProps),
      description: "Single-line text input bound to GenUI state."
    },
    TextAreaField: {
      props: z.object(baseFieldProps),
      description: "Multi-line text input bound to GenUI state."
    },
    SelectField: {
      props: z.object({
        ...baseFieldProps,
        choices: z.array(choiceSchema).optional()
      }),
      description: "Select input bound to one configured value."
    },
    ChoiceGroupField: {
      props: z.object({
        ...baseFieldProps,
        choices: z.array(choiceSchema).optional(),
        multiple: z.boolean().optional()
      }),
      description: "Radio or multiselect choice group bound to GenUI state."
    },
    CheckboxField: {
      props: z.object(baseFieldProps),
      description: "Boolean checkbox bound to GenUI state."
    },
    NumberField: {
      props: z.object({
        ...baseFieldProps,
        min: z.number().optional(),
        max: z.number().optional()
      }),
      description: "Numeric input bound to GenUI state."
    },
    UrlField: {
      props: z.object(baseFieldProps),
      description: "URL input bound to GenUI state."
    },
    FilePathField: {
      props: z.object(baseFieldProps),
      description: "Local path input bound to GenUI state."
    },
    ApprovalField: {
      props: z.object(baseFieldProps),
      description: "Explicit human approval toggle bound to GenUI state."
    },
    MediaPreviewCard: {
      props: z.object({
        title: z.string(),
        kind: z.enum(["text", "image", "video", "audio", "path"]),
        text: nullableString,
        path: nullableString,
        alt: nullableString
      }),
      description: "Safe preview card for project-contained media or text references."
    },
    ReviewGrid: {
      props: z.object({
        title: z.string(),
        items: z.array(z.record(z.string(), z.unknown()))
      }),
      description: "Dense review grid for comparing generated options."
    },
    BriefWorksheet: {
      props: surfaceBlockProps,
      description: "GenUI compatibility brief and context review block."
    },
    EvidenceAlignment: {
      props: surfaceBlockProps,
      description: "GenUI compatibility evidence alignment block."
    },
    ConceptComparison: {
      props: surfaceBlockProps,
      description: "GenUI compatibility side-by-side concept comparison block."
    },
    RuntimeComparison: {
      props: surfaceBlockProps,
      description: "GenUI compatibility runtime comparison and selection block."
    },
    ScriptReview: {
      props: surfaceBlockProps,
      description: "GenUI compatibility script review block."
    },
    ScenePlanReview: {
      props: surfaceBlockProps,
      description: "GenUI compatibility scene plan review block."
    },
    ProductReferencePicker: {
      props: surfaceBlockProps,
      description: "GenUI compatibility product reference selection block."
    },
    MediaCompare: {
      props: surfaceBlockProps,
      description: "GenUI compatibility media comparison and annotation block."
    },
    AssetAnnotation: {
      props: surfaceBlockProps,
      description: "GenUI compatibility generated asset annotation block."
    },
    MusicReview: {
      props: surfaceBlockProps,
      description: "GenUI compatibility music review block."
    },
    ApprovalChecklist: {
      props: surfaceBlockProps,
      description: "GenUI compatibility explicit approval attestation checklist."
    },
    RevisionPatch: {
      props: surfaceBlockProps,
      description: "GenUI compatibility structured revision patch capture block."
    },
    ArtifactTracePanel: {
      props: surfaceBlockProps,
      description: "GenUI compatibility artifact and source trace panel."
    },
    CockpitTimeline: {
      props: surfaceBlockProps,
      description: "Read-only project pipeline timeline block."
    },
    CockpitArtifactGallery: {
      props: surfaceBlockProps,
      description: "Read-only project artifact gallery block."
    },
    ActionBar: {
      props: z.object({
        actions: z.array(actionSchema),
        submitUrl: z.string().nullable().optional(),
        previewOnly: z.boolean().optional()
      }),
      description: "Submit actions that write only ui_surface_response via the local server."
    }
  };

export const catalog = defineCatalog(schema, {
  components: componentDefinitions,
  actions: {}
});
