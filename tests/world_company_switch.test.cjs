const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const root = path.join(__dirname, '..');
const game = path.join(root, 'jiheng_ai_flutter', 'assets', 'game');
const html = fs.readFileSync(path.join(game, 'procurement-journey.html'), 'utf8');
const stateScript = fs.readFileSync(path.join(game, 'static', 'world-state.js'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0];

function makeGeneratedScene(companyId, index) {
  function topic(id) {
    return { id, label: id, prompt: `问${id}`, keys: ['关键词'], reply: '回应', repeat: '重复回应' };
  }
  return {
    id: `${companyId}-${index}`,
    place: `站点${index}`,
    region: `0${index} / 环节`,
    npc: '玑',
    role: '负责人',
    atmosphere: '环境描写',
    arrival: '抵达旁白',
    opening: '开场白',
    generic: '兜底回应',
    topics: [topic('claim'), topic('proof'), topic('risk')],
    offerPrompt: '提出条件',
    early: '还太早',
    offerStrong: '较优条件',
    offerWeak: '较弱条件',
    termsStrong: '优条件摘要',
    termsWeak: '弱条件摘要',
    risk: '情景模拟，需核对真实来源',
    lead: '前往下一站',
    cross: {},
  };
}

function journey() {
  const app = { innerHTML: '', addEventListener() {}, insertAdjacentHTML() {} };
  const saved = new Map();
  const document = {
    body: { classList: { add() {} }, setAttribute() {} },
    getElementById(id) { return id === 'app' ? app : null; },
    addEventListener() {},
  };
  const context = vm.createContext({
    document,
    window: { matchMedia: () => ({ matches: false }), addEventListener() {}, dispatchEvent() {} },
    location: { protocol: 'file:' },
    localStorage: {
      getItem: key => saved.get(key) ?? null,
      setItem: (key, value) => saved.set(key, value),
      removeItem: key => saved.delete(key),
    },
    setTimeout: () => 1,
    clearTimeout() {},
    confirm: () => true,
    console,
  });
  vm.runInContext(stateScript, context);
  vm.runInContext(script, context);
  return { run: code => vm.runInContext(code, context), saved };
}

test('switching to a generated company swaps SCENES and uses a namespaced save slot', () => {
  const g = journey();
  const scenes = [1, 2, 3, 4].map(i => makeGeneratedScene('co-test', i));
  g.run(`window.JHWorldData.scenarios["co-test"] = ${JSON.stringify(scenes)};`);

  g.run('activateCompany("co-test");');
  assert.equal(g.run('SCENES.length'), 4);
  assert.equal(g.run('currentScene().id'), 'co-test-1');
  assert.equal(g.run('activeCompanyId'), 'co-test');

  g.run('resolveTurn(currentScene(),progress(currentScene()),"随便问问","claim");saveState();');
  assert.ok(g.saved.has('jiheng-procurement-journey-v1:co-test'));
  assert.ok(!g.saved.get('jiheng-procurement-journey-v1:co-test').includes('"salt"'));

  g.run('activateCompany("catl");');
  assert.equal(g.run('SCENES.length'), 5);
  assert.equal(g.run('currentScene().id'), 'salt');
  assert.equal(g.run('activeCompanyId'), 'catl');
});

test('malformed generated scenes are rejected and fall back to the seed journey', () => {
  const g = journey();
  g.run('window.JHWorldData.scenarios["co-broken"] = [{id:"co-broken-1",place:"x",topics:[{id:"claim"}]}];');

  g.run('activateCompany("co-broken");');
  assert.equal(g.run('activeCompanyId'), 'catl');
  assert.equal(g.run('SCENES.length'), 5);
});

test('re-entering the same already-active company is a no-op that keeps progress', () => {
  const g = journey();
  g.run('resolveTurn(currentScene(),progress(currentScene()),"库存怎么样","claim");saveState();');
  const before = g.run('JSON.stringify(S.scenes.salt.seen)');

  g.run('activateCompany("catl");');
  assert.equal(g.run('JSON.stringify(S.scenes.salt.seen)'), before);
});
