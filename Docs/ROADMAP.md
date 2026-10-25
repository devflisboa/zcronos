# zCronos — Roadmap SaaS

> Prioridades de desenvolvimento por fase. Ordem baseada em impacto e risco.  
> Data: 2026-10-23 | Versão: 1.0

---

## Visão geral

```
Fase 0 — Segurança imediata      (prioridade: CRÍTICA — fazer antes de qualquer cliente)
Fase 1 — Multi-tenant            (habilita múltiplos usuários)
Fase 2 — Múltiplos veículos      (habilita valor real do produto)
Fase 3 — Monetização             (habilita receita)
Fase 4 — Telemetria OBD-II       (diferencial competitivo)
Fase 5 — IA e preditivo          (produto premium)
Fase 6 — Mobile app              (crescimento)
```

---

## Acompanhamento local — Fases 1, 2 e 3 (24/10/2026)

**Implantação local:** aplicação construída e iniciada pelo `docker-compose.local.yml`; MySQL local atualizado até a004 após backup e auditoria, preservando as contagens verificadas. Procedimento e evidências em [DOCKER_LOCAL.md](DOCKER_LOCAL.md); índice geral no `README.md`. Produção permanece sem alteração. Referências anteriores a migrações não executadas descrevem o estado daquela implementação; o registro operacional mais recente distingue a aplicação local da homologação/produção ainda pendentes.

O estado histórico e os checklists originais abaixo são referências de escopo. A implementação local atual está detalhada em `FASE3_ROADMAP.md`, inclusive os complementos de isolamento e recuperação de senha das Fases 1 e 2. Por orientação do usuário, a execução dos testes restantes foi transferida para depois da conclusão das implementações dessas três fases. Não considerar esta atualização como aprovação de produção, comprovação de migração dos dados reais ou confirmação de pagamento real.

| Fase | Implementação local | Pendências antes de encerrar a entrega |
|---|---|---|
| 1 | Cadastro, confirmação, recuperação de senha, isolamento de relatórios/alterações, vínculos obrigatórios e auditoria | Configurar SMTP, backup e auditoria dos dados reais, aplicar migrações em homologação e validar isolamento na etapa final |
| 2 | Gestão de múltiplos veículos, veículo ativo, validação de placas/documentos, limites por plano, seed só de categorias e consulta FIPE do veículo próprio ou avulsa | Aplicar a migração a004 em homologação; validar FIPE, concorrência, alternância e dados migrados na etapa final |
| 3 | Assinaturas Asaas, faturas, webhook, trial, planos, proteção de recursos pagos, administração; perfil, OCR, galeria, Google, push e passkeys conforme roadmap detalhado | Decisão comercial Frota e vínculo Google, credenciais dos provedores, homologação de cobrança/autenticação/envios e validação final |

Fases 4, 5 e 6 estão fora desta entrega, conforme delimitação expressa do usuário. Não criar o serviço OBD/FastAPI nem iniciar IA preditiva nesta execução.

Complementos operacionais preparados em `FASE3_ROADMAP.md`: formulários de manutenção preservam campos com JavaScript em caso de falha, conferem o veículo exibido e evitam reenvio automático de resultado incerto; o comando `configuracao-diagnosticar` lista presença/formato e pendências sem exibir valores de segredos nem contatar provedores. Configuração comercial Frota inválida mantém a venda desabilitada. Esses complementos ainda não foram executados/validados; o diagnóstico não substitui homologação.

---

## Fase 0 — Segurança imediata
**Objetivo:** Proteger os dados antes de abrir para outros usuários.  
**Estimativa:** 1 semana de desenvolvimento  
**Status do app atual:** Em produção sem autenticação — dados públicos

### Tarefas

- [ ] **0.1** — Adicionar `Flask-WTF` e ativar CSRF em todos os forms
- [ ] **0.2** — Adicionar autenticação básica via `Flask-Login` com login/logout
- [ ] **0.3** — Adicionar `@login_required` em todas as rotas existentes
- [ ] **0.4** — Criar conta única do Felipe com senha forte via script
- [ ] **0.5** — Adicionar `Flask-Limiter` com rate limit de 10 req/min nas rotas de login
- [ ] **0.6** — Configurar cookies seguros: `SESSION_COOKIE_SECURE`, `HTTPONLY`, `SAMESITE`
- [ ] **0.7** — Remover SECRET_KEY padrão fraca do `config.py`
- [ ] **0.8** — Fazer backup do banco antes de qualquer alteração
- [ ] **0.9** — Instalar Alembic e remover `_run_migrations()` manual do `app.py`

### Entrega da Fase 0

- App protegido por login (pelo menos para o dono)
- CSRF ativo em todos os forms
- Cookies seguros
- Zero exposição pública de dados privados

---

## Fase 1 — Multi-tenant (múltiplos usuários)
**Objetivo:** Permitir que outras pessoas criem contas e usem o app com dados isolados.  
**Estimativa:** 2 semanas de desenvolvimento  
**Depende de:** Fase 0

### Tarefas

- [ ] **1.1** — Criar modelo `User` (email, password_hash, nome, plano, status)
- [ ] **1.2** — Criar script Alembic de migração (adicionar `user_id` ao Veiculo, `veiculo_id` às tabelas transacionais)
- [ ] **1.3** — Criar blueprint `auth` (login, registro, logout, confirmação de e-mail)
- [ ] **1.4** — Templates: `login.html`, `registro.html`, `recuperar_senha.html`
- [ ] **1.5** — Atualizar todas as queries nos services para filtrar por `current_user.id`
- [ ] **1.6** — Verificar propriedade em DELETE/UPDATE (comparar `user_id` antes de alterar)
- [ ] **1.7** — Configurar envio de e-mail transacional (confirmação de conta, reset de senha)
- [ ] **1.8** — Criar testes de isolamento: usuário A não acessa dados do usuário B
- [ ] **1.9** — Migrar dados do Felipe para o novo schema sem perda

### Entrega da Fase 1

- Cadastro e login funcionando
- Dados completamente isolados por usuário
- Confirmação de e-mail implementada
- Testes automatizados de isolamento passando

---

## Fase 2 — Múltiplos veículos
**Objetivo:** Sair do Fiat Cronos fixo e suportar qualquer veículo.  
**Estimativa:** 1 semana de desenvolvimento  
**Depende de:** Fase 1

### Tarefas

- [ ] **2.1** — Criar blueprint `veiculo` (listar, cadastrar, editar, selecionar ativo, desativar)
- [ ] **2.2** — Atualizar dashboard para trabalhar com `veiculo_ativo` da sessão
- [ ] **2.3** — Remover seed hardcoded do Fiat Cronos do `app.py`
- [ ] **2.4** — Criar tela de seleção de veículo ativo (select no header ou página dedicada)
- [ ] **2.5** — Adicionar verificação de limite de veículos por plano
- [ ] **2.6** — Adaptar `_seed()` para criar apenas as categorias globais (manter seed de categorias)
- [ ] **2.7** — Implementar consulta à Tabela FIPE para responder “Quanto meu carro está valendo?” e “Quanto o carro Y está valendo?”, usando o veículo ativo ou uma busca avulsa por marca/modelo/versão/ano/combustível.

### 2.7 — Quanto o veículo está valendo? (Tabela FIPE)

**Solicitação do usuário:** a funcionalidade precisa responder às perguntas “Quanto meu carro está valendo?” e “Quanto aquele carro Y está valendo?”. Esta tarefa detalha a integração FIPE já prevista nesta documentação e em `ARQUITETURA_SAAS.md`; não é um módulo paralelo de avaliação.

**Caso 1 — Meu carro:**
- Identificar o veículo ativo da sessão, verificando a propriedade pelo usuário autenticado.
- Reaproveitar marca, modelo e ano do cadastro e os campos revisados após a leitura do CRLV.
- Se já houver identificação FIPE confirmada, usá-la. Caso contrário, solicitar a versão, ano modelo e combustível necessários para identificar o registro correto; não escolher automaticamente entre versões parecidas.
- Apresentar uma resposta direta: “O valor de referência FIPE do seu {veículo/versão}, ano modelo {ano}, {combustível}, é {valor}, referente a {mês/ano}.”
- Oferecer atualizar o valor estimado do cadastro somente após confirmação; preservar o valor manual até essa confirmação.

**Caso 2 — Outro carro:**
- Permitir a pergunta ou busca “Quanto o carro Y está valendo?”, mesmo que o veículo não esteja cadastrado na conta.
- Identificar marca/modelo e pedir os dados que faltarem: versão, ano modelo e combustível. Havendo mais de uma correspondência, mostrar opções para o usuário selecionar.
- Consultar e apresentar o mesmo conjunto de informações do caso anterior, sem criar um veículo nem alterar o veículo ativo.

**Resposta e interface:**
- Mostrar marca, modelo/versão, ano modelo, combustível, valor em reais, código FIPE, mês/ano de referência, fonte e data da consulta.
- Disponibilizar ações visíveis “Quanto vale meu carro?” e “Consultar outro veículo”, além de reconhecer as duas intenções quando recebidas como pergunta. A solução para reconhecer perguntas deve respeitar a arquitetura existente; não presumir necessidade de uma nova integração de IA.
- Identificar o resultado como valor de referência FIPE, distinguindo-o do valor de compra e do preço de venda informado pelo usuário.
- Tratar ausência de veículo ativo, cadastro incompleto, versão ambígua, resultado não encontrado, dados desatualizados e indisponibilidade do provedor. Não fabricar preços nem substituir uma referência antiga por uma suposta cotação atual.
- Usar backend/serviço Flask existente para consultar o provedor, com timeout, cache por identificação/referência e isolamento dos dados da conta. Provedor, condições de uso, limites e eventual necessidade de credenciais devem ser verificados antes da implementação.
- Prever os campos de identificação FIPE e referência necessários em migração incremental, sem remover nem reinterpretar os valores atuais do cadastro.

**Critérios de entrega:** as duas perguntas precisam resultar em uma cotação identificada ou em uma solicitação clara dos dados faltantes; nunca apenas em uma tabela de marcas sem conduzir à resposta. Consulta avulsa não cadastra veículo; atualização do veículo próprio exige confirmação. Validação funcional e de integração fica na etapa final, conforme orientação do usuário.

**Status:** implementado no código local em 24/10/2026, com validação pendente. Tela autenticada `/fipe/`, serviço de catálogo/cotação no backend, cache e confirmação separada para o cadastro. Migração incremental `a004_fipe.py` preparada, ainda não executada. Nenhum valor real foi consultado e nenhum teste foi executado nesta atualização. Detalhes e limitações em `FASE3_ROADMAP.md`, seção “Consulta FIPE”. O checklist permanece aberto até a validação final.

### Entrega da Fase 2

- Usuário pode cadastrar N veículos (limitado pelo plano)
- Dashboard mostra dados do veículo selecionado
- Alternância entre veículos sem perder contexto
- Consulta FIPE do veículo ativo e de outro veículo, com valor e referência identificados

---

## Fase 3 — Monetização
**Objetivo:** Gerar receita recorrente.  
**Estimativa:** 2-3 semanas de desenvolvimento  
**Depende de:** Fase 1 e 2

### Tarefas

- [ ] **3.1** — Criar modelo `Assinatura` (user_id, plano, status, datas, gateway_id)
- [ ] **3.2** — Integrar gateway de pagamento (Asaas recomendado para Brasil — PIX + boleto + cartão)
- [ ] **3.3** — Criar blueprint `assinatura` (planos, checkout, histórico de faturas)
- [ ] **3.4** — Implementar webhook do gateway (atualizar plano ao confirmar pagamento)
- [ ] **3.5** — Criar tela de upgrade de plano com comparação de features
- [ ] **3.6** — Implementar período de trial de 14 dias para novos cadastros
- [ ] **3.7** — Suspender acesso ao expirar assinatura (bloquear rotas, não deletar dados)
- [ ] **3.8** — Criar painel admin básico (listar usuários, planos, receita mensal)

### Planos

| Plano | Preço | Veículos | Recursos |
|---|---|---|---|
| Gratuito | R$ 0 | 1 | Básico (abastecimento, despesas, manutenção) |
| Pro | R$ 14,90/mês | 3 | + relatórios, export CSV, alertas por e-mail |
| Frota | R$ 49,90/mês | 15 | + gestão de equipe, relatórios de frota, API |

> Valores sugeridos — validar com clientes antes de fixar.

### Entrega da Fase 3

- Checkout e cobrança recorrente funcionando
- Upgrade/downgrade de plano
- Trial automático
- Painel admin básico

---

## Fase 4 — Telemetria OBD-II
**Objetivo:** Diferencial competitivo — dados reais do carro em tempo real.  
**Estimativa:** 3-4 semanas de desenvolvimento  
**Depende de:** Fase 1 (multi-tenant) — features pagas (Pro e Frota)  
**Documento detalhado:** `MODULO_TELEMETRIA_OBD.md`

### Tarefas macro

- [ ] **4.1** — Backend: criar API REST para receber telemetria (endpoint autenticado por token de dispositivo)
- [ ] **4.2** — Backend: criar tabela `telemetria_obd`, serviço de armazenamento e agregação
- [ ] **4.3** — Frontend: painel de telemetria real-time (gauges de RPM/velocidade/temp, gráficos históricos)
- [ ] **4.4** — Agente Android: app ou script que lê do ELM327 via Bluetooth e posta na API
- [ ] **4.5** — Primeiro simulador de dados (sem hardware) para testes e demo

### Entrega da Fase 4

- Painel de gauges em tempo real
- Histórico de sensores com gráficos
- App Android (alpha) postando dados reais
- Detecção e explicação de códigos DTC em português

---

## Fase 5 — IA e preditivo
**Objetivo:** Produto premium com inteligência para prevenir falhas.  
**Estimativa:** 4-6 semanas de desenvolvimento  
**Depende de:** Fase 4 (histórico de telemetria acumulado)

### Tarefas macro

- [ ] **5.1** — Detecção de anomalias em séries temporais de RPM e temperatura
- [ ] **5.2** — Correlação entre DTC históricos e padrões de direção
- [ ] **5.3** — Manutenção preditiva baseada em km real + telemetria
- [ ] **5.4** — Explicação de códigos de falha via LLM (Claude API ou local)
- [ ] **5.5** — Alertas proativos via Telegram / e-mail

---

## Fase 6 — Mobile app
**Objetivo:** Aquisição de usuários e experiência mobile-first.  
**Estimativa:** 8-12 semanas  
**Depende de:** Fase 3 (API REST estável)

### Opções de stack mobile

| Opção | Vantagem | Custo |
|---|---|---|
| PWA (Progressive Web App) | Sem loja de apps, custo zero | Funcionalidades limitadas |
| Flutter | Cross-platform iOS + Android | Curva de aprendizado |
| React Native | Compartilha lógica com web | Requer JS frontend |
| App nativo Android (Kotlin) | Acesso direto ao Bluetooth | Apenas Android |

> Recomendação inicial: **PWA** como primeiro passo (adicionar `manifest.json` e Service Worker ao Flask app existente) antes de investir em app nativo.

---

## Integrações externas por fase

| Integração | Fase | Finalidade |
|---|---|---|
| `SendGrid / Resend` | Fase 1 | E-mail transacional |
| `Asaas` | Fase 3 | Cobrança recorrente (PIX/boleto/cartão) |
| `FIPE API` | Fase 2 | Valor de mercado do veículo |
| `ANP preço combustível` | Fase 2 | Comparar preço do abastecimento com média regional |
| `ViaCEP` | Fase 2 | Autocompletar localização do posto |
| `Telegram Bot API` | Fase 4 | Alertas OBD e manutenção (via Alfred se for uso pessoal) |
| `Claude API` | Fase 5 | Explicação de DTCs, análise de padrões |

---

## Métricas de sucesso por fase

| Fase | Métrica |
|---|---|
| 0 — Segurança | Zero dados expostos publicamente |
| 1 — Multi-tenant | 3 usuários beta sem cruzamento de dados |
| 2 — Veículos | 1 usuário com 2+ veículos gerenciados |
| 3 — Monetização | Primeiro pagamento recorrente processado |
| 4 — OBD-II | Dados reais de 1 veículo sendo coletados e exibidos |
| 5 — IA | 1 alerta preditivo correto gerado antes de falha |

---

## O que NÃO está no roadmap (decisões deliberadas)

- **PostgreSQL agora**: MySQL 8.0 é suficiente. Migrar só se houver gargalo real.
- **Microsserviços agora**: monolito Flask bem estruturado é mais fácil de operar no início.
- **iOS app agora**: Android primeiro (onde ELM327 Bluetooth tem melhor suporte).
- **Android Auto sem fio agora**: requer hardware adicional (ver `CLAUDE_Cronos_Auto_Connect.md`).
- **Multi-tenant por schema separado**: complexidade operacional alta para o volume esperado.
