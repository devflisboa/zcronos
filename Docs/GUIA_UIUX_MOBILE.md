# Guia de UI/UX Mobile — AUTOVIU

Padrão obrigatório para desenvolvimento de qualquer tela ou componente mobile do AUTOVIU.
Baseado em Material Design 3, Apple HIG e WCAG 2.2.

---

## 1. Tamanhos de Componentes

| Componente | Tamanho recomendado |
|---|---|
| Botão principal | 48–56 dp/pt de altura |
| Botão secundário | 44–48 dp/pt de altura |
| Área de toque de ícone | 48×48 dp (Android) / 44×44 pt (iOS) |
| Ícone interno do botão | 20–24 |
| Campo de formulário | 48–56 de altura |
| Barra superior (topbar) | ~56 |
| Margem lateral | 16–24 |
| Espaçamento entre campos | 12–16 |
| Espaçamento entre seções | 24–32 |
| Border-radius botões | 8–16 |
| Border-radius cards | 12–16 |

---

## 2. Hierarquia de Botões

- **Apenas 1 ação primária por tela ou contexto.**
- 1 ação secundária ao lado ou abaixo da principal (no máximo).
- Ações menos utilizadas → menus contextuais ou telas de detalhe.
- Ações destrutivas (excluir) devem ter destaque visual diferente e confirmação obrigatória.
- Nunca colocar ações destrutivas próximas de ações frequentes ou bordas de gesto do sistema.

---

## 3. Tipografia

| Elemento | Tamanho |
|---|---|
| Título principal | 24–28 |
| Título de seção | 18–20 |
| Subtítulo | 16–18 |
| Texto comum | 16 |
| Texto de botão | 14–16 |
| Label de formulário | 14 |
| Texto auxiliar / erro | 12–14 |

- Fonte preferencial: **Inter** (multiplataforma) — ou Roboto (Android) / SF Pro (iOS).
- `Orbitron` apenas para valores KPI e elementos premium do AUTOVIU.
- Altura de linha: 1.4–1.6× o tamanho da fonte.
- Nunca fixar tamanho que impeça ampliação das configurações de acessibilidade do dispositivo.

---

## 4. Escala de Espaçamento (múltiplos de 4)

| Valor | Uso |
|---|---|
| 4 | Espaço mínimo entre ícone e texto |
| 8 | Itens relacionados |
| 12 | Componentes |
| 16 | Campos e margens laterais |
| 24 | Entre seções |
| 32 | Grandes blocos |

Regras:
- Alinhar títulos, campos, cards e botões à mesma margem lateral.
- Não preencher todos os espaços vazios com elementos.
- Preferir alinhamento à esquerda para textos longos.

---

## 5. Posicionamento dos Elementos

1. **Topo**: identificação da tela, botão voltar, ações contextuais.
2. **Centro**: conteúdo principal e campos de trabalho.
3. **Parte inferior**: ação principal (quando faz sentido mantê-la acessível).
4. **Navegação inferior**: destinos principais (3–5 itens) — nunca ações temporárias.

---

## 6. Navegação

- **3 a 5 destinos** na navegação inferior.
- Manter navegação consistente entre todas as telas.
- Não usar menus excessivamente complexos.
- Disponibilizar voltar, cancelar e confirmar de forma previsível.

---

## 7. Formulários

- **Labels permanentes** (nunca só placeholder).
- Campos com altura preferencial de 48–56.
- Teclado adequado para cada tipo de entrada (numérico, e-mail, texto).
- Validar e mostrar mensagens próximas ao campo com problema.
- **Preservar dados** após falhas de conexão.
- Dividir formulários longos em etapas com indicador de progresso.
- Nunca ocultar botões ou campos essenciais atrás do teclado virtual.

---

## 8. Cores e Acessibilidade (WCAG 2.2 AA)

| Cor semântica | Aplicação |
|---|---|
| **Gold #D4AF37** | Ações principais, elementos selecionados (AUTOVIU primary) |
| **Neutro #111116** | Fundos, superfícies |
| **#34C759** | Sucesso, conclusão |
| **#FF9F0A** | Atenção, alertas não críticos |
| **#FF3B30** | Erro, exclusão, ações perigosas |
| **#8a9099** | Informações e elementos secundários |

Requisitos:
- Contraste ≥ 4,5:1 para textos normais.
- Contraste ≥ 3:1 para textos grandes e elementos de UI.
- **Nunca usar só cor** para representar estados — sempre adicionar ícone ou texto.
- Áreas de toque mínimas: 48×48 dp / 44×44 pt.
- Suporte a leitores de tela (acessibilidade).

---

## 9. Estados Obrigatórios de Componentes

Todo botão e campo precisa ter estados:
- **Normal**
- **Pressed/Active**
- **Disabled**
- **Loading** (quando aplicável)
- **Error** (para campos)

Toda tela precisa prever:
- Carregamento (skeleton ou spinner)
- Lista vazia (empty state)
- Falha de conexão
- Erro de validação
- Confirmação de sucesso

---

## 10. Checklist de Aprovação (por tela)

- [ ] A tela possui um objetivo principal claro
- [ ] Botões têm áreas de toque adequadas (≥44pt/48dp)
- [ ] Tipografia é legível e ajustável
- [ ] Espaçamentos seguem a escala de 4 pontos
- [ ] Existe apenas uma ação primária por contexto
- [ ] Todos os campos possuem label visível
- [ ] Layout se adapta a celulares pequenos e grandes
- [ ] Layout respeita safe areas e barra de sistema
- [ ] Tratamento para erros, carregamento e listas vazias
- [ ] Navegação funciona com teclado aberto
- [ ] Cores e contrastes atendem à acessibilidade
- [ ] Testado em diferentes tamanhos de tela

---

## 11. Prompt Padrão para IA de Desenvolvimento

Usar no início de qualquer sessão de desenvolvimento de UI mobile:

```
Atue como Senior Product Designer e Senior Mobile Engineer especializado em Material Design 3,
Apple HIG, WCAG 2.2 e Design Systems.

REGRAS OBRIGATÓRIAS:
- Botões principais: altura 48–56dp/pt; 1 ação primária por contexto
- Tipografia: título 24–28, corpo 16, label 14, auxiliar 12–14
- Espaçamento: escala 4/8/12/16/24/32; margens laterais 16–24
- Navegação: 3–5 destinos na barra inferior
- Formulários: labels permanentes, campos 48–56, preservar dados
- Acessibilidade: WCAG 2.2 AA, contraste ≥4.5:1, não usar só cor para estados
- Todo componente deve ter estados: normal, pressed, disabled, loading
- Toda tela deve prever: loading, empty state, erro, sucesso

Não aprovar nenhuma tela sem passar pelo checklist de 12 itens.
```

---

## Referências Oficiais

- [Material Design 3](https://m3.material.io/)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
