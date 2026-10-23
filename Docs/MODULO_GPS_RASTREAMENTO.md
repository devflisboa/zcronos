# zCronos — Módulo de Rastreamento GPS por Smartphone

> Arquitetura independente do módulo OBD-II. Usa Bluetooth do carro como gatilho, GPS como coleta.  
> Data: 2026-10-23 | Versão: 1.0

---

## 1. Visão geral

Detecta automaticamente o início de uma viagem quando o smartphone autorizado se conecta ao Bluetooth do veículo (painel ou som do carro) e inicia rastreamento GPS em foreground service.

**Princípios invioláveis:**
- Rastreamento visível ao usuário (notificação permanente durante coleta)
- Sem rastreamento oculto ou em segundo plano silencioso
- Sem acesso a localizações de outros usuários sem autorização explícita
- Consentimento específico antes da primeira coleta

---

## 2. Diferença em relação ao módulo OBD-II

| Módulo OBD-II | Módulo GPS |
|---|---|
| Requer adaptador ELM327 na porta OBD | Requer apenas smartphone Android |
| Coleta dados de sensores da ECU | Coleta coordenadas GPS do telefone |
| Dados: RPM, temperatura, DTCs | Dados: percurso, distância, duração, velocidade GPS |
| Dependência: Bluetooth Classic serial | Dependência: Bluetooth genérico do carro (qualquer dispositivo BT) |
| Útil para: diagnóstico, desempenho | Útil para: histórico de viagens, km rodados, Uber |

---

## 3. Arquitetura geral

```
┌─────────────────────────────────────────────────────────────────┐
│  DISPOSITIVO BLUETOOTH DO VEÍCULO                               │
│  (Painel Uconnect, rádio, viva-voz — qualquer perfil A2DP/HFP)│
└────────────────────────┬────────────────────────────────────────┘
                         │ Evento de conexão BT (BroadcastReceiver)
┌────────────────────────▼────────────────────────────────────────┐
│  AGENTE ANDROID (app Kotlin)                                    │
│  BT MAC registrado → confirmar movimento via Fused Location     │
│  → iniciar ForegroundService de rastreamento                    │
│  → coletar GPS a cada 5-10s (configurável)                      │
│  → armazenar pontos em Room (offline-first)                     │
│  → detectar fim de viagem (BT desconecta + imobilidade)         │
│  → calcular distância, duração, velocidade média                │
│  → sync via WorkManager quando online                           │
└────────────────────────┬────────────────────────────────────────┘
                         │ POST HTTPS + Bearer + Device Token
┌────────────────────────▼────────────────────────────────────────┐
│  BACKEND FastAPI (mesmo serviço do módulo OBD ou separado)      │
│  POST /api/v1/viagens/iniciar                                   │
│  POST /api/v1/viagens/{id}/pontos (batch)                       │
│  POST /api/v1/viagens/{id}/finalizar                            │
│  GET  /api/v1/viagens/{id}/percurso                             │
│  GET  /api/v1/viagens?user_id=X&from=...&to=...                │
└────────────────────────┬────────────────────────────────────────┘
                         │ PostGIS (consultas geoespaciais)
┌────────────────────────▼────────────────────────────────────────┐
│  PostgreSQL + PostGIS (upgrade necessário para este módulo)     │
│  Tabelas: viagens, pontos_gps, dispositivos_autorizados         │
└─────────────────────────────────────────────────────────────────┘
                         │ MapLibre GL JS ou Leaflet.js
┌────────────────────────▼────────────────────────────────────────┐
│  FRONTEND PWA                                                   │
│  Mapa interativo com percursos                                  │
│  Histórico de viagens com filtros                               │
│  Estatísticas: km total, viagens/semana, duração média          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Stack tecnológica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Agente Android | Kotlin + Android SDK | Acesso nativo ao BT e GPS |
| Location API | Fused Location Provider (Google Play Services) | Balanceamento automático precisão × bateria |
| Persistência local | Room (SQLite) | Offline-first confiável |
| Background sync | WorkManager | Gerenciamento de energia respeitado pelo Android |
| Foreground service | Android ForegroundService (tipo: location) | Obrigatório para GPS contínuo no Android 8+ |
| Backend | FastAPI + Python | Async, ideal para múltiplos clients simultâneos |
| Banco de dados | PostgreSQL 15 + PostGIS | Suporte nativo a geometrias e distâncias |
| Mapa frontend | MapLibre GL JS (open-source) ou Leaflet.js | Sem custo de API key |
| Tiles de mapa | OpenStreetMap + tiles gratuitos | Sem custo |

> **Nota:** Este módulo exige migração de MySQL para PostgreSQL, ou um banco PostgreSQL separado. PostGIS não tem equivalente no MySQL para consultas geoespaciais eficientes.

---

## 5. Agente Android — especificação detalhada

### Permissões (AndroidManifest.xml)

```xml
<!-- Bluetooth -->
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.BLUETOOTH_SCAN"
    android:usesPermissionFlags="neverForLocation" />

<!-- Localização — pedir em runtime -->
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />

<!-- Background location — pedir separado, com justificativa clara -->
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />

<!-- Foreground service -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />

<!-- Internet e monitoramento de rede -->
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<!-- Iniciar ao ligar o dispositivo (para retomar viagem interrompida) -->
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
```

> **Android 15:** ACCESS_BACKGROUND_LOCATION exige justificativa detalhada no Play Store. Alternativa: pedir apenas FINE_LOCATION e usar foreground service — o usuário vê a notificação e sabe que está sendo rastreado.

### Fluxo de detecção de viagem

```
BroadcastReceiver escuta:
  ACTION_ACL_CONNECTED (android.bluetooth.device.action.ACL_CONNECTED)
     │
     ▼
MAC do dispositivo BT = MAC cadastrado para o veículo?
  ✗ → ignorar
  ✓ → aguardar 30s (filtro de falso positivo: ligar carro para buscar algo e desligar)
     │
     ▼
Movimento confirmado? (velocidade GPS ≥ 5 km/h OU deslocamento ≥ 200m)
  ✗ → cancelar, continuar aguardando
  ✓ → iniciar ForegroundService de rastreamento
        └── Notificação: "zCronos: Registrando viagem • 0,0 km"
     │
     ▼
Coletar pontos GPS via FusedLocationProviderClient
  Intervalo: 10s (configurável: 5s rápido / 30s economia de bateria)
  Precisão mínima: 20m (descartar pontos com accuracy > 50m)
  Velocidade: registrar velocidade GPS de cada ponto
     │
     ▼
Detecção de fim de viagem (qualquer condição):
  A) Dispositivo BT desconectou + imobilidade por 60s
  B) Usuário parou manualmente via notificação
  C) App entrou em estado de sem-localização por > 5min
     │
     ▼
Calcular:
  - Distância total (Haversine entre pontos consecutivos)
  - Duração (primeiro ponto → último ponto)
  - Velocidade média e máxima
  - Paradas (velocidade < 5 km/h por > 2min)
     │
     ▼
Salvar viagem completa em Room (offline-first)
Tentar sync imediato; se falhar → WorkManager agenda retry
```

### Configuração de bateria vs. precisão

```kotlin
// Configuração da requisição de localização
val locationRequest = LocationRequest.Builder(
    Priority.PRIORITY_HIGH_ACCURACY,  // GPU + BT + rede — maior precisão
    10_000L  // intervalo em ms (10s default)
).apply {
    setMinUpdateIntervalMillis(5_000L)    // mínimo 5s entre atualizações
    setMinUpdateDistanceMeters(10f)       // ignorar se moveu < 10m
    setGranularity(Granularity.GRANULARITY_FINE)
}.build()

// Para economia de bateria (modo parada):
val locationRequestPausa = LocationRequest.Builder(
    Priority.PRIORITY_BALANCED_POWER_ACCURACY,
    30_000L
).build()
```

### Consumo estimado de bateria

| Modo | Consumo estimado | Uso |
|---|---|---|
| Coleta ativa (10s) | ~8-12% / hora | Viagem em andamento |
| Detecção BT (idle) | ~0,5% / hora | App rodando em background esperando BT |
| Sem app ativo | 0% | App fechado — sem monitoramento |

> Comunicar claramente ao usuário: o app consome bateria durante viagens ativas.

---

## 6. Regras de tolerância e filtros de qualidade

| Cenário | Comportamento |
|---|---|
| Sinal GPS perdido < 30s | Interpolar entre último e próximo ponto |
| Sinal GPS perdido > 30s | Marcar lacuna no percurso (não extrapolar) |
| Ponto com precisão > 50m | Descartar (não incluir no traçado) |
| Velocidade GPS > 200 km/h | Descartar (spike de GPS) |
| Parada em sinal ≥ 2min | Registrar como parada, não encerrar viagem |
| Reconexão BT após curta desconexão (< 2min) | Continuar viagem, não criar nova |
| Bluetooth desconecta mas velocidade GPS > 10 km/h | Não encerrar viagem (celular saindo do alcance BT momentaneamente) |

---

## 7. Backend FastAPI — endpoints de viagens

### Modelos Pydantic

```python
class PontoGPS(BaseModel):
    latitude:   float
    longitude:  float
    altitude_m: Optional[float]
    velocidade_kmh: Optional[float]
    precisao_m: float
    timestamp:  datetime

class IniciarViagemPayload(BaseModel):
    veiculo_id:       int
    device_token:     str
    ponto_inicial:    PontoGPS
    bt_mac_veiculo:   str

class FinalizarViagemPayload(BaseModel):
    ponto_final:      PontoGPS
    distancia_km:     float
    duracao_segundos: int
    velocidade_media: float
    velocidade_maxima: float
    pontos:           List[PontoGPS]  # todos os pontos da viagem
```

### Endpoints

```python
# POST /api/v1/viagens/iniciar
@router.post('/viagens/iniciar')
async def iniciar_viagem(payload: IniciarViagemPayload, device = Depends(auth_device)):
    viagem = Viagem(
        user_id=device.user_id,
        veiculo_id=device.veiculo_id,
        device_id=device.id,
        iniciada_em=payload.ponto_inicial.timestamp,
        status='em_andamento'
    )
    db.add(viagem)
    await db.flush()
    return {'viagem_id': viagem.id}

# POST /api/v1/viagens/{viagem_id}/finalizar
@router.post('/viagens/{viagem_id}/finalizar')
async def finalizar_viagem(viagem_id: int, payload: FinalizarViagemPayload, ...):
    # Salvar pontos como LineString PostGIS
    pontos_geom = [Point(p.longitude, p.latitude) for p in payload.pontos]
    viagem.percurso_geom = LineString(pontos_geom)
    viagem.distancia_km = payload.distancia_km
    viagem.duracao_segundos = payload.duracao_segundos
    viagem.status = 'concluida'
    ...

# GET /api/v1/viagens/{viagem_id}/percurso → GeoJSON para o mapa
@router.get('/viagens/{viagem_id}/percurso')
async def percurso_viagem(viagem_id: int, current_user = Depends(get_user)):
    viagem = await get_viagem_do_usuario(viagem_id, current_user.id)  # isolamento
    return {
        'type': 'Feature',
        'geometry': json.loads(db.scalar(ST_AsGeoJSON(viagem.percurso_geom))),
        'properties': {
            'distancia_km': viagem.distancia_km,
            'duracao': viagem.duracao_segundos,
            'iniciada_em': viagem.iniciada_em.isoformat(),
        }
    }
```

---

## 8. Banco de dados PostgreSQL + PostGIS

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

-- Dispositivos autorizados por veículo
CREATE TABLE dispositivos_autorizados (
    id           SERIAL PRIMARY KEY,
    user_id      INT NOT NULL REFERENCES usuarios(id),
    veiculo_id   INT NOT NULL REFERENCES veiculo(id),
    nome         VARCHAR(100),        -- "Samsung Galaxy do Felipe"
    device_token VARCHAR(64) UNIQUE NOT NULL,
    bt_mac_veiculo VARCHAR(17),       -- MAC Bluetooth do painel do carro: AA:BB:CC:DD:EE:FF
    ativo        BOOLEAN DEFAULT TRUE,
    criado_em    TIMESTAMPTZ DEFAULT NOW()
);

-- Viagens registradas
CREATE TABLE viagens (
    id                SERIAL PRIMARY KEY,
    user_id           INT NOT NULL REFERENCES usuarios(id),
    veiculo_id        INT NOT NULL REFERENCES veiculo(id),
    device_id         INT REFERENCES dispositivos_autorizados(id),
    iniciada_em       TIMESTAMPTZ NOT NULL,
    finalizada_em     TIMESTAMPTZ,
    distancia_km      NUMERIC(8,3),
    duracao_segundos  INT,
    velocidade_media  NUMERIC(5,1),
    velocidade_maxima NUMERIC(5,1),
    status            VARCHAR(20) DEFAULT 'em_andamento',  -- em_andamento | concluida | cancelada
    percurso_geom     GEOMETRY(LINESTRING, 4326),          -- WGS84
    origem_geom       GEOMETRY(POINT, 4326),
    destino_geom      GEOMETRY(POINT, 4326),
    origem_endereco   VARCHAR(200),  -- reverse geocoding opcional
    destino_endereco  VARCHAR(200),
    observacoes       TEXT
);

-- Índices geoespaciais
CREATE INDEX idx_viagens_user ON viagens(user_id);
CREATE INDEX idx_viagens_veiculo ON viagens(veiculo_id);
CREATE INDEX idx_viagens_percurso ON viagens USING GIST(percurso_geom);
CREATE INDEX idx_viagens_data ON viagens(iniciada_em);
```

---

## 9. Frontend — painel de viagens

### Tela de histórico de viagens

```
┌─────────────────────────────────────────────────────────────────┐
│  VIAGENS — Fiat Cronos 2021                                    │
│  Filtros: [Outubro 2026 ▼] [Todos os veículos ▼] [Exportar ↓] │
├───────────────────────────────────────────────────────────────  │
│  📍 Hoje, 14:30   Casa → Shopping Iguatemi                     │
│     12,4 km · 28 min · Vel. média 26 km/h                     │
│     [Ver no mapa]                                              │
├─────────────────────────────────────────────────────────────────┤
│  📍 Hoje, 08:15   Casa → Trabalho                              │
│     8,7 km · 22 min · Vel. média 23 km/h                      │
│     [Ver no mapa]                                              │
├─────────────────────────────────────────────────────────────────┤
│  ESTATÍSTICAS DO MÊS                                           │
│  42 viagens · 487 km · 18h22min dirigindo                     │
└─────────────────────────────────────────────────────────────────┘
```

### Tela de detalhe com mapa (MapLibre GL JS)

```javascript
// Renderizar percurso no mapa
const map = new maplibregl.Map({
    container: 'mapa',
    style: 'https://tiles.openstreetmap.org/style.json',  // tiles gratuitos
    center: [percurso.origem.lng, percurso.origem.lat],
    zoom: 12
});

map.on('load', () => {
    map.addSource('percurso', {
        type: 'geojson',
        data: percursoGeoJSON  // recebido do backend
    });
    map.addLayer({
        id: 'linha-percurso',
        type: 'line',
        source: 'percurso',
        paint: {
            'line-color': '#2563eb',
            'line-width': 4,
            'line-opacity': 0.8
        }
    });
    // Marcadores de início e fim
    new maplibregl.Marker({ color: '#16a34a' })
        .setLngLat(percurso.origem)
        .addTo(map);
    new maplibregl.Marker({ color: '#dc2626' })
        .setLngLat(percurso.destino)
        .addTo(map);
});
```

---

## 10. Simulador de trajetos (desenvolvimento)

```python
# scripts/simular_viagem.py
# Gera viagem simulada entre dois pontos com pontos intermediários realistas

import requests, json, time, math, argparse
from datetime import datetime, timezone

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def interpolar_rota(origem, destino, n_pontos=20):
    pontos = []
    for i in range(n_pontos + 1):
        frac = i / n_pontos
        lat = origem[0] + frac * (destino[0] - origem[0])
        lon = origem[1] + frac * (destino[1] - origem[1])
        pontos.append({'latitude': lat, 'longitude': lon,
                       'precisao_m': 5.0,
                       'velocidade_kmh': 40.0 + (i % 5) * 2,
                       'timestamp': datetime.now(timezone.utc).isoformat()})
        time.sleep(0.5)  # simular tempo entre pontos
    return pontos

if __name__ == '__main__':
    # Exemplo: Casa → Shopping em Curitiba
    ORIGEM  = (-25.4284, -49.2733)
    DESTINO = (-25.4373, -49.2916)
    
    pontos = interpolar_rota(ORIGEM, DESTINO)
    distancia = haversine(*ORIGEM, *DESTINO)
    
    payload = {
        'veiculo_id': 1,
        'ponto_inicial': pontos[0],
        'ponto_final': pontos[-1],
        'distancia_km': round(distancia, 3),
        'duracao_segundos': len(pontos) * 30,
        'velocidade_media': 40.0,
        'velocidade_maxima': 65.0,
        'pontos': pontos
    }
    
    r = requests.post(
        'http://localhost:5013/api/v1/viagens/finalizar-simulado',
        json=payload,
        headers={'X-Device-Token': 'tok_simulador'}
    )
    print(f"[{r.status_code}] Viagem criada: {r.json()}")
```

---

## 11. LGPD e privacidade

### Consentimento obrigatório antes da primeira coleta

- Tela explicativa detalhada antes de ativar o módulo
- Texto direto: "O app irá registrar sua localização GPS durante viagens detectadas pela conexão Bluetooth com seu veículo"
- Checkbox explícito (não pré-marcado)
- Link para política de privacidade

### Direitos do usuário (LGPD Art. 18)

| Direito | Como exercer no app |
|---|---|
| Acesso aos dados | `GET /api/v1/viagens/exportar` → GeoJSON ou CSV |
| Correção | Edição de metadados da viagem (nome, observações) |
| Exclusão | `DELETE /api/v1/viagens/{id}` e `DELETE /api/v1/viagens/todas` |
| Portabilidade | Exportação completa em formato aberto |
| Oposição | Desativar módulo GPS mantendo demais funcionalidades |

### O que NÃO é coletado

- Localização quando fora de uma viagem ativa
- Localização de terceiros no veículo
- Dados de localização em modo background silencioso

---

## 12. Testes de resiliência

| Cenário | Comportamento esperado |
|---|---|
| GPS indisponível ao iniciar | Aguardar até 2min; se não obtiver fix, não iniciar viagem |
| GPS perdido durante viagem | Marcar lacuna, continuar aguardando; encerrar se > 5min |
| Internet indisponível | Salvar tudo em Room; sync automático ao reconectar |
| App morto pelo SO (doze mode) | WorkManager retoma sync; ForegroundService resiste ao kill |
| Bluetooth reconecta após queda < 2min | Continuar viagem atual |
| Bateria crítica (< 5%) | Encerrar viagem automaticamente, salvar o que coletou |
| Celular reiniciado durante viagem | BOOT_COMPLETED → verificar viagem pendente em Room → sync |

---

## 13. Roadmap do módulo GPS

| Versão | Features |
|---|---|
| **v0.1** | Simulador + backend FastAPI + tabelas PostGIS + painel de lista de viagens |
| **v0.2** | Mapa de percurso com MapLibre GL JS |
| **v0.3** | Agente Android alpha — detecção BT + GPS manual (botão iniciar/parar) |
| **v0.4** | Detecção automática via BT MAC do veículo |
| **v0.5** | Offline sync + WorkManager |
| **v0.6** | Estatísticas avançadas + exportação CSV/GeoJSON |
| **v1.0** | Correlação com módulo Uber (comparar km GPS vs. km declarado) |

---

## 14. Integração com demais módulos zCronos

| Módulo | Correlação possível |
|---|---|
| Abastecimento | Km real no odômetro ao abastecer vs. km GPS acumulado — detectar inconsistências |
| Despesas (Uber) | Km percorrido em corridas pode ser preenchido automaticamente via GPS |
| Manutenção | Km para próxima troca de óleo baseado em km GPS real (mais preciso que km declarado) |
| OBD-II | Sincronizar timestamps de telemetria com pontos do percurso GPS (dados combinados) |

---

## 15. Limitações e honestidade técnica

- Sem celular no carro = sem rastreamento (por design e por limitação técnica)
- GPS de smartphones tem precisão de 3-20m — suficiente para rotas, impreciso para parkings
- Android 15 pode matar ForegroundService em cenários extremos de memória — implementar recuperação
- Tiles de mapa gratuitos (OSM) têm limitações de uso comercial — verificar ToS ao escalar
- Reverse geocoding gratuito (Nominatim) tem limite de 1 req/s — cachear resultados
- Não usar localização para funcionalidades que não foram explicitadas ao usuário no consentimento
