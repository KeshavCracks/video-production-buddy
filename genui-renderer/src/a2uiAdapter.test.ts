import { describe, expect, it } from "vitest";
import { createVideoProductionBuddyA2UIRegistry, videoProductionBuddyA2UISchema } from "./a2uiAdapter";

describe("Video Production Buddy A2UI adapter", () => {
  it("registers product-level surfaces in the framework catalog", () => {
    const schemaText = JSON.stringify(videoProductionBuddyA2UISchema);

    expect(schemaText).toContain("GateWorkspace");
    expect(schemaText).toContain("MediaReviewRoom");
    expect(schemaText).toContain("ProjectCockpit");
    expect(schemaText).toContain("BackgroundStatus");
    expect(schemaText).toContain("ProposalLock");
    expect(schemaText).toContain("MediaTimeline");
    expect(schemaText).toContain("MediaComparison");
    expect(schemaText).toContain("RegionAnnotation");
    expect(schemaText).toContain("IssueBoard");
    expect(schemaText).toContain("ArtifactTrace");
    expect(schemaText).toContain("RevisionPatchPreview");
    expect(schemaText).toContain("LiveStatusPanel");
    expect(schemaText).toContain("InteractionJournalPanel");
    expect(schemaText).toContain("OperationTimeline");
    expect(schemaText).toContain("ReviewCompletionPanel");
    expect(schemaText).toContain("DurableDecisionPanel");
    const registry = createVideoProductionBuddyA2UIRegistry();
    expect(registry.getRegisteredTypes()).toContain("GateWorkspace");
    expect(registry.getRegisteredTypes()).toContain("MediaReviewRoom");
    expect(registry.getRegisteredTypes()).toContain("MediaTimeline");
    expect(registry.getRegisteredTypes()).toContain("LiveStatusPanel");
    expect(registry.getRegisteredTypes()).toContain("OperationTimeline");
    expect(registry.getRegisteredTypes()).toContain("ReviewCompletionPanel");
    expect(registry.getRegisteredTypes()).toContain("DurableDecisionPanel");
  });
});
