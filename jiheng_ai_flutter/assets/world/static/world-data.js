/* 玑衡 World · 世界数据
 *
 * Phase 1 只建立最小 Schema，不填任何真实内容 —— 地图、区域、公司、建筑
 * 都在 Phase 2 才写入。现在挂上去只是为了让 Phase 2 有一个稳定的落点。
 */
window.JHWorldData = {
  meta: {
    schema_version: 1,
    phase: "phase-1",
    note: "仅结构定义，内容留待 Phase 2 填充"
  },
  map: {
    width: 1,
    height: 1,
    background: null,
    spawn: { x: 0.5, y: 0.72 }
  },
  regions: [],
  companies: [],
  buildings: [],
  scenarios: []
};
