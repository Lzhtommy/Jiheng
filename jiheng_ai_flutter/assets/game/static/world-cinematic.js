/* 玑衡 World · 演出层。只读场景 DOM，不写剧情/存档，也不发起网络请求。 */
(function (global) {
  "use strict";

  var active = null;
  var signalNames = {
    warehouse: "MATERIAL COST ↓",
    factory: "EFFICIENCY ↑",
    market: "DEMAND ↑"
  };

  function reduced() {
    return !!(global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }
  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character];
    });
  }
  function after(job, callback, delay) {
    var timer = global.setTimeout(callback, delay);
    job.timers.push(timer);
  }
  function finish(job, invoke) {
    if (!job || job.done) return;
    job.done = true;
    job.timers.forEach(global.clearTimeout.bind(global));
    job.frames.forEach(global.cancelAnimationFrame.bind(global));
    if (job.node.parentNode) job.node.parentNode.removeChild(job.node);
    job.root.classList.remove("cg-playing", "cg-world-playing");
    job.root.style.removeProperty("--cg-focus-x");
    job.root.style.removeProperty("--cg-focus-y");
    if (active === job) active = null;
    if (invoke && job.onDone) job.onDone();
  }
  function play(root, kind, content, duration, onDone, canSkip) {
    if (!root || !global.document || !global.document.createElement) {
      if (onDone) onDone();
      return null;
    }
    if (active) finish(active, false);
    var node = global.document.createElement("div");
    node.className = "cg-screen cg-" + kind;
    node.setAttribute("role", "status");
    node.setAttribute("aria-live", "polite");
    node.innerHTML = content + (canSkip ? '<button class="cg-skip" type="button" data-cg-skip="1" aria-label="跳过演出">SKIP »</button>' : "");
    root.appendChild(node);
    root.classList.add(kind === "world-enter" ? "cg-world-playing" : "cg-playing");
    var job = { root: root, node: node, timers: [], frames: [], onDone: onDone, done: false };
    active = job;
    node.addEventListener("click", function (event) {
      if (event.target.closest && event.target.closest("[data-cg-skip]")) finish(job, true);
    });
    after(job, function () { finish(job, true); }, reduced() ? 80 : duration);
    return job;
  }

  function count(job, selector, delay) {
    if (!job || reduced()) return;
    after(job, function () {
      var nodes = job.node.querySelectorAll(selector);
      nodes.forEach(function (node) {
        var from = Number(node.dataset.cgFrom || 0);
        var to = Number(node.dataset.cgTo || 0);
        var suffix = node.dataset.cgSuffix || "";
        var started = global.performance.now();
        function frame(now) {
          if (job.done) return;
          var t = Math.min(1, (now - started) / 520);
          var value = Math.round(from + (to - from) * (1 - Math.pow(1 - t, 3)));
          node.textContent = (value < 0 ? "−" : "") + Math.abs(value) + suffix;
          if (t < 1) job.frames.push(global.requestAnimationFrame(frame));
        }
        job.frames.push(global.requestAnimationFrame(frame));
      });
    }, delay);
  }

  function stationMarkup(id) {
    if (id === "warehouse") return '<div class="cg-hud-label">WAREHOUSE DATA LINK <em>CONNECTED</em></div>' +
      '<div class="cg-data"><span>LFP MATERIAL <b data-cg-from="0" data-cg-to="-18" data-cg-suffix="%">−18%</b></span>' +
      '<span>ELECTROLYTE <b data-cg-from="0" data-cg-to="-11" data-cg-suffix="%">−11%</b></span>' +
      '<span>SEPARATOR <b data-cg-from="0" data-cg-to="-6" data-cg-suffix="%">−6%</b></span></div>' +
      '<svg class="cg-trend" viewBox="0 0 260 70" aria-hidden="true"><path d="M5 9 C50 9 60 22 99 24 S153 49 193 53 S229 63 255 63"/></svg>' +
      '<div class="cg-verdict"><small>SIGNAL DETECTED</small><strong>MATERIAL COST ↓</strong><span>上游成本回落</span></div>';
    if (id === "factory") return '<div class="cg-hud-label">PRODUCTION LINE SCAN <em>LINE #03 · ONLINE</em></div>' +
      '<div class="cg-machines" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>' +
      '<div class="cg-data"><span>AUTOMATION <b data-cg-from="72" data-cg-to="89" data-cg-suffix="%">89%</b></span>' +
      '<span>OUTPUT <b data-cg-from="100" data-cg-to="128">128</b></span></div>' +
      '<div class="cg-energy" aria-hidden="true"></div>' +
      '<div class="cg-companion">小玑 · 产出提高了，单位制造成本却下降了。</div>' +
      '<div class="cg-verdict"><small>SIGNAL DETECTED</small><strong>EFFICIENCY ↑</strong><span>生产效率提升</span></div>';
    return '<div class="cg-hud-label">MARKET DATA LINK <em>SIMULATION · 情景模拟</em></div>' +
      '<div class="cg-data cg-market-data"><span>EV SALES <b>↑ 23%</b></span>' +
      '<span>ENERGY STORAGE <b>↑ 31%</b></span>' +
      '<span>CELL PRICE <b>↓ 16%</b></span></div>' +
      '<div class="cg-contrast">DEMAND ↑ <i>BUT</i> PRICE ↓</div>' +
      '<div class="cg-companion">小玑 · 需求在增长，价格却在下降？</div>' +
      '<div class="cg-verdict"><small>ANOMALY DETECTED</small><strong>DEMAND ↑ · PRICE ↓</strong><span>需求与报价出现背离</span></div>';
  }

  function playScan(root, id, onDone) {
    if (!signalNames[id]) { if (onDone) onDone(); return; }
    play(root, "scan", '<div class="cg-target"><div class="cg-scan-line"></div><span>ANALYZING · ' +
      escapeHtml(id.toUpperCase()) + '</span></div>', 650, onDone, false);
    if (active) active.node.dataset.station = id;
  }

  function playInvestigation(root, id, onDone) {
    if (!signalNames[id]) { if (onDone) onDone(); return; }
    var content = '<div class="cg-target cg-result-target"><div class="cg-scan-line"></div></div>' +
      '<div class="cg-hud"><div class="cg-kicker">JIHENG / INVESTIGATION</div>' + stationMarkup(id) +
      '<small class="cg-disclaimer">数值仅为虚构教学场景，并非真实企业数据</small></div>';
    var job = play(root, "result", content, 1950, onDone, false);
    if (!job) return;
    job.node.dataset.station = id;
    count(job, "[data-cg-to]", 400);
  }

  function playInsight(root, onDone) {
    var content = '<div class="cg-insight-signal cg-s1"><small>01 / WAREHOUSE</small><b>MATERIAL COST ↓</b></div>' +
      '<div class="cg-insight-signal cg-s2"><small>02 / FACTORY</small><b>EFFICIENCY ↑</b></div>' +
      '<div class="cg-insight-signal cg-s3"><small>03 / MARKET</small><b>DEMAND ↑</b></div>' +
      '<svg class="cg-insight-paths" viewBox="0 0 1000 600" preserveAspectRatio="none" aria-hidden="true">' +
      '<path d="M180 390 Q310 435 500 330"/><path d="M500 258 L500 330"/><path d="M820 198 Q670 420 500 330"/></svg>' +
      '<div class="cg-cell-core"><span class="cg-core-ring"></span><span>CELL</span></div>' +
      '<div class="cg-chain">CHAIN REACTION</div>' +
      '<div class="cg-insight-title"><small>INDUSTRY INSIGHT · UNLOCKED</small><strong>CELL PRICE ↓</strong>' +
      '<span>电芯价格下降 ≠ 市场需求消失</span><em>材料成本回落 + 生产效率提升 + 行业竞争</em></div>' +
      '<div class="cg-flash"></div>';
    play(root, "insight", content, 3150, onDone, true);
  }

  function playUnlock(root, nextName, onDone) {
    var content = '<div class="cg-area-heading"><small>AREA COMPLETE</small><strong>03 / 电芯城</strong>' +
      '<span>INDUSTRY INSIGHT ACQUIRED · 电芯成本与规模效应</span></div>' +
      '<div class="cg-unlock-route"><div class="cg-unlock-node is-done"><small>03 / CELL CITY</small><b>电芯城 ✓</b></div>' +
      '<svg viewBox="0 0 500 60" preserveAspectRatio="none" aria-hidden="true"><path d="M4 30 H496"/></svg>' +
      '<div class="cg-unlock-node is-next"><small>04 / NEW AREA</small><b>' + escapeHtml(nextName) + '</b><em>UNLOCKED</em></div></div>' +
      '<div class="cg-unlock-foot">产业路线已点亮 · 由你决定何时出发</div>';
    play(root, "unlock", content, 2500, onDone, true);
  }

  function playWorldEnter(root, player, building, onDone) {
    if (!root || !player || !building || !root.getBoundingClientRect) { if (onDone) onDone(); return; }
    var rect = root.getBoundingClientRect();
    var start = player.getBoundingClientRect(), end = building.getBoundingClientRect();
    var x1 = start.left + start.width / 2 - rect.left, y1 = start.top + start.height / 2 - rect.top;
    var x2 = end.left + end.width / 2 - rect.left, y2 = end.top + end.height / 2 - rect.top;
    var bend = Math.min(y1, y2) - Math.max(42, Math.abs(x2 - x1) * 0.16);
    var curveX = (x1 + x2) / 2 + (Math.abs(x2 - x1) < 55 ? Math.min(rect.width * 0.12, 140) : 0);
    var path = 'M' + x1.toFixed(1) + ' ' + y1.toFixed(1) + ' Q' + curveX.toFixed(1) + ' ' + bend.toFixed(1) + ' ' + x2.toFixed(1) + ' ' + y2.toFixed(1);
    var dots = [0.25, 0.5, 0.75].map(function (t) {
      var x = (1 - t) * (1 - t) * x1 + 2 * (1 - t) * t * curveX + t * t * x2;
      var y = (1 - t) * (1 - t) * y1 + 2 * (1 - t) * t * bend + t * t * y2;
      return '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="3"/>';
    }).join("");
    var content = '<svg class="cg-world-route" viewBox="0 0 ' + rect.width + ' ' + rect.height +
      '" preserveAspectRatio="none" aria-hidden="true"><path d="' + path + '"/>' +
      '<circle cx="' + x1 + '" cy="' + y1 + '" r="4"/>' + dots + '<circle cx="' + x2 + '" cy="' + y2 + '" r="5"/></svg>' +
      '<div class="cg-world-title"><small>ENTERING INDUSTRY WORLD</small><strong>CATL · 动力电池</strong>' +
      '<span>正在进入产业世界</span></div><div class="cg-blackout"></div>';
    if (play(root, "world-enter", content, 1950, onDone, false)) {
      root.style.setProperty("--cg-focus-x", ((x2 / rect.width) * 100).toFixed(1) + "%");
      root.style.setProperty("--cg-focus-y", ((y2 / rect.height) * 100).toFixed(1) + "%");
    }
  }

  function revealScene(root) {
    if (!root) return;
    root.classList.remove("cg-reveal");
    void root.offsetWidth;
    root.classList.add("cg-reveal");
    global.setTimeout(function () { root.classList.remove("cg-reveal"); }, reduced() ? 80 : 1250);
  }

  global.JHWorldFX = {
    playScan: playScan,
    playInvestigation: playInvestigation,
    playInsight: playInsight,
    playUnlock: playUnlock,
    playWorldEnter: playWorldEnter,
    revealScene: revealScene,
    cancel: function () { if (active) finish(active, false); },
    isPlaying: function () { return !!active; }
  };
})(typeof window !== "undefined" ? window : this);
