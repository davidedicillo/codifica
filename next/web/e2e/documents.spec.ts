import { test, expect, type Page } from "@playwright/test";
const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAABgAAAAQCAIAAACDRijCAAAAI0lEQVR4nGP8lBPMQA3ARBVTGEYNIgaMBjZhMBpGhMHgCyMAAtUB0WsFPcgAAAAASUVORK5CYII=", "base64");

async function channel(page: Page) {
  await page.goto("/");
  await page.getByLabel("Your name").fill("Davide");
  await page.getByLabel("Email address").fill("davide@example.com");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Create channel", exact: true }).click();
  const name = `Documents ${Date.now()}`;
  await page.getByLabel("Channel name").fill(name);
  await page.getByRole("dialog").getByRole("button", { name: "Create channel", exact: true }).click();
  await expect(page.getByRole("heading", { name, exact: true }).first()).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toBeVisible();
}

test("empty + Document opens upload, Markdown can be imported, attached and reopened", async ({ page }) => {
  await channel(page);
  await page.getByRole("button", { name: "Attach document", exact: true }).click();
  const picker = page.getByRole("dialog", { name: "Documents" });
  await expect(picker.getByRole("button", { name: "Upload file" })).toBeVisible();
  await picker.getByLabel("Upload document file").setInputFiles({ name: "brief.md", mimeType: "text/markdown", buffer: Buffer.from("# Project brief\nShared **context**.") });
  await expect(picker.getByRole("heading", { name: "Project brief" })).toBeVisible();
  await picker.getByRole("button", { name: "Attach to message" }).click();
  await expect(picker).not.toBeVisible();
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await page.locator("article").getByRole("button", { name: /brief.*revision 1/ }).click();
  await expect(page.locator(".side-panel").getByRole("heading", { name: "Project brief" })).toBeVisible();
  await page.reload();
  await page.locator("article").getByRole("button", { name: /brief.*revision 1/ }).click();
  await expect(page.locator(".side-panel").getByRole("heading", { name: "Project brief" })).toBeVisible();
});

test("image preview, download and attachment survive reload on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await channel(page);
  await page.getByRole("button", { name: "Attach document", exact: true }).click();
  const picker = page.getByRole("dialog", { name: "Documents" });
  await picker.getByLabel("Upload document file").setInputFiles({ name: "reference.png", mimeType: "image/png", buffer: png });
  const preview = picker.getByRole("img", { name: "reference.png" });
  await expect(preview).toBeVisible();
  await expect.poll(() => preview.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(24);
  const downloadEvent = page.waitForEvent("download");
  await picker.getByRole("link", { name: "Download image" }).click();
  expect((await downloadEvent).suggestedFilename()).toBe("reference.png");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "../verification/document-upload-mobile.png", fullPage: true });
  await picker.getByRole("button", { name: "Attach to message" }).click();
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator("article").getByRole("img", { name: "reference.png" })).toBeVisible();
  await page.reload();
  const inline = page.locator("article").getByRole("img", { name: "reference.png" });
  await expect.poll(() => inline.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBe(24);
  await inline.click();
  await expect(page.locator(".side-panel").getByRole("link", { name: "Download image" })).toBeVisible();
});

test("thread document picker supports dropping a file without losing reply draft", async ({ page }) => {
  await channel(page);
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Discuss this");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await page.getByRole("button", { name: "Open thread" }).click();
  const thread = page.locator(".thread-panel");
  await thread.getByRole("textbox", { name: "Reply", exact: true }).fill("Here are the notes");
  await thread.getByRole("button", { name: "Attach document" }).click();
  const picker = page.getByRole("dialog", { name: "Documents" });
  const data = await page.evaluateHandle(() => {
    const transfer = new DataTransfer();
    transfer.items.add(new File(["# Thread notes"], "thread.md", { type: "text/markdown" }));
    return transfer;
  });
  await picker.locator(".docs-panel").dispatchEvent("drop", { dataTransfer: data });
  await expect(picker.getByRole("heading", { name: "Thread notes" })).toBeVisible();
  await page.screenshot({ path: "../verification/document-upload-desktop.png", fullPage: true });
  await picker.getByRole("button", { name: "Attach to message" }).click();
  await expect(thread.getByRole("textbox", { name: "Reply", exact: true })).toHaveValue("Here are the notes");
  await thread.getByRole("button", { name: "Reply", exact: true }).click();
  await expect(thread.locator("article").getByRole("button", { name: /thread.*revision 1/ })).toBeVisible();
});

test("upload errors are visible in empty channels and an uncertain upload retries once", async ({ page }) => {
  await channel(page);
  await page.getByRole("button", { name: "Attach document" }).click();
  const picker = page.getByRole("dialog", { name: "Documents" });
  await picker.getByLabel("Upload document file").setInputFiles({ name: "bad.pdf", mimeType: "application/pdf", buffer: Buffer.from("bad") });
  await expect(picker.getByRole("alert")).toContainText("Choose a .md");
  let attempts = 0;
  await page.route("**/docs/upload", async route => {
    attempts++;
    if (attempts === 1) { await route.fetch(); await route.abort(); }
    else await route.continue();
  });
  await picker.getByLabel("Upload document file").setInputFiles({ name: "retry.md", mimeType: "text/markdown", buffer: Buffer.from("# Recovered upload") });
  await picker.getByRole("button", { name: "Retry upload" }).click();
  await expect(picker.getByRole("heading", { name: "Recovered upload" })).toBeVisible();
  const id = await page.evaluate(() => sessionStorage.getItem("codifica:active"));
  const docs = await (await page.request.get(`/api/v1/channels/${id}/docs`)).json();
  expect(docs.documents).toHaveLength(1);
  expect(attempts).toBe(2);
});
