# deploy.ps1 — zCronos
# Uso: .\deploy.ps1

$SERVER      = "felipe@casakek.duckdns.org"
$SSH_PORT    = "64622"
$SERVER_PATH = "/home/felipe/sistemas/zCronos"
$CONTAINER   = "zcronos_web_1"
$APP_PORT    = "5012"
$HEALTH_URL  = "http://localhost:$APP_PORT"

Write-Host "`n=== zCronos Deploy ===" -ForegroundColor Cyan

# 1. Verificar mudanças locais não commitadas
$status = git status --porcelain
if ($status) {
    Write-Host "`n[AVISO] Existem mudancas nao commitadas:" -ForegroundColor Yellow
    git status --short
    $resp = Read-Host "Continuar mesmo assim? (s/N)"
    if ($resp -ne "s") { Write-Host "Deploy cancelado."; exit 1 }
}

# 2. Push para o GitHub
Write-Host "`n[1/4] Enviando para o GitHub..." -ForegroundColor Cyan
git push origin main
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO no git push." -ForegroundColor Red; exit 1 }

# 3. Build e deploy no servidor
Write-Host "`n[2/4] Construindo imagem no servidor..." -ForegroundColor Cyan
$BUILD_CMD = @"
set -e
cd $SERVER_PATH
git pull --ff-only origin main
docker-compose -f docker-compose.prod.yml build web
"@
ssh -p $SSH_PORT $SERVER $BUILD_CMD
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO no build." -ForegroundColor Red; exit 1 }

Write-Host "`n[3/4] Recriando container..." -ForegroundColor Cyan
$DEPLOY_CMD = @"
set -e
cd $SERVER_PATH
docker rm -f $CONTAINER 2>/dev/null || true
docker-compose -f docker-compose.prod.yml up -d --no-deps web
"@
ssh -p $SSH_PORT $SERVER $DEPLOY_CMD
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO ao subir container." -ForegroundColor Red; exit 1 }

# 4. Health check
Write-Host "`n[4/4] Aguardando app ficar pronto..." -ForegroundColor Cyan
$HEALTH_CMD = @"
for i in \$(seq 1 20); do
  code=\$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)
  if [ "\$code" = "200" ]; then
    echo "App OK (HTTP 200)"
    exit 0
  fi
  echo "Aguardando... tentativa \$i/20 (HTTP \$code)"
  sleep 3
done
echo "TIMEOUT: app nao respondeu"
exit 1
"@
ssh -p $SSH_PORT $SERVER $HEALTH_CMD
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO no health check." -ForegroundColor Red; exit 1 }

Write-Host "`n=== Deploy concluido! ===" -ForegroundColor Green
Write-Host "App rodando em: http://casakek.duckdns.org (via NPM)" -ForegroundColor Green
Write-Host "Porta direta:   http://casakek.duckdns.org:$APP_PORT" -ForegroundColor Green
