# zCronos — Módulo de Telemetria OBD-II

> Arquitetura modular e independente dos módulos financeiros/manutenção.  
> Data: 2026-10-23 | Versão: 1.0

---

## 1. Visão geral

O módulo de telemetria coleta dados reais do veículo via adaptador OBD-II Bluetooth (ELM327 ou compatível), envia ao backend por HTTPS e exibe no painel web em tempo real.

**Escopo da v1:** somente leitura de sensores — sem envio de comandos à ECU.

**Operação offline:** dados armazenados localmente no celular quando sem internet, sincronizados ao reconectar.

---

## 2. Compatibilidade de hardware

### Adaptadores suportados (ELM327 e similares)

| Critério | Recomendado | Evitar |
|---|---|---|
| Interface | Bluetooth Classic (SPP/RFCOMM) | Wi-Fi (complexidade de configuração em Android) |
| Chip | ELM327 v1.5 ou superior | Clones OBDLink v2.1+ (firmware fechado) |
| Android | 4.1+ (Jelly Bean) até Android 15 | — |
| Fiat Cronos 2021 | Protocolo ISO 15765-4 CAN | — |

> **Aviso:** compatibilidade varia por veículo e adaptador. Não garantir universalidade.

### Protocolos OBD-II suportados pelo ELM327

| Protocolo | Código AT | Uso comum |
|---|---|---|
| ISO 15765-4 CAN (11/500) | 6 | Veículos pós-2008 (principal) |
| ISO 15765-4 CAN (29/500) | 7 | Veículos GM, Ford |
| ISO 14230-4 KWP (5-baud) | 4 | Veículos mais antigos |
| ISO 9141-2 | 3 | Veículos europeus pré-2008 |
| SAE J1850 VPW/PWM | 1, 2 | Veículos americanos pré-2008 |

---

## 3. PIDs coletados (OBD-II Mode 01)

O agente detecta automaticamente quais PIDs o veículo suporta antes de iniciar coleta.

| PID | Nome | Unidade | Fórmula |
|---|---|---|---|
| 0x0C | RPM motor | rpm | (A×256+B)/4 |
| 0x0D | Velocidade | km/h | A |
| 0x05 | Temperatura líquido arrefecimento | °C | A-40 |
| 0x04 | Carga calculada motor | % | A×100/255 |
| 0x03 | Status sistema combustível | enum | bits A |
| 0x2F | Nível de combustível | % | A×100/255 |
| 0x33 | Pressão barométrica | kPa | A |
| 0x0A | Pressão combustível | kPa | A×3 |
| 0x11 | Posição borboleta | % | A×100/255 |
| 0x0F | Temperatura ar admissão | °C | A-40 |
| 0x10 | Fluxo de massa de ar (MAF) | g/s | (A×256+B)/100 |
| 0x01 | DTCs ativos (Modo 03) | lista | — |

---

## 4. Arquitetura geral

```
┌─────────────────────────────────────────────────────────────────┐
│  Adaptador ELM327 (Bluetooth Classic)                          │
│  Conectado à porta OBD-II (16 pinos, sob painel)               │
└────────────────────────┬────────────────────────────────────────┘
                         │ RFCOMM / Serial BT (SPP)
┌────────────────────────▼────────────────────────────────────────┐
│  AGENTE ANDROID (app Kotlin ou script Python via Termux)        │
│  - Detecta PIDs suportados na inicialização                     │
│  - Coleta dados em intervalos configuráveis (default: 5s)       │
│  - Armazena offline em SQLite via Room                          │
│  - Sincroniza com API quando internet disponível                │
│  - Operação em foreground service (Android 8+)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │ POST HTTPS + Bearer token
┌────────────────────────▼────────────────────────────────────────┐
│  BACKEND (FastAPI — novo serviço, separado do Flask)            │
│  POST /api/v1/telemetria/leitura                                │
│  GET  /api/v1/telemetria/tempo-real/{veiculo_id}                │
│  GET  /api/v1/telemetria/historico/{veiculo_id}                 │
│  GET  /api/v1/telemetria/dtc/{veiculo_id}                       │
└────────────────────────┬────────────────────────────────────────┘
                         │ SQLAlchemy (async)
┌────────────────────────▼────────────────────────────────────────┐
│  MySQL 8.0 (manter stack atual)                                 │
│  Tabela: telemetria_obd                                         │
│  Tabela: dtc_historico                                          │
│  Tabela: dispositivos_obd (autenticação por device)             │
└─────────────────────────────────────────────────────────────────┘
                         │ SSE (Server-Sent Events) ou polling 5s
┌────────────────────────▼────────────────────────────────────────┐
│  FRONTEND (painel web Flask / futura PWA)                       │
│  Gauges: RPM, velocidade, temperatura, carga                    │
│  Gráficos: histórico de 24h, semana, mês                        │
│  Alertas: DTC detectado, temperatura alta, etc.                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Agente Android — especificação técnica

### Stack

- **Linguagem:** Kotlin (app nativo)
- **Bluetooth:** `BluetoothAdapter` + `BluetoothSocket` (RFCOMM/SPP)
- **Localização:** não necessária neste módulo (ver módulo GPS separado)
- **Persistência offline:** Room (SQLite)
- **Sync background:** WorkManager (constraints: network required)
- **Foreground service:** notificação permanente durante coleta ativa

### Permissões necessárias (Android 15)

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE" />
<uses-permission android:name="android.permission.INTERNET" />
```

> No Android 12+, as permissões BLUETOOTH_CONNECT e BLUETOOTH_SCAN substituem as antigas BLUETOOTH/BLUETOOTH_ADMIN.

### Fluxo do agente

```
App inicia
  │
  ▼
Usuário seleciona dispositivo BT (ELM327 já pareado no SO)
  │
  ▼
Conectar via RFCOMM (UUID: 00001101-0000-1000-8000-00805F9B34FB)
  │
  ▼
Enviar "ATZ\r" → aguardar "ELM327"  [reset]
Enviar "ATE0\r"                     [desativar echo]
Enviar "ATL0\r"                     [desativar line feeds]
Enviar "ATS0\r"                     [desativar espaços]
Enviar "ATSP0\r"                    [auto-detectar protocolo]
  │
  ▼
Detectar PIDs suportados (01 00, 01 20, 01 40, 01 60)
Registrar conjunto de PIDs válidos para este veículo
  │
  ▼
Loop de coleta (a cada 5 segundos):
  Para cada PID suportado:
    Enviar "01 XX\r"
    Ler resposta
    Decodificar valor
  
  Montar payload JSON
  Tentar POST à API:
    ✓ Sucesso → continuar
    ✗ Falha → salvar em Room (fila offline)
  │
  ▼
WorkManager verifica fila offline periodicamente
  └── Se internet disponível → flush da fila para API
```

### Payload de telemetria (JSON)

```json
{
  "device_token": "tok_abc123xyz",
  "veiculo_id": 42,
  "timestamp": "2026-10-23T14:30:00-03:00",
  "protocolo_obd": "ISO 15765-4 CAN",
  "leituras": {
    "rpm": 1450,
    "velocidade_kmh": 0,
    "temp_liquido_c": 87,
    "carga_motor_pct": 22,
    "nivel_comb_pct": 63,
    "pressao_bar_kpa": 101,
    "temp_ar_c": 28,
    "posicao_borboleta_pct": 15
  },
  "dtc": []
}
```

---

## 6. Backend FastAPI — especificação

### Novo serviço separado do Flask

O módulo OBD-II será um serviço FastAPI independente, rodando na mesma rede Docker, por alguns motivos:
- FastAPI suporta async nativo (melhor para SSE e múltiplos clients simultâneos)
- Isolamento: falha no módulo OBD não afeta o app principal
- Escala independente

```yaml
# docker-compose.prod.yml — adicionar:
  obd-api:
    build: ./obd_api
    image: zcronos_obd:latest
    restart: unless-stopped
    ports:
      - "5013:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
```

### Autenticação de dispositivo

```python
# Tabela dispositivos_obd
class DispositivoOBD(Base):
    __tablename__ = 'dispositivos_obd'
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    veiculo_id = Column(Integer, ForeignKey('veiculo.id'), nullable=False)
    nome       = Column(String(100))       # ex: "Samsung Galaxy A55 do Felipe"
    device_token = Column(String(64), unique=True, nullable=False)  # gerado no cadastro
    ativo      = Column(Boolean, default=True)
    criado_em  = Column(DateTime, default=datetime.utcnow)
    ultimo_uso = Column(DateTime)

# Dependency FastAPI
async def get_device(
    token: str = Header(alias='X-Device-Token'),
    db: AsyncSession = Depends(get_db)
) -> DispositivoOBD:
    device = await db.execute(
        select(DispositivoOBD).where(
            DispositivoOBD.device_token == token,
            DispositivoOBD.ativo == True
        )
    )
    device = device.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=401, detail='Token de dispositivo inválido')
    return device
```

### Endpoints principais

```python
# POST /api/v1/telemetria/leitura
@router.post('/leitura', status_code=201)
async def receber_leitura(
    payload: TelemetriaPayload,
    device: DispositivoOBD = Depends(get_device),
    db: AsyncSession = Depends(get_db)
):
    # Validar que veiculo_id pertence ao device.user_id
    ...
    registro = TelemetriaOBD(**payload.leituras, veiculo_id=device.veiculo_id)
    db.add(registro)
    await db.commit()
    return {'status': 'ok', 'id': registro.id}

# GET /api/v1/telemetria/tempo-real/{veiculo_id}
# Server-Sent Events (SSE) — cliente recebe eventos quando chegam novos dados
@router.get('/tempo-real/{veiculo_id}')
async def tempo_real(veiculo_id: int, current_user = Depends(get_current_user)):
    async def gerador():
        while True:
            ultima = await buscar_ultima_leitura(veiculo_id, current_user.id)
            yield f"data: {ultima.json()}\n\n"
            await asyncio.sleep(5)
    return StreamingResponse(gerador(), media_type='text/event-stream')
```

---

## 7. Frontend — painel de telemetria

### Componentes visuais

```
┌──────────────────────────────────────────────────────────────────┐
│  TELEMETRIA EM TEMPO REAL — Fiat Cronos 2021                    │
│  ● Conectado via Bluetooth · última leitura 3s atrás            │
├────────────┬────────────┬────────────┬────────────┬─────────────┤
│    RPM     │ VELOCIDADE │ TEMPERATURA│   CARGA    │ COMBUSTÍVEL │
│   1.450    │   0 km/h   │    87°C    │    22%     │    63%      │
│  [gauge]   │  [gauge]   │  [gauge]   │  [gauge]   │  [gauge]   │
├────────────┴────────────┴────────────┴────────────┴─────────────┤
│  Histórico RPM — últimas 24h                                    │
│  [line chart]                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Códigos DTC Ativos                                             │
│  ✓ Nenhum código de falha ativo                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Implementação SSE no frontend (JavaScript)

```javascript
const eventSource = new EventSource(`/api/v1/telemetria/tempo-real/${veiculoId}`, {
    headers: { 'Authorization': `Bearer ${authToken}` }
});

eventSource.onmessage = (event) => {
    const dados = JSON.parse(event.data);
    atualizarGauge('rpm', dados.rpm);
    atualizarGauge('velocidade', dados.velocidade_kmh);
    atualizarGauge('temperatura', dados.temp_liquido_c);
    // ...
};
```

### Biblioteca de gauges recomendada

- **Gauge.js** (`https://bernii.github.io/gauge.js/`) — leve, sem dependências
- **ou:** Chart.js com plugin `chartjs-gauge`

---

## 8. Tabelas do banco de dados

```sql
-- Dispositivos autorizados a enviar telemetria
CREATE TABLE dispositivos_obd (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES usuarios(id),
    veiculo_id   INT NOT NULL REFERENCES veiculo(id),
    nome         VARCHAR(100),
    device_token VARCHAR(64) UNIQUE NOT NULL,
    ativo        BOOLEAN DEFAULT TRUE,
    criado_em    DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultimo_uso   DATETIME,
    INDEX idx_token (device_token),
    INDEX idx_user_veiculo (user_id, veiculo_id)
);

-- Leituras de sensores
CREATE TABLE telemetria_obd (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    veiculo_id       INT NOT NULL REFERENCES veiculo(id),
    device_id        INT REFERENCES dispositivos_obd(id),
    registrado_em    DATETIME DEFAULT CURRENT_TIMESTAMP,
    protocolo        VARCHAR(30),
    rpm              SMALLINT UNSIGNED,
    velocidade_kmh   TINYINT UNSIGNED,
    temp_liquido_c   TINYINT,
    carga_motor_pct  TINYINT UNSIGNED,
    nivel_comb_pct   TINYINT UNSIGNED,
    pressao_bar_kpa  SMALLINT UNSIGNED,
    temp_ar_c        TINYINT,
    posicao_borb_pct TINYINT UNSIGNED,
    INDEX idx_veiculo_ts (veiculo_id, registrado_em)
) ENGINE=InnoDB ROW_FORMAT=COMPRESSED;  -- compressão para série temporal densa

-- Histórico de DTCs
CREATE TABLE dtc_historico (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    veiculo_id  INT NOT NULL REFERENCES veiculo(id),
    codigo      VARCHAR(10) NOT NULL,  -- ex: P0301
    descricao   TEXT,
    detectado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolvido_em DATETIME,
    INDEX idx_veiculo_codigo (veiculo_id, codigo)
);
```

---

## 9. Retenção e privacidade de dados

| Tipo de dado | Retenção padrão | Opt-out |
|---|---|---|
| Leituras de sensores (Raw) | 90 dias | Usuário pode deletar |
| Agregações horárias | 1 ano | — |
| Agregações mensais | Ilimitado (enquanto conta ativa) | — |
| Histórico de DTCs | Enquanto conta ativa | Usuário pode deletar |
| Dados de localização | Não coletados neste módulo | — |

**LGPD:** usuário pode solicitar exportação (`GET /api/v1/telemetria/exportar`) e exclusão total dos dados de telemetria.

---

## 10. Simulador de dados (desenvolvimento sem hardware)

```python
# scripts/simular_telemetria.py
# Uso: python simular_telemetria.py --veiculo-id 1 --token tok_abc123 --api https://zcronos.duckdns.org
import requests, random, time, argparse

def gerar_leitura(viagem_ativa=True):
    if viagem_ativa:
        return {
            'rpm': random.randint(1000, 4000),
            'velocidade_kmh': random.randint(30, 120),
            'temp_liquido_c': random.randint(85, 100),
            'carga_motor_pct': random.randint(20, 70),
            'nivel_comb_pct': random.randint(40, 80),
        }
    return {  # motor ligado, parado
        'rpm': random.randint(700, 900),
        'velocidade_kmh': 0,
        'temp_liquido_c': random.randint(87, 92),
        'carga_motor_pct': random.randint(5, 15),
        'nivel_comb_pct': 65,
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--veiculo-id', type=int, required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--api', default='http://localhost:5013')
    args = parser.parse_args()
    
    print(f"Simulando telemetria para veículo {args.veiculo_id}...")
    while True:
        payload = {
            'veiculo_id': args.veiculo_id,
            'leituras': gerar_leitura(viagem_ativa=True),
            'dtc': []
        }
        r = requests.post(
            f'{args.api}/api/v1/telemetria/leitura',
            json=payload,
            headers={'X-Device-Token': args.token}
        )
        print(f"[{r.status_code}] RPM: {payload['leituras']['rpm']} | "
              f"Vel: {payload['leituras']['velocidade_kmh']} km/h")
        time.sleep(5)
```

---

## 11. Alertas configuráveis

| Alerta | Condição padrão | Canal |
|---|---|---|
| Temperatura alta | temp_liquido_c > 105°C | E-mail + in-app |
| DTC detectado | qualquer código ativo | E-mail + in-app |
| Combustível baixo | nivel_comb_pct < 15% | In-app |
| RPM excedido | rpm > 6000 (configurável) | In-app |
| Sem coleta | última leitura > 30 min atrás (motor ligado) | In-app |

---

## 12. Roadmap do módulo OBD-II

| Versão | Features |
|---|---|
| **v0.1** | Simulador + backend FastAPI + tabelas + painel gauges em tempo real |
| **v0.2** | Agente Android com ELM327 real + detecção automática de PIDs |
| **v0.3** | Offline sync + fila Room + WorkManager |
| **v0.4** | Histórico com gráficos + alertas configuráveis |
| **v0.5** | DTC decoder (3000+ códigos em PT-BR) |
| **v1.0** | Integração IA para análise de padrões e manutenção preditiva |

---

## 13. Limitações e honestidade técnica

- Compatibilidade OBD-II varia por veículo e adaptador — sempre testar antes de anunciar suporte
- Adaptadores ELM327 baratos (~R$30) podem ter firmware instável ou lento
- Android 12+ exige pareamento manual pelo usuário — sem background Bluetooth discovery
- Alguns PIDs retornam "NO DATA" mesmo em veículos compatíveis (depende da ECU)
- Não implementar comandos de escrita na ECU (Mode 04, 09, ATCM, etc.) — risco real de dano
- Latência de ~200ms por PID via Bluetooth — evitar coleta de múltiplos PIDs em paralelo
