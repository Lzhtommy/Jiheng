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

function journey(savedState) {
  const app = { innerHTML: '', addEventListener() {}, insertAdjacentHTML() {} };
  const saved = new Map(savedState ? [['jiheng-procurement-journey-v1', savedState]] : []);
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
  return { run: code => vm.runInContext(code, context), get html() { return app.innerHTML; }, saved };
}

function enterCell(game) {
  game.run('S.current=2; S.unlocked=2; progress(currentScene()); render();');
}

test('the game uses scripted dialogue without calling a backend', () => {
  assert.doesNotMatch(html, /\bfetch\s*\(/);
  assert.doesNotMatch(html, /\/api\/procurement\/npc/);
  assert.match(html, /预设剧情对话/);
});

test('the cell scene keeps investigation points visually undisclosed until approached', () => {
  const game = journey();
  enterCell(game);
  assert.match(game.html, /class="cell-hotspot/);
  for (const id of ['warehouse', 'factory', 'market']) assert.match(game.html, new RegExp(`data-station="${id}"`));
  assert.doesNotMatch(game.html, /0 \/ 3|class="inspect-pin/);
  assert.match(game.html, /class="cell-hotspot/);
  assert.doesNotMatch(game.html, /data-act="travel"/);

  game.run('openCellInteraction(currentScene(),progress(currentScene()),"warehouse");');
  assert.match(game.html, /type="range"/);
  assert.equal(game.run('cellCount(progress(currentScene()))'), 0);
  game.run('updateCellTimeline(20);');
  assert.equal(game.run('completeCellTimeline(currentScene(),progress(currentScene()))'), false);
  game.run('updateCellTimeline(90);completeCellTimeline(currentScene(),progress(currentScene()));');
  assert.equal(game.run('cellCount(progress(currentScene()))'), 1);
  assert.match(game.html, /成本下降/);
  assert.match(game.run('S.scrolls.join(",")'), /cell-cost/);
});

test('market signals allow a retry; the factory module is dragged before its card is awarded', () => {
  const game = journey();
  enterCell(game);
  game.run('openCellInteraction(currentScene(),progress(currentScene()),"market");');
  assert.match(game.html, /新能源汽车销量/);
  assert.match(game.html, /data-act="cell-market-choice"/);
  game.run('answerCellMarket(currentScene(),progress(currentScene()),"noDemand");');
  assert.match(game.html, /是不是在朝同一个方向变化/);
  assert.equal(game.run('cellCount(progress(currentScene()))'), 0);
  game.run('answerCellMarket(currentScene(),progress(currentScene()),"demandPrice");');
  assert.equal(game.run('cellCount(progress(currentScene()))'), 1);

  game.run('openCellInteraction(currentScene(),progress(currentScene()),"factory");');
  assert.match(game.html, /data-drag-card="factory"/);
  assert.match(game.html, /data-drop-zone="factory"/);
  game.run('completeFactoryUpgrade(currentScene(),progress(currentScene()));');
  assert.match(game.html, /100 → 128/);
  assert.equal(game.run('cellCount(progress(currentScene()))'), 1);
  game.run('collectCellCard(currentScene(),progress(currentScene()),"factory");');
  assert.equal(game.run('cellCount(progress(currentScene()))'), 2);
  assert.match(game.run('S.scrolls.join(",")'), /cell-efficiency/);
});

test('three collected clues must be connected before the insight unlocks the next map node', () => {
  const game = journey();
  enterCell(game);
  game.run('updateCellTimeline(95);completeCellTimeline(currentScene(),progress(currentScene()));');
  game.run('answerCellMarket(currentScene(),progress(currentScene()),"demandPrice");');
  game.run('completeFactoryUpgrade(currentScene(),progress(currentScene()));collectCellCard(currentScene(),progress(currentScene()),"factory");');
  assert.equal(game.run('cellCount(progress(currentScene()))'), 3);
  assert.equal(game.run('submitCellAnalysis(currentScene(),progress(currentScene()))'), false);

  game.run('overlay="cell-analysis";render();');
  assert.match(game.html, /data-drop-zone="analysis"/);
  for (const id of ['warehouse', 'factory', 'market']) game.run(`connectCellCard(progress(currentScene()),"${id}");`);
  assert.equal(game.run('submitCellAnalysis(currentScene(),progress(currentScene()))'), true);
  assert.match(game.html, /价格下降，不等于需求消失/);
  assert.equal(game.run('completeCellArea(currentScene(),progress(currentScene()))'), true);
  assert.equal(game.run('S.scenes.cell.cellMission.completed'), true);
  assert.equal(game.run('S.unlocked'), 3);
  assert.equal(game.run('S.current'), 2);
  assert.match(game.html, /AREA COMPLETE/);

  game.run('overlay="map";render();');
  assert.match(game.html, /NEW · 亲自前往/);
  assert.match(game.html, /车企港/);
  assert.doesNotMatch(game.html, /data-index="3" disabled/);
  const restored = journey(game.saved.get('jiheng-procurement-journey-v1'));
  assert.equal(restored.run('S.current'), 2);
  assert.equal(restored.run('S.scenes.cell.cellMission.completed'), true);
  assert.equal(restored.run('S.unlocked'), 3);
});

test('dialogue or a premature purchase offer cannot bypass the unfinished investigation', () => {
  const game = journey();
  enterCell(game);
  assert.match(game.run('resolveTurn(currentScene(),progress(currentScene()),"下一站去哪","lead")'), /线索/);
  game.run('resolveTurn(currentScene(),progress(currentScene()),"看报价","claim");');
  game.run('resolveTurn(currentScene(),progress(currentScene()),"看交付","proof");');
  game.run('resolveTurn(currentScene(),progress(currentScene()),"提出条件","offer");');
  assert.equal(game.run('S.unlocked'), 2);
  assert.equal(game.run('S.scenes.cell.cellMission.completed'), false);
});

test('older cell saves keep their previously unlocked route', () => {
  const game = journey();
  game.run('S.current=2;S.unlocked=3;S.scenes.cell={seen:[],presented:[],inspected:[],history:[{speaker:"npc",text:"旧对话"}],deal:null,leadHeard:true};saveState();');
  const restored = journey(game.saved.get('jiheng-procurement-journey-v1'));
  assert.equal(restored.run('S.scenes.cell.cellMission.completed'), true);
  assert.equal(restored.run('S.unlocked'), 3);
});
