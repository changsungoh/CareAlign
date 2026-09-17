import { expect, test } from "@playwright/test";

test("synthetic comparison reaches source-linked clarification", async ({ page }) => {
  await page.route("**/api/analyze", async (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      case_id: "case-demo", status: "needs_review", demo_mode: true,
      documents: [
        { document_id: "old", document_type: "Discharge", document_date: "2026-08-01", raw_text: "twice a day" },
        { document_id: "new", document_type: "Prescription", document_date: "2026-09-01", raw_text: "once a day" },
      ],
      safety_message: "Confirm every flag with a qualified healthcare professional.",
      instructions: [],
      conflicts: [{ conflict_id: "c1", conflict_type: "frequency_difference",
        medication_name: "metoprolol tartrate", instruction_ids: ["old-i1", "new-i1"],
        summary: "frequency changed from twice a day to once a day",
        clarification_question: "Which instruction should I follow?", status: "validated",
        confidence: 0.96, evidence_spans: ["twice a day", "once a day"] }],
      metadata: {
        app_version: "0.3.0", release_sha: "test-release", request_id: "e2e-request",
        model_name: "demo", prompt_version: "v1", rules_version: "v1",
        provider_calls: 0, input_tokens: 0, output_tokens: 0, analysis_duration_ms: 12,
      },
    }),
  }));
  await page.goto("/");
  await page.getByLabel(/I confirm this is synthetic data/).check();
  await page.getByRole("button", { name: "Analyze care timeline" }).click();
  await expect(page.getByRole("heading", { name: /1 difference still needs a response/ })).toBeVisible();
  await expect(page.getByText("Which instruction should I follow?")).toBeVisible();
  await page.getByLabel(/Record care team response/).fill("Synthetic response: once daily.");
  await page.getByRole("button", { name: "Save to this browser session" }).click();
  await expect(page.getByRole("heading", { name: "Responses recorded for every difference" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "1 response recorded" })).toBeVisible();
  await expect(page.getByText("User-entered · not verified by CareAlign", { exact: false })).toBeVisible();
});

test("timeline accepts up to five documents and allows removal", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Add document" }).click();
  await expect(page.getByText("Document 3", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Remove document 3" }).click();
  await expect(page.getByText("Document 3", { exact: true })).toHaveCount(0);
});
