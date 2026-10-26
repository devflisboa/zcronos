# ΛUTOVIU — Progresso da Sessão Autônoma

## Commits realizados

| Commit | Descrição |
|---|---|
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

## Testes Cypress
- Baseline: 167/167 passando (master)
- **Último run: 173/173 ✅** (dev, 26/10/2026, pós-commit bdff110)
- Causa de falhas anteriores: servidor E2E com DEBUG=False cacheia templates; resolver com restart

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

## Backlog pendente (Fase 2)
- [ ] Relatório: exportar PDF por veículo com filtro avançado (período + categorias)
- [ ] Dashboard: widget de previsão de gastos (baseado em média mensal)
- [ ] Notificações push (PWA) para alertas de manutenção
- [ ] Compartilhamento de veículo entre usuários (multi-condutor)
