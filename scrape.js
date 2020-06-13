const puppeteer = require('puppeteer');
const rimraf = require('rmfr');
const account = require('./account');

// https://github.com/puppeteer/puppeteer/issues/1837#issuecomment-522850970
const PATHS = {
    win32: {
        executablePath: 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
        userDataDir: 'C:\\temp\\puppeteer_user_data',
    },
    linux: {
        executablePath: '/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe',
        userDataDir: '/mnt/c/temp/puppeteer_user_data',
    },
}

const options = {
  headless: false,
  //args: ['--no-sandbox', '--disable-setuid-sandbox','--unhandled-rejections=strict'],
  executablePath: PATHS[process.platform].executablePath,
  userDataDir: PATHS.win32.userDataDir
};

const elementSelectors = {
  signIn: '#buttons > ytd-button-renderer > a',
  emailInput: '#identifierId',
  next: '#identifierNext',
};

const click = async (page, selector) => {
  await page.waitForSelector(selector, {visible: true});
  await page.click(selector);
};
const type = async (page, selector, text) => {
  await page.waitForSelector(selector, {visible: true});
  await page.type(selector, text);
};

(async () => {
  const browser = await puppeteer.launch(options);
  const page = await browser.newPage();
  await page.goto('https://youtube.com');
  
  await click(page, elementSelectors.signIn);
  await type(page, elementSelectors.emailInput, account.email);
  await click(page, elementSelectors.next);

  //await browser.close();
})()
.catch( e => { console.error(e) })
.finally(() => rimraf(PATHS[process.platform].userDataDir));
