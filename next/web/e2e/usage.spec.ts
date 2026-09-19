import { test, expect } from '@playwright/test';

test('visible authenticated sessions record activity without sending content', async ({ page }) => {
  const calls: string[] = [];
  await page.route('**/api/v1/me', r => r.fulfill({json:{user:{id:'usage-test',name:'Private name',email:'private@example.com'},csrfToken:'csrf'}}));
  await page.route('**/api/v1/channels', r => r.fulfill({json:{channels:[]}}));
  await page.route('**/api/v1/usage/active', async r => {
    calls.push(r.request().postData() || '');
    expect(r.request().headers()['x-csrf-token']).toBe('csrf');
    await r.fulfill({status:204});
  });
  await page.goto('/');
  await expect.poll(() => calls.length).toBe(1);
  expect(calls[0]).not.toContain('private');
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', {value:'hidden', configurable:true});
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect(calls).toHaveLength(1);
});

test('GA runs in an empty frame with a sanitized page location', async ({ page }) => {
  // Exercise the production-only frame on the local test host.
  await page.route('https://www.googletagmanager.com/**', r => r.fulfill({body:'',contentType:'text/javascript'}));
  await page.goto('/analytics.html');
  await expect.poll(() => page.evaluate(() => (window as any).dataLayer?.length || 0)).toBeGreaterThan(1);
  const commands = await page.evaluate(() => Array.from((window as any).dataLayer, (x: any) => Array.from(x)));
  const config = commands.find((x: any) => x[0] === 'config') as any[];
  expect(config[2].page_location).toBe('https://codifica.app/');
  expect(config[2].page_referrer).toBe('');
  expect(config[2].page_title).toBe('Codifica');
  expect(await page.locator('input, a, form').count()).toBe(0);
});
