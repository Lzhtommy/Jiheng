/* 手动运行：node tests/world_cinematic.browser.cjs
 * 使用已安装的 Chrome + 原生 CDP，不需要 Playwright 或额外依赖。 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { pathToFileURL } = require('node:url');

const chrome = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].find(fs.existsSync);
if (!chrome) throw new Error('Chrome/Edge not installed');

const outputDir = fs.mkdtempSync(path.join(os.tmpdir(), 'jiheng-cinematic-'));
const gameUrl = pathToFileURL(path.join(__dirname, '..', 'jiheng_ai_flutter', 'assets', 'game', 'procurement-journey.html')).href;
const browser = spawn(chrome, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--allow-file-access-from-files', '--remote-debugging-port=0',
  '--user-data-dir=' + path.join(outputDir, 'profile'), gameUrl,
], { stdio: 'ignore', windowsHide: true });

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(callback, timeout = 8000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    const value = await callback();
    if (value) return value;
    await sleep(100);
  }
  throw new Error('Timed out waiting for browser state');
}

async function main() {
  const activePort = path.join(outputDir, 'profile', 'DevToolsActivePort');
  const port = await until(() => fs.existsSync(activePort) ? Number(fs.readFileSync(activePort, 'utf8').split(/\r?\n/)[0]) : 0);
  const tab = await until(async () => {
    const tabs = await fetch('http://127.0.0.1:' + port + '/json/list').then(response => response.json());
    return tabs.find(item => item.type === 'page' && item.url.startsWith('file:'));
  });
  const socket = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
  let id = 0;
  const pending = new Map();
  const errors = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
    if (!message.id) return;
    const target = pending.get(message.id);
    if (!target) return;
    pending.delete(message.id);
    if (message.error) target.reject(new Error(message.error.message));
    else target.resolve(message.result);
  });
  function command(method, params = {}) {
    return new Promise((resolve, reject) => {
      const requestId = ++id;
      const timeout = setTimeout(() => { pending.delete(requestId); reject(new Error('CDP timeout: ' + method)); }, 12000);
      pending.set(requestId, {
        resolve: value => { clearTimeout(timeout); resolve(value); },
        reject: error => { clearTimeout(timeout); reject(error); },
      });
      socket.send(JSON.stringify({ id: requestId, method, params }));
    });
  }
  async function evaluate(expression) {
    const result = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text + ': ' + expression);
    return result.result.value;
  }
  async function waitFor(expression, timeout) {
    return until(() => evaluate(expression), timeout);
  }
  async function screenshot(name) {
    const result = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    const imagePath = path.join(outputDir, name + '.png');
    fs.writeFileSync(imagePath, Buffer.from(result.data, 'base64'));
    console.log(name + ': ' + imagePath);
  }
  async function drag(source, target) {
    const points = await evaluate(`(() => { const a=document.querySelector(${JSON.stringify(source)}).getBoundingClientRect(); const b=document.querySelector(${JSON.stringify(target)}).getBoundingClientRect(); return {ax:a.x+a.width/2,ay:a.y+a.height/2,bx:b.x+b.width/2,by:b.y+b.height/2}; })()`);
    await command('Input.dispatchMouseEvent', { type: 'mouseMoved', x: points.ax, y: points.ay });
    await command('Input.dispatchMouseEvent', { type: 'mousePressed', x: points.ax, y: points.ay, button: 'left', clickCount: 1 });
    await command('Input.dispatchMouseEvent', { type: 'mouseMoved', x: points.bx, y: points.by, button: 'left', buttons: 1 });
    await command('Input.dispatchMouseEvent', { type: 'mouseReleased', x: points.bx, y: points.by, button: 'left', clickCount: 1 });
  }

  await command('Page.enable');
  await command('Runtime.enable');
  await command('Emulation.setDeviceMetricsOverride', { width: 1440, height: 850, deviceScaleFactor: 1, mobile: false });
  await waitFor('!!window.JHWorldEntry && !!window.JHWorldFX && document.body.dataset.layer === "world"');
  await screenshot('01-world');

  // 已有电芯城存档：走 World 的真实公司入口，不改游戏内解锁顺序。
  await evaluate('S.current=2;S.unlocked=2;progress(currentScene());saveState();render();JHWorldEntry.select("catl");');
  await waitFor('!!document.querySelector("[data-enter]")');
  await evaluate('document.querySelector("[data-enter]").click()');
  await waitFor('!!document.querySelector(".cg-world-enter")');
  await sleep(1000);
  await screenshot('02-enter');
  await waitFor('document.body.dataset.layer === "scenario"', 4000);
  await sleep(1300);
  assert.equal(await evaluate('(() => [...document.querySelectorAll(".cell-hotspot")].every(node => { const r=node.getBoundingClientRect(),d=document.querySelector(".dialogue").getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2; const hit=document.elementFromPoint(x,y); return r.bottom<d.top && hit && hit.closest(".cell-hotspot")===node; }))()'), true, 'each desktop hotspot should be visible and clickable above the dialogue');
  await screenshot('03-cell');

  await evaluate('document.querySelector("[data-station=warehouse]").click()');
  await waitFor('!!document.querySelector("[data-act=cell-timeline]")');
  await evaluate('const range=document.querySelector("[data-act=cell-timeline]");range.value=90;range.dispatchEvent(new Event("input",{bubbles:true}));document.querySelector("[data-act=cell-timeline-complete]").click();');
  await waitFor('!!document.querySelector(".cg-result[data-station=warehouse]")');
  await sleep(850);
  await screenshot('04-warehouse');
  await waitFor('!!document.querySelector(".cell-record")', 4000);
  await evaluate('document.querySelector("[data-act=close]").click()');

  await evaluate('document.querySelector("[data-station=factory]").click()');
  await waitFor('!!document.querySelector("[data-drag-card=factory]")');
  await drag('[data-drag-card=factory]', '[data-drop-zone=factory]');
  await waitFor('!!document.querySelector("[data-act=collect-cell-card]")');
  await evaluate('document.querySelector("[data-act=collect-cell-card]").click()');
  await waitFor('!!document.querySelector(".cg-result[data-station=factory]")');
  await sleep(850);
  await screenshot('05-factory');
  await waitFor('!!document.querySelector(".cell-record")', 4000);
  await evaluate('document.querySelector("[data-act=close]").click()');

  await evaluate('document.querySelector("[data-station=market]").click()');
  await waitFor('!!document.querySelector("[data-choice=demandPrice]")');
  await evaluate('document.querySelector("[data-choice=demandPrice]").click()');
  await waitFor('!!document.querySelector(".cg-result[data-station=market]")');
  await sleep(1150);
  await screenshot('06-market');
  await waitFor('!!document.querySelector(".cell-record")', 4000);
  await evaluate('document.querySelector("[data-act=close]").click()');

  await evaluate('document.querySelector("[data-act=open-cell-analysis]").click()');
  await waitFor('!!document.querySelector("[data-drop-zone=analysis]")');
  for (const station of ['warehouse', 'factory', 'market']) {
    await drag(`[data-drag-card="analysis:${station}"]`, '[data-drop-zone=analysis]');
    await waitFor(`document.querySelectorAll(".analysis-slot.connected").length === ${['warehouse', 'factory', 'market'].indexOf(station) + 1}`);
  }
  await evaluate('document.querySelector("[data-act=submit-cell-analysis]").click()');
  await waitFor('!!document.querySelector(".cg-insight")');
  await sleep(2150);
  await screenshot('07-insight');
  await waitFor('!!document.querySelector(".cg-unlock")', 5000);
  await sleep(1700);
  await screenshot('08-unlock');
  await waitFor('!!document.querySelector(".cg-route-ready") && !document.querySelector(".cg-screen")', 5000);
  assert.equal(await evaluate('S.unlocked'), 3);
  assert.equal(await evaluate('S.current'), 2);
  assert.equal(await evaluate('S.scenes.cell.cellMission.completed'), true);
  await screenshot('09-done');

  await command('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await sleep(300);
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), true);
  await screenshot('10-mobile-done');

  // 在手机视口复核高潮画面和 SKIP；不修改真实玩法分支。
  await evaluate('const p=progress(currentScene());p.cellMission.completed=false;p.cellMission.analysisCompleted=false;p.cellMission.connected=["warehouse","factory","market"];S.unlocked=2;render();submitCellAnalysis(currentScene(),p);');
  await waitFor('!!document.querySelector(".cg-insight")');
  await sleep(2650);
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), true);
  await screenshot('11-mobile-insight');
  await evaluate('document.querySelector(".cg-insight [data-cg-skip]").click()');
  await waitFor('!!document.querySelector(".cg-unlock")');
  await sleep(1750);
  await screenshot('12-mobile-unlock');
  await evaluate('document.querySelector(".cg-unlock [data-cg-skip]").click()');
  await waitFor('!!document.querySelector(".cg-route-ready") && !JHWorldFX.isPlaying()');
  assert.equal(await evaluate('S.unlocked'), 3);
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), true);

  await evaluate('window.__mobileResultDone=false;JHWorldFX.playInvestigation(document.getElementById("world"),"factory",()=>{window.__mobileResultDone=true;});');
  await waitFor('!!document.querySelector(".cg-result[data-station=factory]")');
  await sleep(1200);
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth + 2'), true);
  await screenshot('13-mobile-factory');
  await waitFor('window.__mobileResultDone === true && !JHWorldFX.isPlaying()', 3000);

  await command('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  await evaluate('window.__fxReducedDone=false;JHWorldFX.playInsight(document.getElementById("world"),()=>{window.__fxReducedDone=true;});');
  await waitFor('window.__fxReducedDone === true && !JHWorldFX.isPlaying()', 1000);
  assert.deepEqual(errors, []);
  socket.close();
  console.log('Browser flow passed. Screenshots: ' + outputDir);
}

main().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => browser.kill());
