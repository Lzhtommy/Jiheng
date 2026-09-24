/* 玑衡 World · 状态层
 *
 * Phase 1 只做一件事：把原来平铺的存档
 *   {version:1, current, unlocked, scenes, scrolls, finished, report}
 * 升级为
 *   {version:2, world:{...}, scenario:{current, unlocked, scenes, scrolls, finished, report}}
 * 并用「非枚举访问器」把 scenario 的六个字段映射回顶层，让现有 Scenario 代码一行不改。
 *
 * 约定：
 * - 只依赖纯 JS，不碰 DOM —— 这样在测试的假 DOM 里也能跑。
 * - alias 必须 enumerable:false，否则 JSON.stringify(S) 会把六个字段重复序列化一遍。
 * - 存档 key 不变（页面侧仍是 jiheng-procurement-journey-v1，Flutter 侧仍是 jiheng.world.v1.<userId>）。
 */
(function (global) {
  "use strict";

  var VERSION = 2;

  /* Scenario 的六个字段：既是要迁移的字段，也是要挂 alias 的字段 */
  var SCENARIO_FIELDS = ["current", "unlocked", "scenes", "scrolls", "finished", "report"];

  /* World 层。Phase 1 只建立结构，不产生任何 UI。 */
  function freshWorldState() {
    return {
      layer: "world",
      player: { x: 0.5, y: 0.72 },
      currentRegion: null,
      visitedCompanies: [],
      unlockedBuildings: [],
      activeCompany: null,
      activeScenario: null
    };
  }

  /* Scenario 层。字段语义与原平铺结构完全一致，一个都没改。 */
  function freshScenarioState() {
    return { current: 0, unlocked: 0, scenes: {}, scrolls: [], finished: false, report: false };
  }

  /* 全新存档（已绑定 alias，可直接当 S 用） */
  function freshState() {
    return bindStateAliases({
      version: VERSION,
      world: freshWorldState(),
      scenario: freshScenarioState()
    });
  }

  /* v1 -> v2。非 v1/v2 一律返回 null，交给调用方回落到 freshState()。 */
  function migrateState(candidate) {
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return null;
    if (candidate.version === VERSION) return candidate;
    if (candidate.version !== 1) return null;
    var scenario = freshScenarioState();
    for (var i = 0; i < SCENARIO_FIELDS.length; i++) {
      var field = SCENARIO_FIELDS[i];
      if (candidate[field] !== undefined) scenario[field] = candidate[field];
    }
    return { version: VERSION, world: freshWorldState(), scenario: scenario };
  }

  /* 校验 v2 结构。sceneCount 由页面传入（= SCENES.length），本模块不依赖场景数据。 */
  function validStateV2(candidate, sceneCount) {
    if (!candidate || typeof candidate !== "object") return false;
    if (candidate.version !== VERSION) return false;
    if (!candidate.world || typeof candidate.world !== "object" || Array.isArray(candidate.world)) return false;
    var scenario = candidate.scenario;
    if (!scenario || typeof scenario !== "object" || Array.isArray(scenario)) return false;
    if (!Number.isInteger(scenario.current) || scenario.current < 0 || scenario.current >= sceneCount) return false;
    if (!Number.isInteger(scenario.unlocked) || scenario.unlocked < scenario.current || scenario.unlocked >= sceneCount) return false;
    if (!scenario.scenes || typeof scenario.scenes !== "object" || Array.isArray(scenario.scenes)) return false;
    if (!Array.isArray(scenario.scrolls)) return false;
    return true;
  }

  /* 兼容访问器：S.current <-> S.scenario.current …… 六个字段全通。
   * enumerable:false 保证 JSON.stringify(S) 只剩 {version, world, scenario}。 */
  function bindStateAliases(state) {
    if (!state || typeof state !== "object" || !state.scenario) return state;
    for (var i = 0; i < SCENARIO_FIELDS.length; i++) {
      bindOne(state, SCENARIO_FIELDS[i]);
    }
    return state;
  }

  function bindOne(state, field) {
    Object.defineProperty(state, field, {
      enumerable: false,
      configurable: true,
      get: function () { return state.scenario[field]; },
      set: function (value) { state.scenario[field] = value; }
    });
  }

  global.JHWorldState = {
    VERSION: VERSION,
    SCENARIO_FIELDS: SCENARIO_FIELDS.slice(),
    freshWorldState: freshWorldState,
    freshScenarioState: freshScenarioState,
    freshState: freshState,
    migrateState: migrateState,
    validStateV2: validStateV2,
    bindStateAliases: bindStateAliases
  };
})(typeof window !== "undefined" ? window : this);
