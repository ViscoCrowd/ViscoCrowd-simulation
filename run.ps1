# ViscoCrowd — raccourcis de developpement pour Windows (PowerShell)
# Equivalent multiplateforme du Makefile pour les environnements PowerShell.

[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [ValidateSet(
        "help",
        "install",
        "test",
        "test-all",
        "lint",
        "format",
        "valider",
        "interface",
        "figures",
        "report",
        "docker",
        "clean"
    )]
    [string]$Command = "help",

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"

# Interpreteur utilise : variable d'environnement VISCO_PY, ou .venv local, ou python dans le PATH
if ($env:VISCO_PY) {
    $Python = $env:VISCO_PY
} elseif (Test-Path $VenvPy) {
    $Python = $VenvPy
} else {
    $Python = "python"
}

function Show-Help {
    Write-Host "Usage: .\run.ps1 <commande> [arguments]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commandes disponibles :"
    Write-Host "  install     Cree l'environnement virtuel et installe le projet en mode editable"
    Write-Host "  test        Lance la suite de tests rapides (hors scenarios lents)"
    Write-Host "  test-all    Lance tous les tests, scenarios lents compris"
    Write-Host "  lint        Verifie le style et le formatage avec ruff"
    Write-Host "  format      Reformate le code avec ruff"
    Write-Host "  valider     Rejoue les criteres de validation du moteur, chiffres"
    Write-Host "  interface   Ouvre l'apercu de la piscine (affichage local)"
    Write-Host "  figures     Regenere toutes les figures dans report/figures"
    Write-Host "  report      Compile le rapport LaTeX (report/main.tex)"
    Write-Host "  docker      Construit l'image Docker de reproductibilite"
    Write-Host "  clean       Supprime les caches et artefacts temporaires"
    Write-Host "  help        Affiche cette aide"
}

function Invoke-Py {
    param (
        [string[]]$BaseArgs,
        [string[]]$MoreArgs
    )
    $AllArgs = @($BaseArgs)
    if ($null -ne $MoreArgs -and $MoreArgs.Count -gt 0) {
        $AllArgs += $MoreArgs
    }
    & $Python @AllArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

switch ($Command) {
    "help" {
        Show-Help
    }

    "install" {
        Write-Host "==> Creation du venv et installation des dependances..." -ForegroundColor Green
        & python -m venv (Join-Path $Root ".venv")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $VenvPy -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $VenvPy -m pip install -e "$Root[dev]"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    "test" {
        Write-Host "==> Execution de la suite de tests rapides..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "pytest", "-m", "not slow") -MoreArgs $ExtraArgs
    }

    "test-all" {
        Write-Host "==> Execution de l'ensemble des tests..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "pytest") -MoreArgs $ExtraArgs
    }

    "lint" {
        Write-Host "==> Verification ruff check..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "ruff", "check", ".") -MoreArgs $ExtraArgs
        Write-Host "==> Verification ruff format..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "ruff", "format", "--check", ".") -MoreArgs $ExtraArgs
    }

    "format" {
        Write-Host "==> Formatage du code avec ruff..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "ruff", "format", ".") -MoreArgs $ExtraArgs
        Write-Host "==> Correction automatique des imports et lints..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "ruff", "check", "--fix", ".") -MoreArgs $ExtraArgs
    }

    "valider" {
        Write-Host "==> Validation des criteres du moteur..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "valider-moteur") -MoreArgs $ExtraArgs
    }

    "interface" {
        Write-Host "==> Lancement de l'interface..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "interface") -MoreArgs $ExtraArgs
    }

    "figures" {
        Write-Host "==> Generation des figures..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "valider-moteur", "--figures", "--sortie", "report/figures") -MoreArgs $ExtraArgs
    }

    "report" {
        Write-Host "==> Compilation du rapport LaTeX..." -ForegroundColor Green
        Push-Location (Join-Path $Root "report")
        try {
            & latexmk -pdf -interaction=nonstopmode main.tex
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        } finally {
            Pop-Location
        }
    }

    "docker" {
        Write-Host "==> Construction de l'image Docker..." -ForegroundColor Green
        & docker compose build
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    "clean" {
        Write-Host "==> Nettoyage des caches et artefacts..." -ForegroundColor Green
        $targets = @(
            Join-Path $Root ".pytest_cache"
            Join-Path $Root ".ruff_cache"
            Join-Path $Root "htmlcov"
            Join-Path $Root ".coverage"
            Join-Path $Root "figures"
        )
        foreach ($t in $targets) {
            if (Test-Path $t) {
                Remove-Item -Recurse -Force $t
                Write-Host "  Supprime : $t"
            }
        }
        Get-ChildItem -Path $Root -Recurse -Filter "__pycache__" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Item -Recurse -Force $_.FullName
            Write-Host "  Supprime : $($_.FullName)"
        }
        Write-Host "Nettoyage termine." -ForegroundColor Green
    }
}
