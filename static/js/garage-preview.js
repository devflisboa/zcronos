/* garage-preview.js — Animação de garagem estilo showroom */
(function () {
  'use strict';

  // ── Mapeamento de cores (PT-BR → HEX) ──────────────────────────────────
  const CORES = {
    branco: '#F0F0F0', branca: '#F0F0F0', white: '#F0F0F0',
    preto: '#151515', preta: '#151515', black: '#151515',
    prata: '#B0BAC5', silver: '#B0BAC5',
    cinza: '#808080', 'cinza escuro': '#555', gray: '#808080', grey: '#808080',
    grafite: '#555', chumbo: '#4a4a4a',
    azul: '#1565C0', 'azul escuro': '#0D47A1', 'azul claro': '#42A5F5', blue: '#1565C0',
    vermelho: '#C62828', red: '#C62828',
    verde: '#2E7D32', 'verde escuro': '#1B5E20', green: '#2E7D32',
    amarelo: '#F9A825', yellow: '#F9A825',
    laranja: '#E65100', orange: '#E65100',
    marrom: '#4E342E', brown: '#4E342E',
    bege: '#D4B896', beige: '#D4B896', champagne: '#F7E7CE',
    rosa: '#AD1457', pink: '#E91E63',
    roxo: '#6A1B9A', lilas: '#9C27B0', purple: '#6A1B9A',
    dourado: '#C8943A', gold: '#C8943A',
    bronze: '#CD7F32',
    bordo: '#800020', vinho: '#7B1020',
    titanio: '#878681', titânio: '#878681',
    cobre: '#B87333',
    terracota: '#C45635',
  };

  function resolverCor(texto) {
    if (!texto) return '#B0BAC5';
    const k = texto.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();
    if (CORES[k]) return CORES[k];
    for (const [chave, hex] of Object.entries(CORES)) {
      const kn = chave.normalize('NFD').replace(/[̀-ͯ]/g, '');
      if (k.includes(kn) || kn.includes(k)) return hex;
    }
    // tenta como valor CSS direto
    return texto;
  }

  function darken(hex, amt) {
    try {
      const n = parseInt(hex.replace('#', ''), 16);
      const r = Math.max(0, (n >> 16) - amt);
      const g = Math.max(0, ((n >> 8) & 0xff) - amt);
      const b = Math.max(0, (n & 0xff) - amt);
      return '#' + ((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1);
    } catch { return '#333'; }
  }

  // ── SVG do carro (sedan moderno) ────────────────────────────────────────
  function gerarCarSVG(corBody) {
    const corEscura = darken(corBody, 40);
    const corMuitoEscura = darken(corBody, 70);

    return `
<svg id="car-svg" viewBox="0 0 500 200" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;overflow:visible">
  <defs>
    <radialGradient id="glowFloor" cx="50%" cy="0%" r="50%">
      <stop offset="0%" stop-color="#D4AF37" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#D4AF37" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="bodyShine" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="rgba(255,255,255,0.18)"/>
      <stop offset="40%" stop-color="rgba(255,255,255,0.06)"/>
      <stop offset="100%" stop-color="rgba(0,0,0,0.2)"/>
    </linearGradient>
    <linearGradient id="windowTint" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#90CAF9" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#1565C0" stop-opacity="0.25"/>
    </linearGradient>
    <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="rgba(0,0,0,0.5)"/>
    </filter>
  </defs>

  <!-- Reflexo no chão -->
  <ellipse cx="250" cy="174" rx="185" ry="10" fill="url(#glowFloor)"/>

  <!-- Sombra do carro -->
  <ellipse cx="250" cy="168" rx="170" ry="7" fill="rgba(0,0,0,0.4)"/>

  <!-- CARROCERIA PRINCIPAL -->
  <path fill="${corBody}" filter="url(#softShadow)" d="
    M 68 160
    Q 56 158 52 148
    L 53 128
    Q 58 98 85 88
    L 110 80
    Q 130 74 155 72
    L 175 53
    Q 202 36 240 33
    Q 276 30 304 38
    L 336 52
    L 372 76
    Q 400 82 428 100
    L 448 118
    Q 455 130 453 146
    Q 451 158 443 162
    L 68 160 Z
  "/>

  <!-- Shine na lataria -->
  <path fill="url(#bodyShine)" d="
    M 68 160
    Q 56 158 52 148 L 53 128
    Q 58 98 85 88 L 110 80
    Q 130 74 155 72 L 175 53
    Q 202 36 240 33 Q 276 30 304 38
    L 336 52 L 372 76
    Q 400 82 428 100 L 448 118
    Q 455 130 453 146 Q 451 158 443 162
    L 68 160 Z
  "/>

  <!-- TETO -->
  <path fill="${corEscura}" d="
    M 175 53
    Q 202 36 240 33
    Q 276 30 304 38
    L 336 52
    L 327 55
    Q 295 44 258 42
    Q 218 39 192 52
    L 175 53 Z
  "/>

  <!-- Para-brisa (windshield) -->
  <path fill="url(#windowTint)" opacity="0.85" d="
    M 176 54
    Q 202 37 240 34
    L 235 73
    L 185 76
    Z
  "/>

  <!-- Janela traseira -->
  <path fill="url(#windowTint)" opacity="0.8" d="
    M 242 33
    Q 277 31 305 39
    L 334 53
    L 280 74
    L 240 73
    Z
  "/>

  <!-- Divisória entre janelas (coluna B) -->
  <rect x="234" y="36" width="7" height="38" fill="${corMuitoEscura}" rx="2"/>

  <!-- Para-lama dianteiro -->
  <path fill="${corEscura}" d="
    M 372 76 Q 400 82 428 100 L 448 118 Q 455 130 453 146 L 442 148 Q 428 115 388 104 Z
  "/>

  <!-- Para-lama traseiro -->
  <path fill="${corEscura}" d="
    M 85 88 L 63 98 Q 55 118 54 135 L 67 136 Q 72 105 92 95 Z
  "/>

  <!-- ARCOS das rodas -->
  <path fill="${corMuitoEscura}" d="M 105 158 Q 105 128 135 126 Q 165 124 168 158 Z"/>
  <path fill="${corMuitoEscura}" d="M 335 158 Q 335 128 362 126 Q 392 124 392 158 Z"/>

  <!-- RODA TRASEIRA -->
  <circle cx="136" cy="161" r="30" fill="#111"/>
  <circle cx="136" cy="161" r="22" fill="#222"/>
  <circle cx="136" cy="161" r="14" fill="#333"/>
  <circle cx="136" cy="161" r="6" fill="#888"/>
  <!-- Raios da roda traseira -->
  <line x1="136" y1="139" x2="136" y2="183" stroke="#666" stroke-width="2.5"/>
  <line x1="114" y1="161" x2="158" y2="161" stroke="#666" stroke-width="2.5"/>
  <line x1="120" y1="145" x2="152" y2="177" stroke="#666" stroke-width="2.5"/>
  <line x1="152" y1="145" x2="120" y2="177" stroke="#666" stroke-width="2.5"/>

  <!-- RODA DIANTEIRA -->
  <circle cx="364" cy="161" r="30" fill="#111"/>
  <circle cx="364" cy="161" r="22" fill="#222"/>
  <circle cx="364" cy="161" r="14" fill="#333"/>
  <circle cx="364" cy="161" r="6" fill="#888"/>
  <!-- Raios da roda dianteira -->
  <line x1="364" y1="139" x2="364" y2="183" stroke="#666" stroke-width="2.5"/>
  <line x1="342" y1="161" x2="386" y2="161" stroke="#666" stroke-width="2.5"/>
  <line x1="348" y1="145" x2="380" y2="177" stroke="#666" stroke-width="2.5"/>
  <line x1="380" y1="145" x2="348" y2="177" stroke="#666" stroke-width="2.5"/>

  <!-- Farol dianteiro -->
  <path fill="#FFFDE7" opacity="0.95" d="M 443 116 Q 455 122 455 136 L 442 140 Q 430 126 443 116 Z"/>
  <path fill="#FFF9C4" opacity="0.5" d="M 446 118 L 455 128 L 452 132 Q 440 120 446 118 Z"/>

  <!-- Farol traseiro -->
  <path fill="#FF1744" opacity="0.8" d="M 55 128 Q 52 138 54 148 L 67 148 Q 64 136 63 126 Z"/>
  <path fill="#FF6D00" opacity="0.5" d="M 57 130 Q 55 140 56 145 L 64 144 Q 62 133 61 128 Z"/>

  <!-- Para-choque dianteiro -->
  <path fill="${corEscura}" d="
    M 443 150 L 456 142 L 460 154 L 455 165 L 440 162 Z
  "/>

  <!-- Para-choque traseiro -->
  <path fill="${corEscura}" d="
    M 48 144 L 54 150 L 68 162 L 55 165 L 42 160 L 40 150 Z
  "/>

  <!-- Soleira (friso lateral) -->
  <path fill="${corMuitoEscura}" d="
    M 68 158 L 105 156 L 170 156 L 335 156 L 392 157 L 443 155 L 444 162 L 68 162 Z
  "/>

  <!-- Maçaneta da porta -->
  <rect x="220" y="118" width="28" height="6" rx="3" fill="${corEscura}" opacity="0.7"/>
  <rect x="222" y="119" width="24" height="4" rx="2" fill="rgba(255,255,255,0.2)"/>
</svg>`;
  }

  // ── HTML da garagem ─────────────────────────────────────────────────────
  function gerarGaragem() {
    return `
<div class="gp-stage">
  <div class="gp-bg">
    <div class="gp-spotlight"></div>
    <div class="gp-floor">
      <div class="gp-floor-grid"></div>
    </div>
  </div>
  <div class="gp-turntable" id="gp-turntable">
    <div class="gp-car-wrap" id="gp-car-wrap">
      ${gerarCarSVG('#B0BAC5')}
    </div>
    <div class="gp-reflection" id="gp-reflection">
      ${gerarCarSVG('#B0BAC5')}
    </div>
  </div>
  <div class="gp-label-bar">
    <span class="gp-label-brand" id="gp-label">ΛUTOVIU</span>
    <span class="gp-label-sub" id="gp-sub">Preencha o formulário</span>
  </div>
</div>`;
  }

  // ── CSS injetado ─────────────────────────────────────────────────────────
  const CSS = `
.gp-wrap {
  position: sticky;
  top: 24px;
  align-self: flex-start;
}
.gp-stage {
  background: #080810;
  border: 1px solid rgba(212,175,55,.25);
  border-radius: 16px;
  overflow: hidden;
  position: relative;
  height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  padding-bottom: 0;
}
.gp-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.gp-spotlight {
  position: absolute;
  top: -60px;
  left: 50%;
  transform: translateX(-50%);
  width: 320px;
  height: 320px;
  background: radial-gradient(ellipse, rgba(212,175,55,.18) 0%, transparent 70%);
  pointer-events: none;
}
.gp-floor {
  position: absolute;
  bottom: 0;
  left: 0; right: 0;
  height: 110px;
  background: linear-gradient(to bottom, transparent, rgba(212,175,55,.04) 40%, rgba(0,0,0,.3));
  overflow: hidden;
}
.gp-floor-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(212,175,55,.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(212,175,55,.12) 1px, transparent 1px);
  background-size: 40px 40px;
  transform: perspective(300px) rotateX(75deg) scaleX(1.6);
  transform-origin: bottom center;
  opacity: 0.6;
}
.gp-turntable {
  position: relative;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 2;
  margin-bottom: 36px;
}
.gp-car-wrap {
  width: 82%;
  max-width: 400px;
  animation: gpShowcase 5s ease-in-out infinite alternate;
  filter: drop-shadow(0 8px 20px rgba(0,0,0,.7));
  display: flex;
  align-items: center;
  justify-content: center;
}
@keyframes gpShowcase {
  0%   { transform: perspective(900px) rotateY(-18deg) scale(1.0); }
  30%  { transform: perspective(900px) rotateY(-5deg)  scale(1.02); }
  70%  { transform: perspective(900px) rotateY(8deg)   scale(1.02); }
  100% { transform: perspective(900px) rotateY(20deg)  scale(1.0); }
}
.gp-reflection {
  width: 82%;
  max-width: 400px;
  transform: scaleY(-0.22) translateY(-4px);
  transform-origin: top center;
  opacity: 0.18;
  filter: blur(2px);
  margin-top: -10px;
  animation: gpShowcaseRef 5s ease-in-out infinite alternate;
  pointer-events: none;
}
@keyframes gpShowcaseRef {
  0%   { transform: scaleY(-0.22) translateY(-4px) perspective(900px) rotateY(-18deg); }
  30%  { transform: scaleY(-0.22) translateY(-4px) perspective(900px) rotateY(-5deg); }
  70%  { transform: scaleY(-0.22) translateY(-4px) perspective(900px) rotateY(8deg); }
  100% { transform: scaleY(-0.22) translateY(-4px) perspective(900px) rotateY(20deg); }
}
@keyframes gpFloat {
  0%   { transform: translateY(0px)   scale(1.04); }
  50%  { transform: translateY(-10px) scale(1.04); }
  100% { transform: translateY(0px)   scale(1.04); }
}
@keyframes gpFloatRef {
  0%   { transform: scaleY(-0.22) translateY(-4px); }
  50%  { transform: scaleY(-0.22) translateY(-14px); }
  100% { transform: scaleY(-0.22) translateY(-4px); }
}
.gp-car-wrap.has-photo {
  animation: gpFloat 4s ease-in-out infinite;
  height: 155px;
}
.gp-reflection.has-photo {
  animation: gpFloatRef 4s ease-in-out infinite;
}
.gp-label-bar {
  position: absolute;
  bottom: 0;
  left: 0; right: 0;
  background: linear-gradient(to top, rgba(0,0,0,.85), transparent);
  padding: 20px 16px 10px;
  text-align: center;
  z-index: 3;
}
.gp-label-brand {
  display: block;
  font-family: 'Orbitron', monospace, sans-serif;
  font-size: 15px;
  font-weight: 800;
  color: var(--gold, #D4AF37);
  letter-spacing: 3px;
  text-transform: uppercase;
  transition: all .5s ease;
}
.gp-label-sub {
  display: block;
  font-size: 11px;
  color: rgba(255,255,255,.4);
  margin-top: 2px;
  letter-spacing: 1px;
  transition: all .5s ease;
}
@media(max-width: 900px) {
  .gp-stage { height: 220px; }
  .gp-car-wrap, .gp-reflection { width: 90%; }
  .gp-turntable { margin-bottom: 30px; }
  .gp-car-wrap.has-photo { height: 125px; }
}
@media(max-width: 600px) {
  .gp-stage { height: 190px; }
  .gp-label-brand { font-size: 12px; }
  .gp-car-wrap.has-photo { height: 105px; }
}
`;

  // ── Foto real no lugar do SVG ────────────────────────────────────────────
  function htmlFotoReal(url) {
    return `<img src="${url}" alt="Foto do veículo"
      style="width:100%;height:100%;object-fit:contain;object-position:center bottom;
             display:block;filter:drop-shadow(0 8px 24px rgba(0,0,0,.8))">`;
  }

  function definirVisualizacao(carWrap, refWrap, url, hex) {
    if (url) {
      if (carWrap) {
        carWrap.innerHTML = htmlFotoReal(url);
        carWrap.classList.add('has-photo');
      }
      if (refWrap) {
        refWrap.innerHTML = htmlFotoReal(url);
        refWrap.classList.add('has-photo');
        refWrap.style.opacity = '0.12';
        refWrap.style.filter  = 'blur(3px)';
      }
    } else {
      if (carWrap) {
        carWrap.innerHTML = gerarCarSVG(hex);
        carWrap.classList.remove('has-photo');
      }
      if (refWrap) {
        refWrap.innerHTML = gerarCarSVG(hex);
        refWrap.classList.remove('has-photo');
        refWrap.style.opacity = '';
        refWrap.style.filter  = '';
      }
    }
  }

  // ── Init ─────────────────────────────────────────────────────────────────
  function init() {
    const el = document.getElementById('garage-preview');
    if (!el) return;

    // injeta CSS
    const style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    // injeta HTML
    el.innerHTML = gerarGaragem();

    // observa campos do formulário
    const campos = {
      marca: document.getElementById('marca'),
      modelo: document.getElementById('modelo'),
      ano: document.getElementById('ano'),
      cor: document.getElementById('cor'),
    };

    // URL da foto já salva (injetada pelo template)
    let capaAtual = (window.GARAGE_CAPA_URL || '').trim();

    function atualizar() {
      const marca = campos.marca ? campos.marca.value.trim() : '';
      const modelo = campos.modelo ? campos.modelo.value.trim() : '';
      const ano = campos.ano ? campos.ano.value.trim() : '';
      const cor = campos.cor ? campos.cor.value.trim() : '';

      // Atualiza label
      const label = document.getElementById('gp-label');
      const sub = document.getElementById('gp-sub');
      if (label) {
        if (marca || modelo) {
          label.textContent = ([marca, modelo].filter(Boolean).join(' ')).toUpperCase();
        } else {
          label.textContent = 'ΛUTOVIU';
        }
      }
      if (sub) {
        sub.textContent = ano ? `${ano} · Gestão Automotiva` : 'Gestão Automotiva';
      }

      // Foto real ou SVG com cor
      const hex = resolverCor(cor);
      const carWrap = document.getElementById('gp-car-wrap');
      const refWrap = document.getElementById('gp-reflection');
      definirVisualizacao(carWrap, refWrap, capaAtual, hex);
    }

    // Escuta mudanças em todos os campos relevantes
    Object.values(campos).forEach(function (inp) {
      if (!inp) return;
      inp.addEventListener('input', atualizar);
      inp.addEventListener('change', atualizar);
    });

    // Preview ao selecionar nova foto (antes do upload)
    const inputFoto = document.getElementById('foto_capa');
    if (inputFoto) {
      inputFoto.addEventListener('change', function () {
        const file = this.files && this.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function (e) {
          capaAtual = e.target.result;
          atualizar();
          // atualiza o box de preview ao lado do upload
          const previewBox = document.getElementById('upload-capa-preview-box');
          if (previewBox) {
            let img = previewBox.querySelector('img');
            if (!img) {
              previewBox.innerHTML = '';
              img = document.createElement('img');
              previewBox.appendChild(img);
            }
            img.src = e.target.result;
            img.alt = 'Pré-visualização';
            const labelBtn = document.getElementById('upload-capa-label-btn');
            if (labelBtn) {
              Array.from(labelBtn.childNodes).forEach(function(n) {
                if (n.nodeType === Node.TEXT_NODE && n.textContent.trim()) {
                  n.textContent = ' Trocar foto';
                }
              });
            }
          }
          // indica que há foto pendente de save
          const hint = document.querySelector('.upload-capa-hint');
          if (hint) {
            hint.textContent = 'Foto selecionada — clique em Salvar para confirmar.';
            hint.style.color = '#D4AF37';
          }
        };
        reader.readAsDataURL(file);
      });
    }

    // Roda com os valores iniciais (edição de veículo existente)
    atualizar();
  }

  // Aguarda DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
