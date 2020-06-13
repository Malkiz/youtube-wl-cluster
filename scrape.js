const puppeteer = require('puppeteer');
const rimraf = require('rmfr');

// https://github.com/puppeteer/puppeteer/issues/1837#issuecomment-413725395
const USER_DATA_DIR = 'C:\\temp\\puppeteer_user_data';
const USER_DATA_DIR_WSL = '/mnt/c/temp/puppeteer_user_data';

// NOTE: for this to work, WSL needs to know the location of 'chrome.exe'.
// I did that by adding it to the PATH in ~/.bashrc like so:
// PATH="$PATH:/mnt/c/Program Files (x86)/Google/Chrome/Application"
// and then running `source ~/.bashrc`

const options = {
  headless: false,
  //args: ['--no-sandbox', '--disable-setuid-sandbox','--unhandled-rejections=strict'],
  executablePath: 'chrome.exe',
  userDataDir: USER_DATA_DIR
};

(async () => {
  const browser = await puppeteer.launch(options);
  const page = await browser.newPage();
  await page.goto('https://google.com');
  await page.screenshot({path: 'example.png'});

  await browser.close();
})()
.catch( e => { console.error(e) })
.finally(() => rimraf(USER_DATA_DIR_WSL));
