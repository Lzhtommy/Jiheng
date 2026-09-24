/* 玑衡 World · 像素风探索首页
 *
 * 职责：只负责 #worldlayer 里的那个像素产业城市 —— 场景、像素小人、点击移动、
 * 公司建筑高亮、公司信息卡。它不认识 SCENES / NPC / 存档，也不碰 #app。
 *
 * 与产业链探索页面的唯一联系是两条 window 事件（单向解耦，谁都不引用谁）：
 *   本模块 -> 页面：  window 派发 "jh-world:enter"（玩家点了「进入探索」）
 *   页面 -> 本模块：  window 派发 "jh-world:back" （玩家点了「返回 World」）
 * 层与层的显隐由 body[data-layer] 决定（world.css），本模块不参与。
 *
 * 状态刻意保持极简（刷新后重新出生是可接受的）：
 *   state = { x, y, selected }   —— x / y 都是 0~100 的百分比，不写死 px。
 * 画家算法：z-index = round(y)，y 越大越靠前，人物用 round(y)+1。所以只要给对 y，
 * 遮挡关系就自然正确，不需要额外排序。
 */
(function (global) {
  "use strict";

  var ENTER_EVENT = "jh-world:enter";
  var BACK_EVENT = "jh-world:back";
  var NARROW_QUERY = "(max-width:760px)";

  /* 5 家公司：以「建筑」存在，不是 logo 卡片。
     wide / narrow 是两套归一化坐标（x / y / w / h 都是百分比），窄屏整体换一套。
     分远近两排：远景排更小更靠上，近景排更大更靠下 —— 靠尺寸差撑出纵深。 */
  var COMPANIES = [
    {
      id: "catl", code: "300750", name: "宁德时代", tag: "动力电池 · 中游", kind: "battery",
      enter: true, label: "CATL",
      wide: { x: 26, y: 86, w: 18, h: 21 }, narrow: { x: 30, y: 84, w: 40, h: 17 }
    },
    {
      id: "naura", code: "002371", name: "北方华创", tag: "半导体设备 · 上游", kind: "equip",
      label: "NAURA",
      wide: { x: 61, y: 90, w: 13, h: 17 }, narrow: { x: 74, y: 88, w: 28, h: 13 }
    },
    {
      id: "smic", code: "688981", name: "中芯国际", tag: "晶圆制造 · 上游", kind: "fab",
      label: "SMIC",
      wide: { x: 15, y: 62, w: 12, h: 16 }, narrow: { x: 22, y: 60, w: 26, h: 12 }
    },
    {
      id: "byd", code: "002594", name: "比亚迪", tag: "整车 · 下游", kind: "auto",
      label: "BYD",
      wide: { x: 37, y: 60, w: 13, h: 13 }, narrow: { x: 55, y: 58, w: 26, h: 11 }
    },
    {
      id: "xiaomi", code: "01810", name: "小米", tag: "消费电子 · 终端", kind: "tech",
      label: "XIAOMI",
      wide: { x: 88, y: 62, w: 11, h: 17 }, narrow: { x: 84, y: 60, w: 22, h: 14 }
    }
  ];

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* 玑衡 Agent 生成的公司越来越多，一张地图放不下：每张「新增地图」最多放 MAP_CAPACITY 家，
     放满一页就自动开一页新的，玩家通过地图两侧的传送点前后翻页。
     extraCompanies 是所有生成公司的扁平列表（不含手写的 5 家)，按生成顺序分页；
     currentMapIndex = 0 是手写的主城地图，1/2/3... 是纯生成公司的「新区」地图。 */
  var MAP_CAPACITY = 6;
  var extraCompanies = [];
  var currentMapIndex = 0;

  /* 追加公司的单排落位算法：一页最多 MAP_CAPACITY 家，横向摆成一排，不会互相遮挡，
     也不会撞到任何一张地图上的道路 / 装饰物坐标。 */
  function growthSlot(indexInPage, narrowMode) {
    var x = 8 + indexInPage * (84 / (MAP_CAPACITY - 1 || 1));
    return narrowMode ? { x: x, y: 40, w: 13, h: 11 } : { x: x, y: 36, w: 11, h: 14 };
  }

  function totalExtraPages() { return Math.ceil(extraCompanies.length / MAP_CAPACITY); }
  /* 目前地图总数（除主城外）= 已经放满/正在使用的「新区」页数；0 表示还没有任何生成公司。 */
  function maxMapIndex() { return totalExtraPages(); }

  function buildingsForMap(mapIndex) {
    if (mapIndex <= 0) return COMPANIES;
    var start = (mapIndex - 1) * MAP_CAPACITY;
    return extraCompanies.slice(start, start + MAP_CAPACITY);
  }

  /* 地图道路两侧的传送点：走过去就翻到上一页 / 下一页「新区」地图。
     只有 currentMapIndex>0 时才有「上一张」，只有还有下一页内容时才有「下一张」。 */
  var PORTAL_LEFT = {
    id: "portal-left", label: "上一张地图",
    wide: { x: 4, y: 84, w: 7, h: 16 }, narrow: { x: 6, y: 82, w: 15, h: 13 }
  };
  var PORTAL_RIGHT = {
    id: "portal-right", label: "下一张地图",
    wide: { x: 96, y: 84, w: 7, h: 16 }, narrow: { x: 94, y: 82, w: 15, h: 13 }
  };

  var SKIN = {
    battery: { body: "#1b3b4a", roof: "#2a5b68", win: "rgba(243,200,132,.95)", alpha: ".85" },
    auto: { body: "#20363f", roof: "#2e6b73", win: "rgba(157,216,208,.9)", alpha: ".8" },
    fab: { body: "#152738", roof: "#2b5872", win: "rgba(219,246,255,.95)", alpha: ".9" },
    equip: { body: "#22333b", roof: "#365a63", win: "rgba(243,200,132,.85)", alpha: ".8" },
    tech: { body: "#122332", roof: "#24506d", win: "rgba(243,200,132,.98)", alpha: ".9" }
  };

  /* 出生点：必须落在「道路带 + 没有任何建筑遮挡」的空隙里，否则会被画家算法挡在楼后。
     wide 在 CATL/NAURA 之间的空档，narrow 在 CATL 与 NAURA 之间的路面上。 */
  var SPAWN = { wide: { x: 47, y: 79 }, narrow: { x: 55, y: 78 } };
  var WALK_MIN_Y = 66;
  var WALK_MAX_Y = 96;

  /* 「加号基座」：不指向任何一家公司，而是让玩家自己输入想了解的公司。
     x / y 必须落在建筑矩形之外的空档里（wide 在 CATL 与 NAURA 之间，narrow 在两者之间的路面）。 */
  var PEDESTAL = {
    id: "custom",
    label: "添加公司",
    wide: { x: 44, y: 88, w: 5.5, h: 9 },
    narrow: { x: 54, y: 88, w: 11, h: 7 }
  };
  var stage = null, player = null, buildings = null, card = null, pedestal = null, mounted = false;
  var portalLeftNode = null, portalRightNode = null, mapHud = null;
  var narrow = false;
  var nodes = {};

  var state = { x: SPAWN.wide.x, y: SPAWN.wide.y, selected: null, requested: null };
  var arrivalTimer = null, arrivalHandler = null;

  /* ---------- 小工具 ---------- */

  function makeRng(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function el(tag, cls) { var n = document.createElement(tag); if (cls) n.className = cls; return n; }
  function findCompany(id) {
    for (var i = 0; i < COMPANIES.length; i++) if (COMPANIES[i].id === id) return COMPANIES[i];
    for (var j = 0; j < extraCompanies.length; j++) if (extraCompanies[j].id === id) return extraCompanies[j];
    return null;
  }
  function layoutOf(c) { return narrow ? c.narrow : c.wide; }
  function isNarrow() { return !!(global.matchMedia && global.matchMedia(NARROW_QUERY).matches); }

  /* 把一个元素按 (x%, y%) 放好，y 是「底边距顶部」的百分比 */
  function placeAt(node, x, y, z) {
    node.style.left = x + "%";
    node.style.bottom = (100 - y) + "%";
    node.style.zIndex = String(z === undefined ? Math.round(y) : z);
  }

  /* ---------- 场景搭建 ---------- */

  function buildSky(sky) {
    var stars = el("div", "we-stars");
    var rng = makeRng(20260923);
    var shadows = [];
    for (var i = 0; i < 58; i++) {
      shadows.push(Math.round(rng() * 100) + "vw " + Math.round(rng() * 46) + "vh 0 0 " + (rng() > 0.84 ? "#ffe9c8" : "#dff0ff"));
    }
    stars.style.boxShadow = shadows.join(",");
    sky.appendChild(stars);

    sky.appendChild(el("div", "we-sun"));

    var clouds = [
      { left: "10%", bottom: "44%", width: "64px" },
      { left: "42%", bottom: "50%", width: "48px" },
      { left: "86%", bottom: "46%", width: "58px" }
    ];
    for (var c = 0; c < clouds.length; c++) {
      var cloud = el("div", "we-cloud");
      cloud.style.left = clouds[c].left;
      cloud.style.bottom = clouds[c].bottom;
      cloud.style.width = clouds[c].width;
      sky.appendChild(cloud);
    }
  }

  function buildSkyline(layer, seed, minH, maxH) {
    var rng = makeRng(seed);
    var x = -1.5;
    while (x < 101) {
      var w = 1.8 + rng() * 3.4;
      var tower = el("div", "we-tower");
      tower.style.left = x.toFixed(2) + "%";
      tower.style.width = w.toFixed(2) + "%";
      tower.style.height = (minH + rng() * (maxH - minH)).toFixed(2) + "%";
      if (rng() > 0.86) {
        var blink = el("div", "we-blink");
        blink.style.left = "50%";
        blink.style.top = "6px";
        tower.appendChild(blink);
      }
      layer.appendChild(tower);
      x += w + 0.5 + rng() * 1.5;
    }
  }

  function buildChimneys(layer, spec) {
    for (var i = 0; i < spec.length; i++) {
      var chimney = el("div", "we-chimney");
      chimney.style.left = spec[i].left + "%";
      chimney.style.height = spec[i].height + "%";
      var puffs = 2 + (i % 2);
      for (var p = 0; p < puffs; p++) {
        var puff = el("div", "we-puff");
        puff.style.animationDelay = (p * 2.1 + i * 0.7).toFixed(1) + "s";
        puff.style.animationDuration = (6.4 + p * 0.8).toFixed(1) + "s";
        chimney.appendChild(puff);
      }
      layer.appendChild(chimney);
    }
  }

  /* 码头货柜 / 前景货柜 / 卡车 */
  function buildProps(root) {
    var palettes = [
      ["#8a5a3c", "#3f6d7a", "#a8543f"],
      ["#2f6f6a", "#8a5a3c", "#c08a4a"],
      ["#3f6d7a", "#a8543f", "#8a5a3c"]
    ];
    var quay = narrow
      ? [{ x: 11, y: 60 }, { x: 90, y: 60 }]
      : [{ x: 9, y: 60 }, { x: 16, y: 60 }, { x: 91, y: 60 }];
    var fore = narrow ? [{ x: 6, y: 96 }, { x: 94, y: 96 }] : [{ x: 5, y: 96 }, { x: 95, y: 96 }];

    var all = quay.concat(fore);
    for (var i = 0; i < all.length; i++) {
      var s = el("div", "we-stack");
      var pal = palettes[i % palettes.length];
      s.style.setProperty("--we-c1", pal[0]);
      s.style.setProperty("--we-c2", pal[1]);
      s.style.setProperty("--we-c3", pal[2]);
      placeAt(s, all[i].x, all[i].y);
      root.appendChild(s);
    }

    var truck = el("div", "we-truck");
    placeAt(truck, narrow ? 87 : 89, narrow ? 92 : 93);
    root.appendChild(truck);
  }

  function buildLamps(root) {
    var lampWide = [{ x: 8, y: 77 }, { x: 33, y: 77 }, { x: 55, y: 77 }, { x: 82, y: 77 }];
    var lampNarrow = [{ x: 22, y: 76 }, { x: 62, y: 76 }];
    var spots = narrow ? lampNarrow : lampWide;
    for (var i = 0; i < spots.length; i++) {
      var lamp = el("div", "we-lamp");
      placeAt(lamp, spots[i].x, spots[i].y);
      root.appendChild(lamp);
    }
  }

  function detailHtml(kind) {
    if (kind === "battery") {
      return '<span class="we-bld-chimney" style="left:7%"></span>' +
        '<span class="we-bld-chimney" style="left:22%;height:30%"></span>' +
        '<span class="we-bld-silo" style="left:74%"></span>' +
        '<span class="we-bld-tank" style="left:44%"></span>' +
        '<span class="we-bld-tank" style="left:63%"></span>';
    }
    if (kind === "auto") {
      return '<span class="we-bld-car" style="left:6%"></span>' +
        '<span class="we-bld-car" style="left:30%;--we-car:#c8724f"></span>' +
        '<span class="we-bld-car" style="left:54%;--we-car:#8ab6c4"></span>' +
        '<span class="we-bld-car" style="left:78%;--we-car:#c8a04f"></span>';
    }
    if (kind === "fab") {
      return '<span class="we-bld-tower" style="left:28%;width:44%"></span>' +
        '<span class="we-bld-wafer" style="bottom:30%;width:34%"></span>';
    }
    if (kind === "equip") {
      return '<span class="we-bld-pipe" style="left:24%;height:38%"></span>' +
        '<span class="we-bld-pipe" style="left:42%;height:50%"></span>' +
        '<span class="we-bld-pipe" style="left:60%;height:32%"></span>';
    }
    return '<span class="we-bld-tower" style="left:30%;width:40%;height:44%"></span>' +
      '<span class="we-bld-antenna" style="left:50%"></span>';
  }

  function buildBuilding(c) {
    var skin = SKIN[c.kind] || SKIN.tech;
    var b = el("button", "we-bld we-bld-" + c.kind);
    b.type = "button";
    b.dataset.company = c.id;
    b.setAttribute("aria-label", c.name + " · " + c.tag + (c.enter ? " · 可进入探索" : " · 暂未开放"));
    b.style.setProperty("--we-body", skin.body);
    b.style.setProperty("--we-roof", skin.roof);
    b.style.setProperty("--we-win-color", skin.win);
    b.style.setProperty("--we-win-alpha", skin.alpha);
    b.innerHTML =
      '<span class="we-bld-base"></span>' +
      '<span class="we-bld-body"></span>' +
      '<span class="we-bld-roof"></span>' +
      '<span class="we-bld-top"></span>' +
      detailHtml(c.kind) +
      '<span class="we-bld-sign"><b>' + esc(c.label) + '</b><i>' + esc(c.name) + '</i></span>' +
      '<span class="we-bld-marker">▼</span>';
    return b;
  }

  /* 加号基座：一座小台子，上面顶着一个发光的「+」 */
  function buildPedestal() {
    var p = el("button", "we-pedestal");
    p.type = "button";
    p.dataset.company = PEDESTAL.id;
    p.setAttribute("aria-label", PEDESTAL.label + "：输入你想了解的公司");
    p.innerHTML =
      '<span class="we-pd-glow"></span>' +
      '<span class="we-pd-plus" aria-hidden="true">+</span>' +
      '<span class="we-pd-cap"></span>' +
      '<span class="we-pd-shaft"></span>' +
      '<span class="we-pd-base"></span>' +
      '<span class="we-pd-sign">' + PEDESTAL.label + '</span>';
    return p;
  }

  /* 传送点：地图道路两侧的门；走过去会翻到上一页/下一页「新区」地图。 */
  function buildPortal(spec, dir) {
    var p = el("button", "we-portal we-portal-" + (dir < 0 ? "left" : "right"));
    p.type = "button";
    p.dataset.dir = String(dir);
    p.setAttribute("aria-label", spec.label);
    p.innerHTML =
      '<span class="we-pt-pillar we-pt-pillar-a"></span>' +
      '<span class="we-pt-pillar we-pt-pillar-b"></span>' +
      '<span class="we-pt-arch"></span>' +
      '<span class="we-pt-glow"></span>' +
      '<span class="we-pt-sign">' + esc(spec.label) + '</span>';
    return p;
  }

  function buildPlayer() {
    var p = el("div", "we-player");
    p.dataset.facing = "right";
    p.innerHTML =
      '<span class="we-pl-inner">' +
      '<span class="we-pl-shadow"></span>' +
      '<span class="we-pl-backpack"></span>' +
      '<span class="we-pl-leg we-pl-leg-l"></span>' +
      '<span class="we-pl-leg we-pl-leg-r"></span>' +
      '<span class="we-pl-body"></span>' +
      '<span class="we-pl-arm"></span>' +
      '<span class="we-pl-head"></span>' +
      '</span>';
    return p;
  }

  /* ---------- 坐标 / 落位 ---------- */

  function place(animate) {
    if (!stage || !player) return;
    var w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    var pw = player.offsetWidth || 22;
    var tx = w * state.x / 100 - pw / 2;
    var ty = -h * (1 - state.y / 100);
    if (animate === false) {
      var prev = player.style.transitionDuration || "0s";
      player.style.transitionDuration = "0s";
      player.style.transform = "translate3d(" + tx.toFixed(1) + "px," + ty.toFixed(1) + "px,0)";
      void player.offsetWidth;
      player.style.transitionDuration = prev;
    } else {
      player.style.transform = "translate3d(" + tx.toFixed(1) + "px," + ty.toFixed(1) + "px,0)";
    }
    player.style.zIndex = String(Math.round(state.y) + 1);
  }

  function standPoint(c) {
    var l = layoutOf(c);
    return { x: l.x, y: clamp(l.y + 4, WALK_MIN_Y, WALK_MAX_Y) };
  }

  function applyLayout() {
    var list = buildingsForMap(currentMapIndex);
    for (var i = 0; i < list.length; i++) layoutEntity(nodes[list[i].id], list[i]);
    if (pedestal) layoutEntity(pedestal, PEDESTAL);
    if (portalLeftNode) layoutEntity(portalLeftNode, PORTAL_LEFT);
    if (portalRightNode) layoutEntity(portalRightNode, PORTAL_RIGHT);
  }

  function layoutEntity(node, spec) {
    if (!node) return;
    var l = layoutOf(spec);
    placeAt(node, l.x, l.y);
    node.style.width = l.w + "%";
    node.style.height = l.h + "%";
  }

  /* ---------- 移动 ---------- */

  function clearArrival() {
    if (arrivalTimer) { clearTimeout(arrivalTimer); arrivalTimer = null; }
    if (arrivalHandler) { player.removeEventListener("transitionend", arrivalHandler); arrivalHandler = null; }
  }

  function moveTo(tx, ty, onArrive) {
    var dx = tx - state.x, dy = ty - state.y;
    var dist = Math.sqrt(dx * dx + dy * dy);
    clearArrival();
    if (dist < 0.8) {
      state.x = tx; state.y = ty;
      place(false);
      if (onArrive) onArrive();
      return;
    }
    state.x = tx; state.y = ty;
    if (Math.abs(dx) > 0.6) player.dataset.facing = dx < 0 ? "left" : "right";
    var dur = clamp(dist * 0.055, 0.42, 1.5);
    player.style.transitionDuration = dur + "s";
    void player.offsetWidth;   /* 强制一次重排，确保新的 duration 先于 transform 生效 */
    player.classList.add("is-walking");
    place(true);

    var done = false;
    var fire = function () {
      if (done) return;
      done = true;
      clearArrival();
      player.classList.remove("is-walking");
      if (onArrive) onArrive();
    };
    /* 只认小人自己身上的过渡：内层 .we-pl-inner 翻转朝向时也会发 transitionend，
       而且会冒泡上来，不区分 target 的话「到达」会提前触发。 */
    var onEnd = function (event) {
      if (event && event.target !== player) return;
      fire();
    };
    arrivalHandler = onEnd;
    player.addEventListener("transitionend", onEnd);
    /* 无障碍（prefers-reduced-motion）下过渡被压到 0.01ms，transitionend 仍会到；
       这里再加一条兜底，保证任何情况下「到达」都会发生。 */
    arrivalTimer = setTimeout(fire, dur * 1000 + 150);
  }

  /* ---------- 公司交互 ---------- */

  function paint() {
    var list = buildingsForMap(currentMapIndex);
    for (var i = 0; i < list.length; i++) {
      var node = nodes[list[i].id];
      if (!node) continue;
      node.classList.toggle("is-active", state.selected === list[i].id);
    }
    if (pedestal) pedestal.classList.toggle("is-active", state.selected === PEDESTAL.id);
    if (portalLeftNode) portalLeftNode.classList.toggle("is-active", state.selected === PORTAL_LEFT.id);
    if (portalRightNode) portalRightNode.classList.toggle("is-active", state.selected === PORTAL_RIGHT.id);
  }

  function showCard(c) {
    card.innerHTML =
      '<div class="we-card-code">' + (c.enter ? esc(c.code) : "COMING SOON") + '</div>' +
      '<div class="we-card-name">' + esc(c.name) + '</div>' +
      '<div class="we-card-tag">' + esc(c.tag) + '</div>' +
      (c.enter
        ? '<button type="button" class="we-card-act" data-enter="1">进入探索</button>'
        : '<button type="button" class="we-card-act is-soon" disabled>新的产业调查正在准备中……</button>');
    card.hidden = false;
  }

  function deselect() {
    state.selected = null;
    paint();
    card.hidden = true;
  }

  function select(id) {
    var c = findCompany(id);
    if (!c) return;
    var stand = standPoint(c);
    moveTo(stand.x, stand.y, function () {
      state.selected = c.id;
      paint();
      showCard(c);
    });
  }

  /* 「想了解哪家公司？」——自己输入，提交后交给宿主 */
  function showRequestCard() {
    card.innerHTML =
      '<div class="we-card-code">NEW</div>' +
      '<div class="we-card-name">想了解哪家公司？</div>' +
      '<div class="we-card-tag">说出名字，玑衡替你把它的产业链搭出来</div>' +
      '<form class="we-card-form" data-request-form="1">' +
      '<input class="we-card-input" type="text" maxlength="24" autocomplete="off" ' +
      'placeholder="例如：隆基绿能" aria-label="公司名称">' +
      '<button class="we-card-act" type="submit">开始搭建</button>' +
      '</form>';
    card.hidden = false;
    var input = card.querySelector(".we-card-input");
    if (input && input.focus) input.focus();
  }

  function showGeneratingCard(name) {
    card.innerHTML =
      '<div class="we-card-code">生成中</div>' +
      '<div class="we-card-name">' + esc(name) + '</div>' +
      '<div class="we-card-tag">玑衡 Agent 正在为「' + esc(name) + '」搭建产业链关卡，请稍候……</div>' +
      '<button type="button" class="we-card-act is-soon" disabled>生成中…</button>';
    card.hidden = false;
  }

  function showErrorCard(message) {
    card.innerHTML =
      '<div class="we-card-code">NEW</div>' +
      '<div class="we-card-name">生成失败</div>' +
      '<div class="we-card-tag">' + esc(message || "请稍后重试") + '</div>' +
      '<form class="we-card-form" data-request-form="1">' +
      '<input class="we-card-input" type="text" maxlength="24" autocomplete="off" ' +
      'value="' + esc(state.requested || "") + '" aria-label="公司名称">' +
      '<button class="we-card-act" type="submit">重新尝试</button>' +
      '</form>';
    card.hidden = false;
  }

  function selectPedestal() {
    var stand = standPoint(PEDESTAL);
    moveTo(stand.x, stand.y, function () {
      state.selected = PEDESTAL.id;
      paint();
      showRequestCard();
    });
  }

  /* 走到传送点后翻页：往左减一页、往右加一页，越界会被 changeMap 自己钳制住。 */
  function selectPortal(dir) {
    var target = dir < 0 ? PORTAL_LEFT : PORTAL_RIGHT;
    var stand = standPoint(target);
    moveTo(stand.x, stand.y, function () {
      state.selected = target.id;
      paint();
      changeMap(dir);
    });
  }

  /* 切换当前地图页：重建建筑/传送点，并把玩家放在「从另一侧走出来」的位置，
     制造穿过传送门、走进下一张地图的感觉。 */
  function changeMap(dir) {
    var nextIndex = clamp(currentMapIndex + dir, 0, maxMapIndex());
    if (nextIndex === currentMapIndex) return;
    currentMapIndex = nextIndex;
    state.selected = null;
    card.hidden = true;
    rebuildBuildings();
    var entrySpot = standPoint(dir > 0 ? PORTAL_LEFT : PORTAL_RIGHT);
    state.x = entrySpot.x;
    state.y = entrySpot.y;
    place(false);
    paint();
    updateMapHud();
  }

  function updateMapHud() {
    if (!mapHud) return;
    var total = maxMapIndex() + 1;
    mapHud.textContent = total > 1 ? "地图 " + (currentMapIndex + 1) + " / " + total : "";
  }

  function submitCompany(rawName) {
    var name = String(rawName || "").replace(/\s+/g, " ").trim().slice(0, 24);
    if (!name) return false;
    state.requested = name;
    if (global.JihengWorldBridge && typeof global.JihengWorldBridge.postMessage === "function") {
      showGeneratingCard(name);
      global.JihengWorldBridge.postMessage(JSON.stringify({ type: "request-company", company: name }));
    } else {
      showErrorCard("生成产业链关卡需要在玑衡 App 内联网使用。");
    }
    return true;
  }

  function onStageSubmit(event) {
    var form = event.target;
    if (!form || !form.closest || !form.closest("[data-request-form]")) return;
    event.preventDefault();
    var input = form.querySelector(".we-card-input");
    if (!submitCompany(input ? input.value : "") && input && input.focus) input.focus();
  }

  function enterScenario() {
    if (typeof global.CustomEvent === "function") {
      global.dispatchEvent(new CustomEvent(ENTER_EVENT, { detail: { companyId: state.selected } }));
    }
  }

  function onStageClick(event) {
    var target = event.target;
    if (target && target.closest) {
      if (target.closest(".we-card")) {
        if (target.closest("[data-enter]")) { enterScenario(); return; }
        if (target.closest("[data-close-card]")) { deselect(); return; }
        return;
      }
      var pod = target.closest(".we-pedestal");
      if (pod) { selectPedestal(); return; }
      var portal = target.closest(".we-portal");
      if (portal) { selectPortal(Number(portal.dataset.dir)); return; }
      var bld = target.closest(".we-bld");
      if (bld) { select(bld.dataset.company); return; }
    }
    var rect = stage.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    var x = clamp(((event.clientX - rect.left) / rect.width) * 100, 5, 95);
    var y = clamp(((event.clientY - rect.top) / rect.height) * 100, WALK_MIN_Y, WALK_MAX_Y);
    deselect();
    moveTo(x, y, null);
  }

  function onResize() {
    var next = isNarrow();
    if (next !== narrow) {
      narrow = next;
      if (state.selected) {
        var c = findCompany(state.selected);
        if (c) { var s = standPoint(c); state.x = s.x; state.y = s.y; }
      }
      buildPropsRefresh();
      applyLayout();
    }
    place(false);
  }

  /* 换布局时，装饰物的坐标也要跟着换 —— 直接重建那几个元素最省事 */
  var propsHost = null;
  function buildPropsRefresh() {
    if (!propsHost) return;
    while (propsHost.firstChild) propsHost.removeChild(propsHost.firstChild);
    buildProps(propsHost);
    buildLamps(propsHost);
  }

  function onBackToWorld() {
    /* 回到 World：人物留在刚才那栋楼旁边（DOM 一直被保留，位置天然还在），
       这里只需要在被显示出来之后重新量一次尺寸。 */
    place(false);
  }

  /* ---------- 挂载 ---------- */

  /* 重建当前地图页上的所有建筑/传送点：初次挂载、「新增公司」、翻页都走这条路，
     保证 nodes/pedestal/传送点与 currentMapIndex 对应的数据同步。 */
  function rebuildBuildings() {
    if (!buildings) return;
    while (buildings.firstChild) buildings.removeChild(buildings.firstChild);
    nodes = {};
    var list = buildingsForMap(currentMapIndex);
    for (var i = 0; i < list.length; i++) {
      var node = buildBuilding(list[i]);
      nodes[list[i].id] = node;
      buildings.appendChild(node);
    }
    pedestal = null;
    if (currentMapIndex === 0) {
      pedestal = buildPedestal();
      buildings.appendChild(pedestal);
    }
    portalLeftNode = portalRightNode = null;
    if (currentMapIndex > 0) {
      portalLeftNode = buildPortal(PORTAL_LEFT, -1);
      buildings.appendChild(portalLeftNode);
    }
    if (currentMapIndex < maxMapIndex()) {
      portalRightNode = buildPortal(PORTAL_RIGHT, 1);
      buildings.appendChild(portalRightNode);
    }
    applyLayout();
  }

  /* 玑衡 Agent 生成关卡成功后，Flutter 通过这个入口把公司写进地图（追加到「新区」分页列表）。
     payload 形如 {company:{id,name,code,tag,kind}, scenes:[...]}；scenes 交给 JHWorldData，供探索页读取。 */
  function addCompany(payload) {
    if (!payload || !payload.company || !Array.isArray(payload.scenes) || !payload.scenes.length) return false;
    var meta = payload.company;
    if (!meta.id || findCompany(meta.id)) return false;
    var posInPage = extraCompanies.length % MAP_CAPACITY;
    var entry = {
      id: meta.id,
      code: meta.code || "",
      name: meta.name || meta.id,
      tag: meta.tag || "",
      kind: SKIN[meta.kind] ? meta.kind : "tech",
      enter: true,
      label: String(meta.name || meta.id).slice(0, 10),
      wide: growthSlot(posInPage, false),
      narrow: growthSlot(posInPage, true)
    };
    extraCompanies.push(entry);
    if (global.JHWorldData) {
      global.JHWorldData.companies.push(entry);
      global.JHWorldData.scenarios[meta.id] = payload.scenes;
    }
    if (mounted) { rebuildBuildings(); updateMapHud(); }
    if (state.selected === PEDESTAL.id) {
      state.selected = entry.id;
      paint();
      showCard(entry);
    }
    return true;
  }

  /* App 打开 World 时把服务端已生成的公司整批灌回来，恢复到重启前的地图状态。 */
  function hydrate(list) {
    (list || []).forEach(function (item) { addCompany(item); });
  }

  /* 生成失败：只有还停在「添加公司」卡片上时才提示，避免打断玩家已经切走的操作。 */
  function setError(message) {
    if (state.selected === PEDESTAL.id) showErrorCard(message);
  }

  function mount(root) {
    if (mounted || !root || !document.querySelector) return;
    mounted = true;
    narrow = isNarrow();
    state.x = (narrow ? SPAWN.narrow : SPAWN.wide).x;
    state.y = (narrow ? SPAWN.narrow : SPAWN.wide).y;

    root.classList.add("we-root");

    var sky = el("div", "we-sky");
    buildSky(sky);
    root.appendChild(sky);

    var far = el("div", "we-skyline-far we-layer");
    far.style.cssText = "position:absolute;inset:0;z-index:3;";
    buildSkyline(far, 7331, 5, 13);
    root.appendChild(far);

    var mid = el("div", "we-skyline-mid we-layer");
    mid.style.cssText = "position:absolute;inset:0;z-index:4;";
    buildSkyline(mid, 9187, 9, 20);
    buildChimneys(mid, [{ left: 70, height: 22 }, { left: 74, height: 16 }, { left: 30, height: 18 }]);
    root.appendChild(mid);

    root.appendChild(el("div", "we-haze"));
    root.appendChild(el("div", "we-water"));
    root.appendChild(el("div", "we-ground"));
    root.appendChild(el("div", "we-road"));

    root.appendChild(el("div", "we-crane"));

    propsHost = el("div", "we-props");
    propsHost.style.cssText = "position:absolute;inset:0;";
    buildProps(propsHost);
    buildLamps(propsHost);
    root.appendChild(propsHost);

    buildings = el("div", "we-buildings");
    buildings.style.cssText = "position:absolute;inset:0;";
    root.appendChild(buildings);
    rebuildBuildings();

    player = buildPlayer();
    root.appendChild(player);

    var hudTop = el("header", "we-hud we-hud-top");
    hudTop.innerHTML = '<div class="we-logo">玑衡 <b>WORLD</b></div><div class="we-sub">探索真实产业</div>';
    mapHud = el("span", "we-map-hud");
    hudTop.appendChild(mapHud);
    root.appendChild(hudTop);

    var hudBottom = el("footer", "we-hud we-hud-bottom");
    hudBottom.innerHTML = '<span class="we-hint">点击公司 · 前往调查</span>';
    root.appendChild(hudBottom);

    card = el("div", "we-card");
    card.hidden = true;
    root.appendChild(card);

    stage = root;
    applyLayout();
    place(false);
    updateMapHud();

    root.addEventListener("click", onStageClick);
    root.addEventListener("submit", onStageSubmit);
    global.addEventListener("resize", onResize);
    global.addEventListener(BACK_EVENT, onBackToWorld);
  }

  global.JHWorldEntry = {
    mount: mount,
    isMounted: function () { return mounted; },
    /* 供调试/测试使用 */
    state: function () { return { x: state.x, y: state.y, selected: state.selected, requested: state.requested }; },
    select: select,
    selectPedestal: selectPedestal,
    requestCompany: submitCompany,
    enter: enterScenario,
    /* 多地图翻页：供调试/测试使用，也可用于将来的地图选择 UI */
    mapIndex: function () { return currentMapIndex; },
    maxMapIndex: maxMapIndex,
    changeMap: changeMap,
    /* 供 Flutter 通过 runJavaScript 调用 */
    addCompany: addCompany,
    hydrate: hydrate,
    setError: setError
  };

  /* 自启动：本文件是页面里的最后一个脚本，DOM 已就绪 */
  function boot() {
    var root = document.getElementById && document.getElementById("worldlayer");
    if (root) mount(root);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(typeof window !== "undefined" ? window : this);
