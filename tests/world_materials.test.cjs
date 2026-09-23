const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const html = fs.readFileSync(
  path.join(__dirname, '..', 'app', 'static', 'procurement-journey.html'),
  'utf8',
);
// The page loads static/world-state.js before its inline script, so the harness must too:
// the inline script builds S through window.JHWorldState.
const stateScript = fs.readFileSync(
  path.join(__dirname, '..', 'app', 'static', 'world-state.js'),
  'utf8',
);
const script = html.split('<script>')[1].split('</script>')[0];

function journey() {
  const app = {
    innerHTML: '',
    addEventListener() {},
    insertAdjacentHTML() {},
  };
  const saved = new Map();
  const document = {
    body: { classList: { add() {} }, setAttribute() {} },
    getElementById(id) { return id === 'app' ? app : null; },
    addEventListener() {},
  };
  const context = vm.createContext({
    document,
    // The page now registers a window-level listener for the World entry layer
    // ("jh-world:enter"), so the harness window carries the two event methods.
    window: { matchMedia: () => ({ matches: false }), addEventListener() {}, dispatchEvent() {} },
    location: { protocol: 'file:' },
    localStorage: {
      getItem: (key) => saved.get(key) ?? null,
      setItem: (key, value) => saved.set(key, value),
      removeItem: (key) => saved.delete(key),
    },
    setTimeout: () => 1,
    clearTimeout() {},
    confirm: () => true,
    console,
  });
  vm.runInContext(stateScript, context);
  vm.runInContext(script, context);
  return {
    run: (code) => vm.runInContext(code, context),
    get html() { return app.innerHTML; },
  };
}

function enterMaterials(game) {
  game.run('S.current=1; S.unlocked=1; progress(currentScene()); render();');
}

test('material negotiation rejects an unsupported quarterly claim', () => {
  const game = journey();
  enterMaterials(game);
  assert.equal(game.run('classify(currentScene(),"我想看库存台账")'), 'claim');
  assert.equal(game.run('classify(currentScene(),"排产窗口还能留多久")'), 'risk');
  assert.equal(game.run('classify(currentScene(),"上游长协怎么调价")'), 'proof');
  game.run('resolveTurn(currentScene(),progress(currentScene()),"下一站去哪","lead");');
  assert.equal(game.run('S.unlocked'), 1);
  const reply = game.run('resolveTurn(currentScene(),progress(currentScene()),"我要按季度核价","material-offer","audit")');
  assert.match(reply, /长协调价条款/);
  assert.equal(game.run('materialDeal()'), null);
  assert.equal(game.run('S.unlocked'), 1);
});

test('investigating all three workshop objects earns a rolling plan', () => {
  const game = journey();
  enterMaterials(game);
  for (const clue of ['stock', 'contract', 'schedule']) {
    const reply = game.run(`resolveTurn(currentScene(),progress(currentScene()),"查看现场","inspect","${clue}")`);
    assert.ok(reply.length > 10);
  }
  assert.deepEqual(
    JSON.parse(game.run('JSON.stringify(S.scrolls.filter(x=>x.startsWith("materials-")))')),
    ['materials-stock', 'materials-contract', 'materials-schedule'],
  );
  const reply = game.run('resolveTurn(currentScene(),progress(currentScene()),"给滚动采购计划","material-offer","rolling")');
  assert.match(reply, /条件预留/);
  assert.equal(game.run('materialRoute()'), 'rolling');
  assert.equal(game.run('S.unlocked'), 2);
  game.run('S.current=2; progress(currentScene()); render();');
  assert.match(game.html, /岑给了你分批排产窗口/);
  game.run('resolveTurn(currentScene(),progress(currentScene()),"看综合报价","claim");');
  game.run('resolveTurn(currentScene(),progress(currentScene()),"看交付规则","proof");');
  game.run('resolveTurn(currentScene(),progress(currentScene()),"提出采购条件","offer");');
  assert.match(game.run('S.scenes.cell.deal.terms'), /滚动交付/);
});

test('rush and audit choices change the next NPC and written consequences', () => {
  const rush = journey();
  enterMaterials(rush);
  rush.run('resolveTurn(currentScene(),progress(currentScene()),"先锁排产","material-offer","rush");');
  rush.run('S.current=2; progress(currentScene());');
  assert.match(rush.run('S.scenes.cell.history[0].text'), /交货日价格没有上限/);
  rush.run('S.current=1; render();');
  assert.match(rush.run('resolveTurn(currentScene(),progress(currentScene()),"改按季度","material-offer","audit")'), /不能悄悄改上游条款/);

  const audit = journey();
  enterMaterials(audit);
  audit.run('resolveTurn(currentScene(),progress(currentScene()),"看长协","inspect","contract");');
  audit.run('resolveTurn(currentScene(),progress(currentScene()),"按季度核价","material-offer","audit");');
  assert.equal(audit.run('materialRoute()'), 'audit');
  audit.run('S.current=2; progress(currentScene());');
  assert.match(audit.run('S.scenes.cell.history[0].text'), /没给你保排产位/);
  audit.run('resolveTurn(currentScene(),progress(currentScene()),"看综合报价","claim");');
  audit.run('resolveTurn(currentScene(),progress(currentScene()),"看交付规则","proof");');
  audit.run('resolveTurn(currentScene(),progress(currentScene()),"提出采购条件","offer");');
  assert.match(audit.run('S.scenes.cell.deal.terms'), /供料日期待工坊确认/);
});
