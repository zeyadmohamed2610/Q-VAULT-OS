const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const chrome = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const outDir = path.resolve('.logs/cinematic-audit');
const profileDir = path.join(outDir, 'chrome-profile');
const port = 10400 + Math.floor(Math.random() * 1000);
const url = process.argv[2] || 'http://127.0.0.1:3000';

const shots = [
  ['00_void_establish', 7000],
  ['00_void_mid', 10000],
  ['01_threat_establish', 14500],
  ['02_hardware_establish', 21500],
  ['03_trust_establish', 30000],
  ['04_protocol_establish', 37000],
  ['05_zk_establish', 43000],
  ['06_provision_establish', 50000],
  ['07_os_establish', 58500],
  ['08_governance_establish', 67000],
  ['09_threat_matrix_establish', 74500],
  ['10_lifecycle_establish', 82500],
  ['11_roadmap_establish', 90000],
  ['12_seal_establish', 98000],
  ['12_credits', 104000],
];

fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(profileDir, { recursive: true });

const browser = spawn(chrome, [
  '--headless=new',
  '--disable-gpu',
  '--hide-scrollbars',
  '--no-first-run',
  '--disable-extensions',
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profileDir}`,
  '--window-size=1440,900',
  'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] });

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getJson(endpoint) {
  const response = await fetch(`http://127.0.0.1:${port}${endpoint}`);
  if (!response.ok) throw new Error(`CDP ${endpoint} failed: ${response.status}`);
  return response.json();
}

async function waitForCdp() {
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    try {
      await getJson('/json/version');
      return;
    } catch {
      await delay(100);
    }
  }
  throw new Error('Chrome CDP did not become ready');
}

async function main() {
  await waitForCdp();
  const targets = await getJson('/json/list');
  const target = targets.find((item) => item.type === 'page');
  if (!target) throw new Error('No page target');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', reject, { once: true });
  });

  let id = 0;
  const pending = new Map();
  const events = [];

  ws.addEventListener('message', (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
      return;
    }
    if (msg.method === 'Runtime.consoleAPICalled') {
      events.push(`[console:${msg.params.type}] ${msg.params.args.map((arg) => arg.value ?? arg.description).join(' ')}`);
    }
    if (msg.method === 'Runtime.exceptionThrown') {
      events.push(`[exception] ${msg.params.exceptionDetails.text}`);
    }
    if (msg.method === 'Log.entryAdded' && msg.params.entry.level !== 'verbose') {
      events.push(`[log:${msg.params.entry.level}] ${msg.params.entry.text}`);
    }
  });

  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const msgId = ++id;
    pending.set(msgId, { resolve, reject });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });

  await send('Runtime.enable');
  await send('Log.enable');
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await send('Page.navigate', { url });

  const startedAt = Date.now();
  const report = [];

  for (const [name, atMs] of shots) {
    const remaining = atMs - (Date.now() - startedAt);
    if (remaining > 0) await delay(remaining);

    const state = await send('Runtime.evaluate', {
      returnByValue: true,
      expression: `(() => ({
        text: document.body.innerText,
        canvas: !!document.querySelector('canvas')
      }))()`,
    });

    const screenshot = await send('Page.captureScreenshot', { format: 'png' });
    const file = path.join(outDir, `${name}.png`);
    fs.writeFileSync(file, Buffer.from(screenshot.data, 'base64'));
    const value = state.result.value;
    report.push({ name, atMs, text: value.text, canvas: value.canvas, file });
    console.log(`${name} ${atMs}ms`);
  }

  fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify({ events, report }, null, 2));
  console.log(JSON.stringify({ events, report }, null, 2));
  ws.close();
}

main()
  .catch((err) => {
    console.error(err);
    process.exitCode = 1;
  })
  .finally(() => {
    browser.kill();
  });
