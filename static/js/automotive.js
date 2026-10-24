/* ── CRONOS DASHBOARD ── */

const CHART_DEFAULTS = {
  color: '#f0f0f0',
  grid: 'rgba(255,255,255,0.04)',
  red: '#CE2B37',        /* vermelho italiano */
  blue: '#8a9099',       /* prata metálica */
  ok: '#009246',         /* verde italiano */
  warn: '#f59e0b',
  gold: '#c9a84c',
  silver: '#b0b8c2',
  bg_red: 'rgba(206,43,55,0.12)',
  bg_blue: 'rgba(138,144,153,0.12)',
  bg_ok: 'rgba(0,146,70,0.12)',
};

if (typeof Chart !== 'undefined') {
  Chart.defaults.color = CHART_DEFAULTS.color;
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.font.size = 11;
}

// ── BOOT ──────────────────────────────────────────────
const BOOT_MSGS = [
  'Inicializando sistema de bordo...',
  'Carregando dados do veículo...',
  'Conectando ao banco de dados...',
  'Pronto.',
];

function runBoot() {
  const boot = document.getElementById('boot');
  if (!boot) {
    // Páginas sem boot screen (veículos, formulários)
    initAll();
    return;
  }
  const el = document.getElementById('boot-msg');
  let i = 0;
  const iv = setInterval(() => {
    if (i < BOOT_MSGS.length && el) el.textContent = BOOT_MSGS[i++];
  }, 350);

  setTimeout(() => {
    clearInterval(iv);
    boot.style.transition = 'opacity .5s ease';
    boot.style.opacity = '0';
    setTimeout(() => {
      boot.style.display = 'none';
      const app = document.getElementById('app');
      if (app) app.classList.add('ready');
      initAll();
    }, 500);
  }, 1800);
}

// ── SECTION NAV ───────────────────────────────────────
const sections = {};
let activeSection = 'home';

function initNav() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const sec = btn.dataset.section;
      if (sec) switchSection(sec, btn.dataset.label || sec);
    });
  });
}

function switchSection(id, label) {
  if (activeSection === id) return;
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const el = document.getElementById('sec-' + id);
  if (el) el.classList.add('active');
  const btn = document.querySelector(`.nav-item[data-section="${id}"]`);
  if (btn) btn.classList.add('active');
  document.getElementById('topbar-title').textContent = label || id;
  activeSection = id;
  if (window.innerWidth <= 768) closeSidebar();
}

// ── COUNTER ANIMATION ─────────────────────────────────
function animateCounter(el, target, prefix = '', suffix = '', decimals = 0, duration = 1200) {
  const start = performance.now();
  const step = (ts) => {
    const p = Math.min((ts - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    const val = target * ease;
    el.textContent = prefix + val.toLocaleString('pt-BR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }) + suffix;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function initCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseFloat(el.dataset.count);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const dec = parseInt(el.dataset.dec || '0');
    animateCounter(el, target, prefix, suffix, dec);
  });
}

// ── GAUGE ─────────────────────────────────────────────
function initGauges() {
  document.querySelectorAll('[data-gauge]').forEach(el => {
    const pct = parseFloat(el.dataset.gauge) / 100;
    const fill = el.querySelector('.gauge-fill');
    if (!fill) return;
    const total = 251;
    const offset = total - (total * pct);
    setTimeout(() => {
      fill.style.strokeDashoffset = offset;
    }, 200);
  });
}

// ── FUEL SEGMENTS ─────────────────────────────────────
function initFuel() {
  document.querySelectorAll('[data-fuel]').forEach(wrap => {
    const pct = parseFloat(wrap.dataset.fuel);
    const segs = wrap.querySelectorAll('.fuel-seg');
    const lit = Math.round((pct / 100) * segs.length);
    segs.forEach((s, i) => {
      setTimeout(() => {
        if (i < lit) {
          s.classList.add(pct < 20 ? 'danger' : pct < 35 ? 'warn' : 'lit');
        }
      }, i * 60);
    });
  });
}

// ── CHARTS ────────────────────────────────────────────
let charts = {};

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function mkChart(id, config) {
  destroyChart(id);
  const canvas = document.getElementById(id);
  if (!canvas) return;
  charts[id] = new Chart(canvas, config);
  return charts[id];
}

function gridOpts(color = CHART_DEFAULTS.grid) {
  return { color, drawBorder: false };
}

function tickOpts() {
  return { color: 'rgba(255,255,255,0.3)', padding: 6 };
}

function initChartGastosMes(data) {
  if (!data || !data.length) return;
  const labels = data.map(d => d.mes);
  const values = data.map(d => d.total);
  mkChart('chart-gastos-mes', {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Gasto Total (R$)',
        data: values,
        borderColor: CHART_DEFAULTS.red,
        backgroundColor: CHART_DEFAULTS.bg_red,
        fill: true,
        tension: .4,
        pointBackgroundColor: CHART_DEFAULTS.red,
        pointRadius: 4,
        pointHoverRadius: 7,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        label: ctx => ' R$ ' + ctx.raw.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
      }}},
      scales: {
        x: { grid: gridOpts(), ticks: tickOpts() },
        y: { grid: gridOpts(), ticks: { ...tickOpts(), callback: v => 'R$' + v.toLocaleString('pt-BR') }, beginAtZero: true }
      }
    }
  });
}

function initChartCategorias(data) {
  if (!data || !data.length) return;
  const COLORS = [
    CHART_DEFAULTS.red, CHART_DEFAULTS.blue, CHART_DEFAULTS.ok,
    CHART_DEFAULTS.warn, CHART_DEFAULTS.gold, '#9b59b6', '#e67e22', '#1abc9c'
  ];
  mkChart('chart-categorias', {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.categoria),
      datasets: [{
        data: data.map(d => d.total),
        backgroundColor: COLORS.map(c => c + '22'),
        borderColor: COLORS,
        borderWidth: 2,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: { position: 'right', labels: { padding: 12, boxWidth: 10 } },
        tooltip: { callbacks: {
          label: ctx => ' R$ ' + ctx.raw.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
        }}
      }
    }
  });
}

function initChartCombustivel(data) {
  if (!data || !data.length) return;
  mkChart('chart-combustivel', {
    type: 'bar',
    data: {
      labels: data.map(d => d.mes),
      datasets: [
        {
          label: 'Valor (R$)',
          data: data.map(d => d.valor),
          backgroundColor: CHART_DEFAULTS.bg_red,
          borderColor: CHART_DEFAULTS.red,
          borderWidth: 2,
          borderRadius: 6,
          yAxisID: 'y',
        },
        {
          label: 'Litros',
          data: data.map(d => d.litros),
          backgroundColor: CHART_DEFAULTS.bg_blue,
          borderColor: CHART_DEFAULTS.blue,
          borderWidth: 2,
          borderRadius: 6,
          type: 'line',
          tension: .4,
          yAxisID: 'y1',
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: { padding: 16, boxWidth: 10 } } },
      scales: {
        x: { grid: gridOpts(), ticks: tickOpts() },
        y: { grid: gridOpts(), ticks: { ...tickOpts(), callback: v => 'R$' + v }, beginAtZero: true, position: 'left' },
        y1: { grid: { display: false }, ticks: { ...tickOpts(), callback: v => v + 'L' }, beginAtZero: true, position: 'right' },
      }
    }
  });
}

function initChartAnual(data) {
  if (!data || !data.length) return;
  mkChart('chart-anual', {
    type: 'bar',
    data: {
      labels: data.map(d => d.mes),
      datasets: [{
        label: 'Gasto mensal (R$)',
        data: data.map(d => d.total),
        backgroundColor: data.map((_, i) => i === data.length - 1 ? CHART_DEFAULTS.red : CHART_DEFAULTS.bg_red),
        borderColor: CHART_DEFAULTS.red,
        borderWidth: 1.5,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        label: ctx => ' R$ ' + ctx.raw.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
      }}},
      scales: {
        x: { grid: gridOpts(), ticks: tickOpts() },
        y: { grid: gridOpts(), ticks: { ...tickOpts(), callback: v => 'R$' + v.toLocaleString('pt-BR') }, beginAtZero: true }
      }
    }
  });
}

// ── MODALS ────────────────────────────────────────────
function openModal(id) {
  const overlay = document.getElementById('modal-' + id);
  if (overlay) overlay.classList.add('open');
}
function closeModal(id) {
  const overlay = document.getElementById('modal-' + id);
  if (overlay) overlay.classList.remove('open');
}

function initModals() {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.modal-overlay').classList.remove('open');
    });
  });
}

// ── FLASH ─────────────────────────────────────────────
function initFlash() {
  document.querySelectorAll('.flash-msg').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity .4s, transform .4s';
      el.style.opacity = '0';
      el.style.transform = 'translateX(20px)';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });
}

// ── SIDEBAR MOBILE ────────────────────────────────────
function openSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sb-overlay');
  if (sidebar) sidebar.classList.add('open');
  if (overlay) overlay.classList.add('visible');
}
function closeSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sb-overlay');
  if (sidebar) sidebar.classList.remove('open');
  if (overlay) overlay.classList.remove('visible');
}

function initSidebarToggle() {
  const toggle = document.getElementById('sb-toggle');
  const overlay = document.getElementById('sb-overlay');
  if (toggle) toggle.addEventListener('click', () => {
    document.getElementById('sidebar').classList.contains('open') ? closeSidebar() : openSidebar();
  });
  if (overlay) overlay.addEventListener('click', closeSidebar);
}

// ── DELETE CONFIRM ────────────────────────────────────
function confirmDelete(formId) {
  if (confirm('Confirmar exclusão?')) {
    document.getElementById(formId).submit();
  }
}

// ── INIT ALL ──────────────────────────────────────────
function initAll() {
  initNav();
  initCounters();
  initGauges();
  initFuel();
  initModals();
  initFlash();
  initSidebarToggle();

  // Charts - data injected from template
  if (window.DASH) {
    initChartGastosMes(window.DASH.gastos_por_mes);
    initChartCategorias(window.DASH.gastos_por_categoria);
    initChartCombustivel(window.DASH.combustivel_por_mes);
    initChartAnual(window.DASH.gastos_por_mes);
  }
}

document.addEventListener('DOMContentLoaded', runBoot);
