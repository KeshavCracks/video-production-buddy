import { describe, expect, it } from "vitest";
import { catalog, componentDefinitions, VIDEO_PRODUCTION_BUDDY_COMPONENTS } from "./catalog";

describe("Video Production Buddy json-render catalog", () => {
  it("registers the fixed GenUI component catalog", () => {
    expect(VIDEO_PRODUCTION_BUDDY_COMPONENTS).toEqual([
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
    ]);
    expect(Object.keys(componentDefinitions)).toEqual(VIDEO_PRODUCTION_BUDDY_COMPONENTS);
    expect(typeof catalog.prompt).toBe("function");
  });
});
