/* 玑衡 World · 世界数据
 *
 * Phase 2：玑衡 Agent 生成公司关卡后的运行时落点。
 * - companies：追加公司的元信息（id/name/code/tag/kind + 地图落位），world-entry.js 读写。
 * - scenarios：以 companyId 为 key 的关卡数组（procurement-journey.html 的 SCENES 结构），
 *   由 Flutter 在生成成功 / App 启动时通过 window.JHWorldEntry.addCompany / .hydrate 写入。
 * 手写的宁德时代旅程不经过这里 —— 它是 procurement-journey.html 里的 SEED_SCENES 常量。
 */
window.JHWorldData = {
  meta: {
    schema_version: 2,
    phase: "phase-2",
    note: "companies/scenarios 由玑衡 Agent 生成的公司在运行时写入"
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
  scenarios: {}
};
