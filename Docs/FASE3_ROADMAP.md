# AUTOVIU — Roadmap Fase 3

**Criado em:** 24/10/2026  
**Status:** Planejamento

---

## Visão Geral

A Fase 3 expande o AUTOVIU de uma ferramenta de gestão pessoal para um SaaS completo com monetização, perfil de condutor e inteligência documental.

---

## 3.1 — Monetização (Asaas)

**Objetivo:** Converter usuários do plano `free` em pagantes.

| Plano | Veículos | Preço |
|---|---|---|
| Free | 1 | R$ 0/mês |
| Pro | 3 | R$ 14,90/mês |
| Frota | Ilimitado | R$ 39,90/mês |

**Implementação:**
- Integração com Asaas (API de cobranças)
- Webhook para atualizar `plano` no banco ao confirmar pagamento
- Tela de upgrade dentro do app (`/plano`)
- Trial de 14 dias para o plano Pro

---

## 3.2 — Cadastro Público (Registro de Usuários)

**Objetivo:** Permitir novos usuários se cadastrarem sem intervenção do superadmin.

**Fluxo:**
1. Tela `/registro` pública com e-mail + senha + nome
2. Verificação por e-mail (token de ativação)
3. Usuário entra no plano `free` automaticamente
4. Onboarding: cadastro do primeiro veículo com OCR opcional

---

## 3.3 — Perfil do Condutor

**Objetivo:** Associar dados do motorista ao veículo.

**Campos:**
- Nome completo, CPF, data de nascimento
- Categoria CNH, número de registro CNH
- Data de validade da CNH
- Alertas automáticos de vencimento (30 dias antes)

**Modelo de dados:**
```python
class Condutor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    nome = db.Column(db.String(120))
    cpf = db.Column(db.String(14))
    cnh_numero = db.Column(db.String(20))
    cnh_categoria = db.Column(db.String(5))      # A, B, AB, C, D, E
    cnh_validade = db.Column(db.Date)
    cnh_primeira_habilitacao = db.Column(db.Date)
```

---

## 3.4 — Upload Inteligente de Documentos (CNH + CRLV)

**Objetivo:** O usuário faz upload da foto/PDF do documento e o app preenche os campos automaticamente via OCR + IA.

### Fluxo do CRLV (Certificado de Registro e Licenciamento de Veículo)

```
Upload CRLV (foto/PDF)
        ↓
OCR + extração via GPT-4 Vision
        ↓
Campos extraídos:
  - Placa
  - Marca / Modelo
  - Ano de fabricação / Ano modelo
  - Cor
  - Chassi
  - Renavam
  - Proprietário
        ↓
Pré-preenche formulário de cadastro do veículo
        ↓
Usuário revisa e confirma
```

### Fluxo da CNH (Carteira Nacional de Habilitação)

```
Upload CNH (foto frente + verso, ou PDF digital)
        ↓
OCR + extração via GPT-4 Vision
        ↓
Campos extraídos:
  - Nome completo
  - CPF
  - Data de nascimento
  - Número de registro
  - Categoria (A, B, AB, C, D, E)
  - Data de validade
  - Data da primeira habilitação
        ↓
Pré-preenche formulário do perfil do condutor
        ↓
Usuário revisa e confirma
```

### Stack técnica

| Componente | Opção Principal | Alternativa |
|---|---|---|
| OCR | GPT-4 Vision (OpenAI API) | Google Cloud Vision |
| Armazenamento temporário | `/tmp` do servidor (apagar após extração) | AWS S3 (criptografado) |
| Formato aceito | JPG, PNG, PDF (até 10 MB) | — |
| Biblioteca PDF | PyMuPDF (`fitz`) | pdf2image + Pillow |

### Endpoint backend

```python
@bp.route('/veiculo/upload-crlv', methods=['POST'])
@login_required
def upload_crlv():
    arquivo = request.files.get('crlv')
    # 1. Salva temporariamente
    # 2. Converte PDF → imagem se necessário
    # 3. Envia para GPT-4 Vision com prompt estruturado
    # 4. Parseia JSON de resposta
    # 5. Deleta arquivo temporário
    # 6. Retorna campos extraídos como JSON
    return jsonify(campos_extraidos)
```

### Prompt para GPT-4 Vision (CRLV)

```
Analise esta imagem de um CRLV (Certificado de Registro e Licenciamento de Veículo) 
brasileiro e extraia os seguintes campos em formato JSON:
{
  "placa": "",
  "marca": "",
  "modelo": "",
  "ano_fabricacao": "",
  "ano_modelo": "",
  "cor": "",
  "chassi": "",
  "renavam": ""
}
Retorne apenas o JSON, sem explicações. Se um campo não estiver visível, use null.
```

### Segurança

- Arquivos deletados do servidor imediatamente após extração (nunca persistidos)
- Não armazenar dados brutos do documento no banco — apenas os campos extraídos
- Validar tipo MIME antes de processar (aceitar apenas image/* e application/pdf)
- Limite de tamanho: 10 MB por upload
- Rate limit: 5 uploads por hora por usuário

### UX no formulário

```
[ Preencher manualmente ]  ou  [ Importar do CRLV ]
                                        ↓
                              [ Selecionar arquivo ]
                                        ↓
                              [  Analisando...  ]  ← spinner
                                        ↓
                              Campos pré-preenchidos
                              (editáveis pelo usuário)
```

---

## 3.5 — Alertas Inteligentes

**Objetivo:** Notificações proativas via e-mail e push notification.

| Alerta | Gatilho |
|---|---|
| CNH próxima do vencimento | 60 e 30 dias antes |
| CRLV vencendo | 30 dias antes do licenciamento |
| Revisão do fabricante | Km atingido (conforme agenda) |
| Seguro vencendo | 30 dias antes |
| IPVA | Aviso em janeiro com valor estimado |

---

## Prioridade de Implementação

```
3.2 Registro público    ← primeiro (sem isso, não há novos usuários)
3.1 Monetização         ← junto com registro
3.3 Perfil do condutor  ← base para 3.4 e 3.5
3.4 Upload CNH/CRLV     ← diferencial competitivo
3.5 Alertas inteligentes ← retenção de usuários
```

---

## Dependências Externas

| Serviço | Uso | Custo estimado |
|---|---|---|
| OpenAI API (GPT-4 Vision) | OCR de documentos | ~R$ 0,50 por upload |
| Asaas | Cobranças e assinaturas | 2,49% por transação |
| SendGrid ou Resend | E-mails transacionais | Free tier até 100/dia |
| Redis (opcional) | Rate limiting, sessões | R$ 50/mês no servidor |
