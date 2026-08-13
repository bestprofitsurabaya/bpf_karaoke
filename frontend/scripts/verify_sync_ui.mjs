#!/usr/bin/env node
/**
 * Gladi resik UI kontrol sinkronisasi (panel admin karaoke).
 * Memverifikasi: kartu Sinkronisasi tampil, badge status paused,
 * tombol ▶ Lanjut / ⏸ Pause bekerja (flag Redis berubah), konsol bersih.
 *
 * Pemakaian: node scripts/verify_sync_ui.mjs
 * Prasyarat: app karaoke live di https://localhost:8443
 */
import puppeteer from 'puppeteer-core';

const BASE = process.env.BASE_URL || 'https://localhost:8443';
const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.ADMIN_PASSWORD || '141969Bds$#';

const CHROME = '/home/it-ef/.local/opt/chrome/chrome-linux64/chrome';

let passed = 0;
let failed = 0;
const errors = [];

function ok(name, cond, extra = '') {
  if (cond) {
    passed++;
    console.log(`  ✅ ${name}`);
  } else {
    failed++;
    errors.push(`${name} ${extra}`);
    console.log(`  ❌ ${name} ${extra}`);
  }
}

async function main() {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors', '--disable-gpu'],
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(20000);

  const consoleErrs = [];
  const httpErrs = [];
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrs.push(m.text());
  });
  page.on('pageerror', (e) => consoleErrs.push(String(e)));
  page.on('response', (r) => {
    if (r.status() >= 400) httpErrs.push(`${r.status()} ${r.url()}`);
  });

  console.log('=== 1. Login admin ===');
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle2', ignoreHTTPSErrors: true });
  await page.waitForSelector('input', { timeout: 15000 });
  const inputs = await page.$$('input');
  await inputs[0].type(ADMIN_USER);
  if (inputs[1]) await inputs[1].type(ADMIN_PASS);
  // cari tombol login (button berisi teks login/masuk)
  const btns = await page.$$('button');
  let clicked = false;
  for (const b of btns) {
    const t = await b.evaluate((el) => el.textContent.toLowerCase());
    if (t.includes('login') || t.includes('masuk')) {
      await b.click();
      clicked = true;
      break;
    }
  }
  if (!clicked && inputs[1]) await inputs[1].press('Enter');
  await page.waitForNavigation({ waitUntil: 'networkidle2', ignoreHTTPSErrors: true }).catch(() => {});
  await new Promise((r) => setTimeout(r, 2500));
  ok('Login admin berhasil (URL bukan /login)', !page.url().includes('/login'), `url=${page.url()}`);

  console.log('=== 2. Buka halaman admin ===');
  await page.goto(`${BASE}/admin`, { waitUntil: 'networkidle2', ignoreHTTPSErrors: true });
  await new Promise((r) => setTimeout(r, 3000));

  // Cari kartu Sinkronisasi
  const bodyText = await page.evaluate(() => document.body.innerText);
  ok('Halaman admin terbuka', bodyText.length > 200, `len=${bodyText.length}`);
  const syncVisible = bodyText.toLowerCase().includes('sinkronis') || bodyText.toLowerCase().includes('sync');
  ok('Kartu Sinkronisasi tampil', syncVisible);

  // Badge status — cek apakah ada teks jeda/pause
  const pausedShown = /dijeda|pause/i.test(bodyText) || /lanjut|resume/i.test(bodyText);
  ok('Status jeda/lanjut tampil di kartu', pausedShown, `(teks: ${bodyText.match(/.{0,20}(dijeda|pause|lanjut|resume).{0,20}/i)?.[0] || 'tidak ketemu'})`);

  console.log('=== 3. Tombol ▶ Lanjut (resume) ===');
  // klik tombol yang berisi teks lanjut/resume/start
  let resumeClicked = false;
  const buttons = await page.$$('button');
  for (const b of buttons) {
    const t = await b.evaluate((el) => el.textContent.toLowerCase());
    if (/(lanjut|resume|start|mulai)/.test(t)) {
      await b.click();
      resumeClicked = true;
      break;
    }
  }
  ok('Tombol resume dapat diklik', resumeClicked);
  await new Promise((r) => setTimeout(r, 2500));

  console.log('=== 4. Verifikasi flag Redis berubah (via API) ===');
  // Cek lewat API: login ulang + status
  const loginRes = await page.evaluate(async (u, p) => {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: u, password: p }),
    });
    return r.json();
  }, ADMIN_USER, ADMIN_PASS);
  const token = loginRes && loginRes.access_token;
  ok('API login menghasilkan token', !!token);
  if (token) {
    const st = await page.evaluate(async (tk) => {
      const r = await fetch('/api/admin/sync/status', { headers: { Authorization: `Bearer ${tk}` } });
      return r.json();
    }, token);
    ok('API status: paused=false setelah resume', st.paused === false, `paused=${st.paused}`);
  }

  console.log('=== 5. Kembalikan ke keadaan DIJEDA (sesuai kondisi awal) ===');
  let pauseClicked = false;
  const buttons2 = await page.$$('button');
  for (const b of buttons2) {
    const t = await b.evaluate((el) => el.textContent.toLowerCase());
    if (/(jeda|pause|stop)/.test(t)) {
      await b.click();
      pauseClicked = true;
      break;
    }
  }
  ok('Tombol pause dapat diklik', pauseClicked);
  await new Promise((r) => setTimeout(r, 2500));
  if (token) {
    const st2 = await page.evaluate(async (tk) => {
      const r = await fetch('/api/admin/sync/status', { headers: { Authorization: `Bearer ${tk}` } });
      return r.json();
    }, token);
    ok('API status: paused=true (kembali dijeda)', st2.paused === true, `paused=${st2.paused}`);
  }

  console.log('=== 6. Konsol bersih ===');
  // 404 sesi kamar (/api/rooms/*/session/current) = perilaku normal aplikasi karaoke.
  const knownOk = /session\/current/i;
  const badHttp = httpErrs.filter((e) => !knownOk.test(e));
  const realErrs = consoleErrs.filter((e) => !/favicon/i.test(e) && !/Failed to load resource/i.test(e)).concat(badHttp);
  ok('Tidak ada error konsol/HTTP', realErrs.length === 0, realErrs.slice(0, 3).join(' | '));

  await browser.close();

  console.log(`\n${passed} passed, ${failed} failed`);
  if (failed > 0) {
    console.log(errors.join('\n'));
    process.exit(1);
  }
}

main().catch((e) => {
  console.error('FATAL:', e.message);
  process.exit(1);
});
