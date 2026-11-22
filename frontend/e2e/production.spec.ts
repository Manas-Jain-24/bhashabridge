import {expect, test} from '@playwright/test';

test.skip(!process.env.BB_PRODUCTION_ORIGIN, 'Requires scripts/test_production_stack.py --browser');

test('HTTPS invitation, progress, translation and session revocation', async ({page, context}) => {
  await page.goto('/');
  await page.getByRole('button', {name:'Create an account', exact:true}).click();
  await page.getByLabel('Username').fill('browser_learner');
  await page.getByLabel('Password', {exact:true}).fill('A synthetic production test password!');
  await page.getByLabel('Invitation code').fill(process.env.BB_BROWSER_INVITATION!);
  await page.getByRole('button', {name:'Create account', exact:true}).click();
  await expect(page.getByRole('button', {name:'Sign out', exact:true})).toBeVisible();
  const cookies = await context.cookies();
  expect(cookies.find(cookie => cookie.name === 'bb_session')).toMatchObject({
    secure:true, httpOnly:true, sameSite:'Strict',
  });
  await expect(page.getByLabel('Translation', {exact:true})).toHaveValue('local');
  await page.getByLabel('Sentence to translate').fill('Mujhe paani chahiye');
  const response = page.waitForResponse(result => result.url().endsWith('/api/analyze'));
  await page.getByRole('button', {name:'Translate', exact:true}).click();
  expect((await response).ok()).toBeTruthy();
  await expect(page.getByRole('table')).toBeVisible();
  await expect(page.getByRole('button', {name:'Sign out', exact:true})).toBeVisible();
  await page.getByRole('button', {name:'Sign out', exact:true}).click();
  await expect(page.getByRole('heading', {name:'Sign in to BhashaBridge'})).toBeVisible();
  await page.getByLabel('Username').fill('browser_learner');
  await page.getByLabel('Password', {exact:true}).fill('A synthetic production test password!');
  await page.getByRole('button', {name:'Sign in', exact:true}).click();
  await expect(page.getByRole('button', {name:'Sign out', exact:true})).toBeVisible();
});
