# Assistente PowerShell para subir no GitHub
Clear-Host
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Assistente de Publicacao no GitHub" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[ERRO] Git nao encontrado! Baixe em: https://git-scm.com/download/win" -ForegroundColor Red
    Pause
    Exit
}
Write-Host "[OK] Git detectado com sucesso." -ForegroundColor Green

# 2. Commit local
git add .
git commit -m "feat: Portal de Gestao de Projetos" 2>$null

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Yellow
Write-Host "Cole a URL HTTPS do seu repositorio no GitHub (Ex: https://github.com/usuario/repo.git):" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Yellow
$repoUrl = Read-Host "URL do Repositorio"

if ([string]::IsNullOrWhiteSpace($repoUrl)) {
    Write-Host "[AVISO] Nenhuma URL informada. Cancelado." -ForegroundColor Yellow
    Pause
    Exit
}

$repoUrl = $repoUrl.Trim('"', "'", " ")

git remote remove origin 2>$null
git remote add origin $repoUrl

Write-Host ""
Write-Host "Sincronizando alteracoes remotas..." -ForegroundColor Cyan
git pull --rebase origin main 2>$null

Write-Host "Enviando arquivos para o GitHub (git push -u origin main)..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host "[SUCESSO] Projeto publicado com sucesso no GitHub!" -ForegroundColor Green
    Write-Host "Acesse seu repositorio em: $repoUrl" -ForegroundColor Green
    Write-Host "==============================================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Red
    Write-Host "[ATENCAO] Ocorreu uma falha no envio. Se o repositorio ja foi criado com README, use:" -ForegroundColor Red
    Write-Host "git push -u origin main --force" -ForegroundColor Yellow
    Write-Host "==============================================================================" -ForegroundColor Red
}
Pause
