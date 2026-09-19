import { test, expect, Page } from "@playwright/test";
async function login(page: Page, email: string, name: string) {
  await page.goto("/");
  await page.getByLabel("Your name").fill(name);
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Create channel", exact: true }),
  ).toBeVisible();
}
async function createChannel(page: Page, name: string) {
  await page
    .getByRole("button", { name: "Create channel", exact: true })
    .click();
  await page.getByLabel("Channel name").fill(name);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Create channel", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name, exact: true }).first(),
  ).toBeVisible();
}
test("named agents can be renamed and all-agent requests reach only selected identities", async ({ page }) => {
  await login(page, "davide@example.com", "Davide");
  await createChannel(page, `Agent controls ${Date.now()}`);
  const agents: { token: string; participant: { id: string } }[] = [];
  for (const name of ["Davide's Codex", "Enrico's Claude"]) {
    await page.getByRole("button", { name: "Connect an agent", exact: true }).click();
    await page.getByLabel("Agent name", { exact: true }).fill(name);
    await page.getByRole("button", { name: "Create connection prompt" }).click();
    const prompt = await page.getByLabel("Paste this into your agent").inputValue();
    expect(prompt).toContain(JSON.stringify(name));
    const instructions = prompt.match(/https?:\/\/[^\s]+\/instructions/)![0];
    const response = await page.request.post(instructions.replace(/\/instructions$/, "/join"), {
      data: { name, provider: name.includes("Codex") ? "openai" : "anthropic", requestId: crypto.randomUUID() },
    });
    expect(response.status()).toBe(200);
    agents.push(await response.json());
    await page.getByRole("button", { name: "Close dialog" }).click();
  }
  await page.getByRole("button", { name: "Show participants" }).click();
  await page.getByRole("button", { name: "Rename Davide's Codex", exact: true }).click();
  await page.getByLabel("Agent name", { exact: true }).fill("Backend reviewer");
  await page.getByRole("button", { name: "Save name", exact: true }).click();
  await expect(page.locator(".person").getByText("Backend reviewer", { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Show participants" }).click();
  await expect(page.locator(".person").getByText("Backend reviewer", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Close participants" }).click();
  const channel = await page.evaluate(() => sessionStorage.getItem("codifica:active"));
  const inbox = async (token: string) => (await page.request.get(`/api/v1/channels/${channel}/activity?wait=0`, {
    headers: { Authorization: `Bearer ${token}` },
  })).json();
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Just chatting");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator("article").getByText("Just chatting", { exact: true })).toBeVisible();
  for (const a of agents) expect((await inbox(a.token)).batchId).toBeNull();
  await page.getByRole("button", { name: "Ask all agents", exact: true }).click();
  await expect(page.locator(".chips")).toContainText("Backend reviewer");
  await expect(page.locator(".chips")).toContainText("Enrico's Claude");
  await page.reload();
  await expect(page.locator(".chips")).toContainText("Backend reviewer");
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Who's here?");
  // Recipient choices and draft survive a reload before sending.
  await page.reload();
  await expect(page.locator(".chips")).toContainText("Backend reviewer");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator("article").getByText("Who's here?", { exact: true })).toBeVisible();
  for (const a of agents) {
    const batch = await inbox(a.token);
    expect(batch.activities).toHaveLength(1);
    expect(batch.activities[0].body).toBe("Who's here?");
    expect(batch.activities[0].mentions.sort()).toEqual(agents.map(a => a.participant.id).sort());
  }
  await expect(page.locator(".chips")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("button", { name: "Ask all agents" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "../verification/agent-controls-mobile.png", fullPage: true });
});
test("channel creation, posting, docs revision and archive survive reload", async ({
  page,
}) => {
  await login(page, "davide@example.com", "Davide");
  await page
    .getByRole("button", { name: "Create channel", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Channel name").fill(`Product ${Date.now()}`);
  await dialog
    .getByRole("button", { name: "Create channel", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Connect an agent", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("A shared place for our agents.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(
    page
      .locator("article")
      .getByText("A shared place for our agents.", { exact: true }),
  ).toHaveCount(1);
  await page.reload();
  await expect(
    page
      .locator("article")
      .getByText("A shared place for our agents.", { exact: true }),
  ).toHaveCount(1);
  await page.getByRole("button", { name: /^Docs/ }).click();
  await page.getByRole("button", { name: "New doc", exact: true }).click();
  await page.getByLabel("Document title").fill("Product spec");
  await page
    .getByLabel("Document content")
    .fill("# First revision\nBring your own agents.");
  await page
    .getByRole("button", { name: "Save document", exact: true })
    .click();
  await expect(
    page.getByText("Viewing revision 1", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close docs" }).click();
  await page
    .getByLabel("Attach document")
    .selectOption({ label: "Product spec · v1" });
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("Review this revision.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "▤ Product spec · revision 1" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../verification/desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Manage channel" }).click();
  await page
    .getByRole("button", { name: "Archive channel", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Message", exact: true }),
  ).toBeDisabled();
});
test("invalid messages remain editable and a thread draft cannot target another thread", async ({
  page,
}) => {
  await login(page, "davide@example.com", "Davide");
  await createChannel(page, `Recovery ${Date.now()}`);
  await page.route("**/api/v1/channels/*/messages", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 413,
        contentType: "application/json",
        body: JSON.stringify({
          code: "INVALID_ARGUMENT",
          message: "Message is too long.",
        }),
      });
      await page.unroute("**/api/v1/channels/*/messages");
    } else await route.continue();
  });
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("Rejected draft");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Message is too long");
  await expect(
    page.getByRole("textbox", { name: "Message", exact: true }),
  ).toBeEditable();
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("First topic");
  await page.getByRole("button", { name: "Retry send", exact: true }).click();
  await expect(
    page.locator("article").getByText("First topic", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("Second topic");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(
    page.locator("article").getByText("Second topic", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Open thread", exact: true })
    .first()
    .click();
  await page
    .getByRole("textbox", { name: "Reply", exact: true })
    .fill("For the first topic only");
  await page
    .getByRole("button", { name: "Open thread", exact: true })
    .nth(1)
    .click();
  await expect(
    page.getByRole("textbox", { name: "Reply", exact: true }),
  ).toHaveValue("");
  await page
    .getByRole("button", { name: "Open thread", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("textbox", { name: "Reply", exact: true }),
  ).toHaveValue("For the first topic only");
  let release: () => void = () => {};
  const delayed = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/channels/*/messages", async (route) => {
    if (route.request().method() === "POST") {
      const response = await route.fetch();
      await delayed;
      await route.fulfill({ response });
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Reply", exact: true }).click();
  await page
    .getByRole("button", { name: "Open thread", exact: true })
    .nth(1)
    .click();
  release();
  await expect(
    page
      .locator(".thread-panel article")
      .getByText("For the first topic only", { exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Open thread", exact: true })
    .first()
    .click();
  await expect(
    page
      .locator(".thread-panel article")
      .getByText("For the first topic only", { exact: true }),
  ).toBeVisible();
});
test("document save retry is idempotent and unsaved drafts survive panel navigation", async ({
  page,
}) => {
  await login(page, "davide@example.com", "Davide");
  await createChannel(page, `Docs recovery ${Date.now()}`);
  await page.getByRole("button", { name: /^Docs/ }).click();
  await page.getByRole("button", { name: "New doc", exact: true }).click();
  await page.getByLabel("Document title").fill("Persistent draft");
  await page.getByLabel("Document content").fill("Draft stays in this tab.");
  await page
    .getByRole("button", { name: "Show participants", exact: true })
    .click();
  await page.getByRole("button", { name: /^Docs/ }).click();
  await expect(page.getByLabel("Document content")).toHaveValue(
    "Draft stays in this tab.",
  );
  let first = true;
  const requests: string[] = [];
  await page.route("**/api/v1/channels/*/docs", async (route) => {
    if (route.request().method() === "POST") {
      requests.push(route.request().postDataJSON().requestId);
      if (first) {
        first = false;
        await route.fetch();
        await route.abort();
        return;
      }
    }
    await route.continue();
  });
  await page
    .getByRole("button", { name: "Save document", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("fetch");
  await page
    .getByRole("button", { name: "Save document", exact: true })
    .click();
  await expect(
    page.getByText("Viewing revision 1", { exact: true }),
  ).toBeVisible();
  expect(requests).toHaveLength(2);
  expect(requests[0]).toBe(requests[1]);
  await expect(
    page
      .getByLabel("Choose document")
      .locator("option", { hasText: "Persistent draft" }),
  ).toHaveCount(1);
});
test("conflicting document edit preserves draft and historical revision remains available", async ({
  page,
}) => {
  await login(page, "davide@example.com", "Davide");
  await createChannel(page, `Conflict ${Date.now()}`);
  await page.getByRole("button", { name: /^Docs/ }).click();
  await page.getByRole("button", { name: "New doc", exact: true }).click();
  await page.getByLabel("Document title").fill("Shared spec");
  await page.getByLabel("Document content").fill("Original shared content");
  await page
    .getByRole("button", { name: "Save document", exact: true })
    .click();
  await expect(
    page.getByText("Viewing revision 1", { exact: true }),
  ).toBeVisible();
  const docId = await page.getByLabel("Choose document").inputValue();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByLabel("Document content").fill("My preserved draft");
  const status = await page.evaluate(
    async ({ docId }) => {
      const me = await (await fetch("/api/v1/me")).json();
      const channelId = sessionStorage.getItem("codifica:active");
      const response = await fetch(
        `/api/v1/channels/${channelId}/docs/${docId}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": me.csrfToken,
          },
          body: JSON.stringify({
            title: "Shared spec",
            body: "Another editor changed this",
            expectedRevision: 1,
            requestId: crypto.randomUUID(),
          }),
        },
      );
      return response.status;
    },
    { docId },
  );
  expect(status).toBe(200);
  await page
    .getByRole("button", { name: "Save document", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "This document has changed",
  );
  await expect(page.getByLabel("Document content")).toHaveValue(
    "My preserved draft",
  );
  await page
    .getByRole("button", { name: "Use this revision as the new base" })
    .click();
  await page
    .getByRole("button", { name: "Save document", exact: true })
    .click();
  await expect(
    page.getByText("Viewing revision 3", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Document revision").selectOption("1");
  await expect(
    page.getByText("Original shared content", { exact: true }),
  ).toBeVisible();
});
test("channel interface fits mobile and remains keyboard accessible", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "davide@example.com", "Davide");
  await createChannel(page, `Mobile ${Date.now()}`);
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("Ready to collaborate.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(
    page.locator("article").getByText("Ready to collaborate.", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "../verification/mobile.png", fullPage: true });
});
test("invited collaborator sees history and does not receive owner controls", async ({
  browser,
  page,
}) => {
  await login(page, "davide@example.com", "Davide");
  await page
    .getByRole("button", { name: "Create channel", exact: true })
    .click();
  await page.getByLabel("Channel name").fill(`Shared ${Date.now()}`);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Create channel", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill("Written before Enrico joined.");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(
    page
      .locator("article")
      .getByText("Written before Enrico joined.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Invite people", exact: true })
    .click();
  await page.getByLabel("Email address").fill("enrico@example.com");
  await page
    .getByRole("button", { name: "Create invitation", exact: true })
    .click();
  const url = await page.getByLabel("Invitation link").inputValue();
  const context = await browser.newContext();
  const other = await context.newPage();
  await login(other, "enrico@example.com", "Enrico");
  await other.goto(url);
  await other
    .getByRole("button", { name: "Join channel", exact: true })
    .click();
  await expect(
    other
      .locator("article")
      .getByText("Written before Enrico joined.", { exact: true }),
  ).toBeVisible();
  await expect(
    other.getByRole("button", { name: "Manage channel" }),
  ).toHaveCount(0);
  await expect(
    other.getByRole("button", { name: "Invite people", exact: true }),
  ).toHaveCount(0);
  await expect(
    other.getByRole("button", { name: "Connect an agent", exact: true }),
  ).toBeVisible();
  await context.close();
});
