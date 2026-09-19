import { test, expect } from '@playwright/test';

test('email sign-in requests a code and preserves input on verification failure', async ({ page }) => {
  await page.route('**/api/v1/auth/config', r => r.fulfill({json:{devAuth:false,emailAuth:true,loginUrl:'/api/v1/auth/login'}}));
  await page.route('**/api/v1/auth/email/request', async r => {
    expect(r.request().postDataJSON()).toEqual({email:'owner@example.com'});
    await r.fulfill({json:{message:'If this email has access, a sign-in code is on its way.'}});
  });
  await page.route('**/api/v1/auth/email/verify', async r => {
    expect(r.request().postDataJSON()).toEqual({name:'Owner',code:'123456'});
    await r.fulfill({status:401,json:{message:'Invalid or expired code'}});
  });
  await page.goto('/');
  await page.getByLabel('Your name').fill('Owner');
  await page.getByLabel('Email address').fill('owner@example.com');
  await page.getByRole('button',{name:'Send sign-in code',exact:true}).click();
  await expect(page.getByText('If this email has access, a sign-in code is on its way.')).toBeVisible();
  await page.getByLabel('Sign-in code').fill('123456');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(page.getByText('Invalid or expired code')).toBeVisible();
  await expect(page.getByLabel('Sign-in code')).toHaveValue('123456');
  await page.getByRole('button',{name:'Use a different email'}).click();
  await expect(page.getByLabel('Email address')).toHaveValue('owner@example.com');
});

test('signing out after email login returns to requesting a fresh code', async ({ page }) => {
  let signedIn = false;
  await page.route('**/api/v1/auth/config', r => r.fulfill({json:{devAuth:false,emailAuth:true,loginUrl:'/api/v1/auth/login'}}));
  await page.route('**/api/v1/me', r => r.fulfill(signedIn ? {json:{user:{id:'email-user',name:'Owner',email:'owner@example.com'},csrfToken:'test'}} : {status:401,json:{message:'Sign in'}}));
  await page.route('**/api/v1/channels', r => r.fulfill({json:{channels:[]}}));
  await page.route('**/api/v1/auth/email/request', r => r.fulfill({json:{message:'Code sent'}}));
  await page.route('**/api/v1/auth/email/verify', async r => { signedIn = true; await r.fulfill({json:{}}); });
  await page.route('**/api/v1/auth/logout', async r => { signedIn = false; await r.fulfill({json:{}}); });
  await page.goto('/');
  await page.getByLabel('Your name').fill('Owner');
  await page.getByLabel('Email address').fill('owner@example.com');
  await page.getByRole('button',{name:'Send sign-in code',exact:true}).click();
  await page.getByLabel('Sign-in code').fill('123456');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByRole('button',{name:'Sign out'}).click();
  await expect(page.getByRole('button',{name:'Send sign-in code',exact:true})).toBeVisible();
  await expect(page.getByLabel('Sign-in code')).toHaveCount(0);
});
