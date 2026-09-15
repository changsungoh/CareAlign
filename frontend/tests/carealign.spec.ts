import { expect, test } from "@playwright/test";

test("synthetic comparison reaches source-linked clarification", async ({ page }) => {
  await page.route("**/api/analyze", async (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      case_id: "case-demo", status: "needs_review", demo_mode: true,
      safety_message: "Confirm every flag with a qualified healthcare professional.",
      instructions: [],
      conflicts: [{ conflict_id: "c1", conflict_type: "frequency_difference",
        medication_name: "metoprolol tartrate", instruction_ids: ["old-i1", "new-i1"],
        summary: "frequency changed from twice a day to once a day",
        clarification_question: "Which instruction should I follow?", status: "validated",
        confidence: 0.96, evidence_spans: ["twice a day", "once a day"] }],
      metadata: { model_name: "demo", prompt_version: "v1", rules_version: "v1" },
    }),
  }));
  await page.goto("/");
  await page.getByLabel(/I confirm this is synthetic data/).check();
  await page.getByRole("button", { name: "Compare instructions" }).click();
  await expect(page.getByRole("heading", { name: /1 potential difference/ })).toBeVisible();
  await expect(page.getByText("Which instruction should I follow?")).toBeVisible();
});
