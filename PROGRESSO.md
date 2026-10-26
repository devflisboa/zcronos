# ΛUTOVIU — Progresso da Sessão Autônoma

## Commits realizados

| Commit | Descrição |
|---|---|
| `f117e7c` | **Push notifications PWA** — VAPID keys, sw.js v6, payload rico, alerta_service enriquecido (Cypress 173/173) |
| `f87b408` | **Fix regressão sidebar** — placa Mercosul sempre visível, fallback `———` quando sem placa (Cypress 173/173) |
| `38a4408` | geolocalização, placa mask, email HTML, OG tags |
| `0a24b90` | animação garagem 3D no form de veículo |
| `1508018` | mapa de abastecimentos Leaflet.js + tipo_combustivel |
| `8465460` | badge alertas no menu, KPIs histórico/consumo, CSV com filtro de período, migration auto-run |
| `49bd171` | redesign de alertas, edição de abastecimento e despesa |
| `afd1702` | odômetro inteligente — previsão de manutenção por ritmo de km |
| `275f83a` | gráfico de evolução de consumo (km/L) na aba Combustível |
| `be9cec5` | km_atual auto-atualizado ao registrar abastecimento/despesa + forma_pagamento no cadastro |
| `1fd73f7` | Cypress 172/172 — edição de abastecimento/despesa, isolamento e fix responsividade |
| `71038e7` | edição de manutenção via modal + botão editar na tabela |
| `47df64d` | filtro de período (mês/ano) nos KPIs do dashboard |
| `8e9528a` | botão Imprimir/PDF na página de relatórios (window.print() + CSS de impressão) |
| `bdff110` | modal de abastecimento com tipo_combustivel, observacao e csrf_token |
| `4df1563` | gráfico preço médio/L por mês + auto-calc valor total no modal de abastecimento |
| `74c2570` | busca nas tabelas, projeção anual, autocomplete de postos, data padrão=hoje, km padrão modal despesa |
| `57fcdd6` | busca na tabela manutenção, projeção anual na análise, SW v5, shortcut relatórios no PWA |
| `0a0f3dd` | PROGRESSO.md — 16 commits, 173/173 Cypress, 28 features entregues |
| `dd63d89` | **Metas de Gasto** — MetaGasto model, blueprint /meta, meta_service, UI com barras de progresso (Cypress 173/173) |
| `9433b6f` | **MERGE master** — dev/garage-animation-e-melhorias → master (deploy 26/10/2026) |

## Deploy
- **26/10/2026** — 3 deploys consecutivos em master (todas com rebuild da imagem)
  - `9433b6f` — MERGE dev/garage-animation-e-melhorias (deploy inicial)
  - `f117e7c` — Push notifications PWA
  - `f87b408` — Fix regressão placa Mercosul
- Servidor: `casakek.duckdns.org:64622` · path `/home/felipe/sistemas/zCronos/zcronos`
- Rebuild obrigatório: `docker-compose build web` + `docker rm -f` + `up -d --no-deps web`
- URL produção: `zcronos.duckdns.org` · HTTP 200 confirmado após cada deploy

## Testes Cypress
- Baseline: 167/167 passando (master)
- **Último run: 173/173 ✅** (commit f87b408, 26/10/2026)
- Causa de falhas anteriores: servidor E2E com DEBUG=False cacheia templates; resolver com restart do serve_cypress.py

## Funcionalidades entregues
| Feature | Status | Commit |
|---|---|---|
| Geolocalização (abastecimento + despesa) | ✅ em master | 38a4408 |
| Máscara de placa JS | ✅ em master | 38a4408 |
| Email HTML dark-theme | ✅ em master | 38a4408 |
| Open Graph tags | ✅ em master | 38a4408 |
| Animação garagem 3D | ✅ em dev | 0a24b90 |
| Mapa de abastecimentos (Leaflet.js) | ✅ em dev | 1508018 |
| Badge alertas urgentes no menu | ✅ em dev | 8465460 |
| KPIs: Histórico / Consumo / Preço/L / Último abast. | ✅ em dev | 8465460 |
| CSV com filtro de período (de/até) | ✅ em dev | 8465460 |
| Migration auto-run no startup Docker | ✅ em dev | 8465460 |
| Redesign alertas (cards coloridos + painel preferências) | ✅ em dev | 49bd171 |
| Edição de abastecimento (GET/POST /abastecimento/editar/<id>) | ✅ em dev | 49bd171 |
| Edição de despesa (GET/POST /despesa/editar/<id>) | ✅ em dev | 49bd171 |
| Botão de editar na tabela de abastecimentos e despesas | ✅ em dev | 49bd171 |
| Odômetro inteligente (previsão por ritmo de km/dia) | ✅ em dev | afd1702 |
| Gráfico evolução de consumo (km/L) | ✅ em dev | 275f83a |
| km_atual auto-atualizado ao registrar abastecimento/despesa | ✅ em dev | be9cec5 |
| forma_pagamento no cadastro de despesa | ✅ em dev | be9cec5 |
| Edição de manutenção via modal (POST /manutencao/editar/<id>) | ✅ em dev | 71038e7 |
| Filtro de período (mês/ano) nos KPIs do dashboard | ✅ em dev | 47df64d |
| Botão Imprimir/PDF na página de relatórios | ✅ em dev | 8e9528a |
| Modal abastecimento: tipo_combustivel + observacao + csrf_token | ✅ em dev | bdff110 |
| Gráfico preço médio combustível por mês (R$/L) | ✅ em dev | 4df1563 |
| Auto-cálculo valor total no modal (litros × preço/L) | ✅ em dev | 4df1563 |
| Busca rápida nas tabelas (despesas, abastecimentos, manutenções) | ✅ em dev | 74c2570 |
| Projeção de gasto anual no KPI "Custo do Ano" | ✅ em dev | 74c2570 |
| Autocomplete de postos no modal de abastecimento | ✅ em dev | 74c2570 |
| Data padrão = hoje nos modais de abastecimento e despesa | ✅ em dev | 74c2570 |
| Km padrão = atual no modal de despesa | ✅ em dev | 74c2570 |
| Projeção anual destacada na seção Análise | ✅ master | 57fcdd6 |
| Service Worker v5 + shortcut "Relatórios" no PWA | ✅ master | 57fcdd6 |
| **Metas de Gasto** — MetaGasto model + blueprint /meta + service + barras de progresso | ✅ master | dd63d89 |

## Funcionalidades entregues — sessão 26/10/2026 (pós-merge)

| Feature | Status | Commit |
|---|---|---|
| Push notifications PWA — Service Worker v6 payload rico | ✅ master | f117e7c |
| VAPID keys no `.env` + `config.py` decode `\n` | ✅ master | f117e7c |
| `alerta_service.py` envia `title`/`body`/`url`/`tag` real | ✅ master | f117e7c |
| Fix regressão: placa Mercosul sempre visível na sidebar | ✅ master | f87b408 |

## Backlog pendente (Fase 3)
- [ ] **3.2 Registro público** — `/registro` + verificação de e-mail + onboarding (**bloqueador de crescimento**)
- [ ] **3.1 Monetização** — Asaas, planos Free/Pro/Frota, webhook, tela `/plano` (junto com 3.2)
- [ ] **3.7 Google OAuth** — Login social (Authlib + google_id no User) — reduz atrito no cadastro
- [ ] **3.5 Alertas inteligentes** — push automático para CNH/CRLV/revisão/seguro/IPVA (infra push pronta)
- [ ] **3.6 Galeria de fotos** — Upload + lightbox + card social canvas 1080×1080
- [ ] **3.3 Perfil condutor** — campos CNH, modelo Condutor
- [ ] **3.4 Upload CNH/CRLV** — OCR via GPT-4 Vision → preenche formulário auto
- [ ] **3.8 WebAuthn/Passkeys** — login biométrico (digital, Face ID, Windows Hello)
- [ ] Exportar relatório completo com gráficos (screenshot + PDF server-side)
- [ ] Testes Cypress para o blueprint /meta (isolamento: delete 404, add validação)

## Arquitetura resumida
| Camada | Detalhe |
|---|---|
| Backend | Flask + SQLAlchemy + MySQL (prod) / SQLite (E2E) |
| Auth | Flask-Login + bcrypt + CSRF (Flask-WTF) |
| Blueprints | auth, main, abastecimento, despesa, manutencao, veiculo, uber, fipe, relatorio, meta, condutor, documento, galeria, alerta, assinatura |
| Serviços | dashboard_service, meta_service, alerta_service, assinatura_service, veiculo_helper |
| E2E | Cypress 12 · serve_cypress.py porta 5087 · SQLite in-memory · `AUTOVIU_E2E=1` |
| Deploy | Docker · `docker-compose build web` + `docker rm -f` + `up -d --no-deps web` |
| Prod | `zcronos.duckdns.org` · SSH `casakek.duckdns.org:64622` · `/home/felipe/sistemas/zCronos/zcronos` |
