import {test,expect} from '@playwright/test';
test('all eleven pages work and filter official objectives',async({page})=>{
 await page.goto('/');await expect(page.getByRole('heading',{name:'A little practice. A lot of progress.'})).toBeVisible();
 for(const [nav,title] of [['Full Mock Exam','Make it feel like exam day.'],['Quick Practice','Build momentum in minutes.'],['Topic-Based Practice','Focus on what matters.'],['SPL Challenges','Think in SPL.'],['Wrong Answers','Turn mistakes into progress.'],['Bookmarks','Keep the useful ones close.'],['Exam History','Your practice, recorded.'],['Performance Analytics','See where you’re growing.'],['Question Bank','Your library of understanding.'],['Settings','Make this lab your own.']]){
  await page.locator('nav').getByRole('button',{name:nav,exact:true}).click();await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible();
 }
 await page.locator('nav').getByRole('button',{name:'Question Bank',exact:true}).click();await page.getByLabel('Filter objective').selectOption('1.1');
 await expect(page.getByText('6 matching questions',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Create question'}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.getByLabel('Close dialog').click();
});
test('autosaved exam survives refresh, submits, and supports revision',async({page})=>{
 await page.goto('/');await page.locator('nav').getByRole('button',{name:'Quick Practice',exact:true}).click();
 await page.getByLabel('Custom question count').fill('2');await page.getByText('Timed practice',{exact:true}).click();
 await page.getByRole('button',{name:'Start practice session'}).click();await expect(page.getByText('QUESTION 1 OF 2',{exact:true})).toBeVisible();
 const first=page.locator('.option').first();await first.click();await expect(first).toHaveAttribute('aria-pressed','true');
 await page.getByRole('button',{name:'Flag for review'}).click();await expect(page.getByRole('button',{name:'Flagged',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Save & leave session'}).click();await page.reload();
 await page.locator('nav').getByRole('button',{name:'Exam History',exact:true}).click();await page.getByRole('button',{name:'Resume',exact:true}).first().click();
 await expect(page.locator('.option[aria-pressed=true]')).toHaveCount(1);await expect(page.getByRole('button',{name:'Flagged',exact:true})).toBeVisible();
 await expect(page.locator('.timer')).toContainText(/\d\d:\d\d/);
 await page.getByRole('button',{name:'Next question'}).click();await expect(page.getByText('QUESTION 2 OF 2',{exact:true})).toBeVisible();
 await page.locator('.option').first().click();await expect(page.locator('.option[aria-pressed=true]')).toHaveCount(1);
 await page.getByRole('button',{name:'Submit examination'}).click();await page.getByRole('button',{name:'Submit & see results'}).click();
 await expect(page.getByRole('heading',{name:'Review your answers'})).toBeVisible();
 await page.locator('.review-question summary').first().click();await page.getByRole('button',{name:'Bookmark question'}).first().click();await expect(page.getByRole('button',{name:'Bookmarked',exact:true})).toBeVisible();
 await page.getByLabel('Personal revision note').first().fill('E2E note: review this concept');await page.getByRole('button',{name:'Save note'}).first().click();await expect(page.getByText('Saved to SQLite',{exact:true})).toBeVisible();
 await page.locator('nav').getByRole('button',{name:'Bookmarks',exact:true}).click();await expect(page.locator('.bank-question')).toHaveCount(1);
});
test('SPL challenge validates and persists feedback',async({page})=>{
 await page.goto('/');await page.locator('nav').getByRole('button',{name:'SPL Challenges',exact:true}).click();
 await page.getByRole('button',{name:/A clearer authentication timeline/}).click();await page.getByLabel('Your answer').fill('timechart');await page.getByRole('button',{name:'Check solution'}).click();await expect(page.getByRole('heading',{name:'Correct solution.'})).toBeVisible();
 await page.getByLabel('Close dialog').click();await expect(page.getByRole('button',{name:/A clearer authentication timeline/})).toContainText('Practice again');
});
test('mobile navigation and light theme are usable',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await page.getByRole('button',{name:'Open navigation'}).click();await page.locator('nav').getByRole('button',{name:'Settings',exact:true}).click();
 await page.getByRole('combobox',{name:'Color theme',exact:true}).selectOption('light');await page.getByRole('button',{name:'Save preferences'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.getByRole('combobox',{name:'Color theme',exact:true}).selectOption('dark');await page.getByRole('button',{name:'Save preferences'}).click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
});
