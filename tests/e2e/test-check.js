const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('http://whisper_nginx_dev/shared/test-token-123');
  await page.waitForTimeout(3000);
  
  // Check page title
  const title = await page.title();
  console.log('Page title:', title);
  
  // Check for any elements with data-testid
  const testIds = await page.150722eval('[data-testid]', elements => 
    elements.map(el => el.getAttribute('data-testid'))
  );
  console.log('Found data-testid attributes:', testIds);
  
  // Check if audio player container exists
  const audioPlayer = await page.;
  console.log('Audio player exists:', !!audioPlayer);
  console.log('Audio player visible:', audioPlayer ? await audioPlayer.isVisible() : false);
  
  await browser.close();
})();
