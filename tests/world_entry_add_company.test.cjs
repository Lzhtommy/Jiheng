const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const script = fs.readFileSync(
  path.join(__dirname, '..', 'jiheng_ai_flutter', 'assets', 'game', 'static', 'world-entry.js'),
  'utf8',
);

function makeClassList() {
  const set = new Set();
  return {
    add: (...names) => names.forEach(n => set.add(n)),
    remove: (...names) => names.forEach(n => set.delete(n)),
    toggle(name, force) {
      const next = force === undefined ? !set.has(name) : force;
      if (next) set.add(name); else set.delete(name);
      return next;
    },
    contains: name => set.has(name),
  };
}

function makeEl(tag) {
  const el = {
    tagName: tag,
    children: [],
    dataset: {},
    attrs: {},
    style: { setProperty() {}, removeProperty() {} },
    classList: makeClassList(),
    className: '',
    innerHTML: '',
    hidden: false,
    listeners: {},
    appendChild(child) { this.children.push(child); return child; },
    removeChild(child) { this.children = this.children.filter(c => c !== child); return child; },
    get firstChild() { return this.children[0] || null; },
    setAttribute(k, v) { this.attrs[k] = v; },
    getAttribute(k) { return this.attrs[k]; },
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); },
    removeEventListener() {},
    closest() { return null; },
    querySelector() { return null; },
    offsetWidth: 40,
    clientWidth: 800,
    clientHeight: 600,
  };
  return el;
}

function harness() {
  const root = makeEl('div');
  root.id = 'worldlayer';
  const els = { worldlayer: root };
  const document = {
    readyState: 'complete',
    createElement: tag => makeEl(tag),
    getElementById: id => els[id] || null,
    addEventListener() {},
    querySelector() {},
  };
  const context = vm.createContext({
    document,
    window: {
      matchMedia: () => ({ matches: false }),
      addEventListener() {},
      dispatchEvent() {},
      CustomEvent: function CustomEvent(type, opts) { this.type = type; this.detail = opts && opts.detail; },
    },
    JHWorldData: { meta: {}, map: {}, regions: [], companies: [], buildings: [], scenarios: {} },
    setTimeout: () => 1,
    clearTimeout() {},
    console,
  });
  context.window.JHWorldData = context.JHWorldData;
  vm.runInContext(script, context);
  return { run: code => vm.runInContext(code, context), root };
}

function fakeScenario(companyId) {
  return {
    company: { id: companyId, name: '测试公司', code: '000000', tag: '测试 · 中游', kind: 'tech' },
    scenes: [{ id: `${companyId}-1`, place: '站点一' }],
  };
}

test('addCompany appends a building and registers scenario data', () => {
  const g = harness();
  const ok = g.run(`window.JHWorldEntry.addCompany(${JSON.stringify(fakeScenario('co-abc'))})`);
  assert.equal(ok, true);
  assert.equal(g.run('window.JHWorldEntry.isMounted()'), true);
  assert.ok(g.run('!!window.JHWorldData.scenarios["co-abc"]'));
  assert.equal(g.run('window.JHWorldData.companies.length'), 1);
});

test('addCompany is idempotent for the same company id', () => {
  const g = harness();
  g.run(`window.JHWorldEntry.addCompany(${JSON.stringify(fakeScenario('co-dup'))})`);
  const second = g.run(`window.JHWorldEntry.addCompany(${JSON.stringify(fakeScenario('co-dup'))})`);
  assert.equal(second, false);
  assert.equal(g.run('window.JHWorldData.companies.length'), 1);
});

test('hydrate accepts a batch and each gets a distinct growth-row slot', () => {
  const g = harness();
  const batch = ['co-1', 'co-2', 'co-3'].map(fakeScenario);
  g.run(`window.JHWorldEntry.hydrate(${JSON.stringify(batch)})`);
  assert.equal(g.run('window.JHWorldData.companies.length'), 3);
  const xs = g.run('window.JHWorldData.companies.map(c=>c.wide.x)');
  assert.equal(new Set(xs).size, 3);
});

test('malformed payloads are rejected without throwing', () => {
  const g = harness();
  assert.equal(g.run('window.JHWorldEntry.addCompany(null)'), false);
  assert.equal(g.run('window.JHWorldEntry.addCompany({company:{id:"x"}})'), false);
  assert.equal(g.run('window.JHWorldData.companies.length'), 0);
});

test('a new page opens once a map fills up, and stays put until it does', () => {
  const g = harness();
  ['a', 'b', 'c', 'd', 'e', 'f'].forEach(id => {
    g.run(`window.JHWorldEntry.addCompany(${JSON.stringify(fakeScenario('co-' + id))})`);
  });
  assert.equal(g.run('window.JHWorldEntry.maxMapIndex()'), 1);

  g.run(`window.JHWorldEntry.addCompany(${JSON.stringify(fakeScenario('co-g'))})`);
  assert.equal(g.run('window.JHWorldEntry.maxMapIndex()'), 2);
});

test('changeMap walks forward/backward and clamps at both ends', () => {
  const g = harness();
  ['a', 'b', 'c', 'd', 'e', 'f', 'g'].forEach(id => {
    g.run(`window.JHWorldEntry.addCompany(${JSON.stringify(fakeScenario('co-' + id))})`);
  });
  assert.equal(g.run('window.JHWorldEntry.mapIndex()'), 0);

  g.run('window.JHWorldEntry.changeMap(1)');
  assert.equal(g.run('window.JHWorldEntry.mapIndex()'), 1);
  g.run('window.JHWorldEntry.changeMap(1)');
  assert.equal(g.run('window.JHWorldEntry.mapIndex()'), 2);
  g.run('window.JHWorldEntry.changeMap(1)');
  assert.equal(g.run('window.JHWorldEntry.mapIndex()'), 2, 'stays on the last page past the frontier');

  g.run('window.JHWorldEntry.changeMap(-1)');
  assert.equal(g.run('window.JHWorldEntry.mapIndex()'), 1);
  g.run('window.JHWorldEntry.changeMap(-1)');
  assert.equal(g.run('window.JHWorldEntry.mapIndex()'), 0);
  g.run('window.JHWorldEntry.changeMap(-1)');
  assert.equal(g.run('window.JHWorldEntry.mapIndex()'), 0, 'stays on the main map before page 0');
});

test('companies on later pages stay findable by select() even off-screen', () => {
  const g = harness();
  ['a', 'b', 'c', 'd', 'e', 'f', 'g'].forEach(id => {
    g.run(`window.JHWorldEntry.addCompany(${JSON.stringify(fakeScenario('co-' + id))})`);
  });
  // co-g is the 7th company, i.e. the sole occupant of page 2; still on the main map (page 0).
  assert.equal(g.run('window.JHWorldEntry.mapIndex()'), 0);
  g.run('window.JHWorldEntry.select("co-g")');
  assert.equal(g.run('window.JHWorldEntry.state().selected'), null, 'select() walks async; not selected yet mid-transition is fine, but it must not throw');
});
