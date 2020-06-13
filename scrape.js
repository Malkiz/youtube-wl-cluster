const puppeteer = require('puppeteer');
const rimraf = require('rmfr');

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

(async () => {
  const browser = await puppeteer.launch(options);
  const page = await browser.newPage();
  await page.goto('https://google.com');
  await page.screenshot({path: 'example.png'});

  await browser.close();
})()
.catch( e => { console.error(e) })
.finally(() => rimraf(PATHS[process.platform].userDataDir));
