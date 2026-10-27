# ViscoCrowd — raccourcis de developpement pour Windows (PowerShell)
# Equivalent multiplateforme du Makefile pour les environnements PowerShell.

[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [ValidateSet("help", "install", "test", "test-all", "lint", "format", "valider", "interface", "figures", "clean")]
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
    Write-Host "  clean       Supprime les caches et artefacts temporaires"
    Write-Host "  help        Affiche cette aide"
}

function Invoke-Py {
    param ([string[]]$ArgsList)
    & $Python $ArgsList
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
        & $VenvPy -m pip install --upgrade pip
        & $VenvPy -m pip install -e "$Root[dev]"
    }

    "test" {
        Write-Host "==> Execution de la suite de tests rapides..." -ForegroundColor Green
        Invoke-Py (@("-m", "pytest", "-m", "not slow") + $ExtraArgs)
    }

    "test-all" {
        Write-Host "==> Execution de l'ensemble des tests..." -ForegroundColor Green
        Invoke-Py (@("-m", "pytest") + $ExtraArgs)
    }

    "lint" {
        Write-Host "==> Verification ruff check..." -ForegroundColor Green
        Invoke-Py (@("-m", "ruff", "check", ".") + $ExtraArgs)
        Write-Host "==> Verification ruff format..." -ForegroundColor Green
        Invoke-Py (@("-m", "ruff", "format", "--check", ".") + $ExtraArgs)
    }

    "format" {
        Write-Host "==> Formatage du code avec ruff..." -ForegroundColor Green
        Invoke-Py (@("-m", "ruff", "format", ".") + $ExtraArgs)
        Write-Host "==> Correction automatique des imports et lints..." -ForegroundColor Green
        Invoke-Py (@("-m", "ruff", "check", "--fix", ".") + $ExtraArgs)
    }

    "valider" {
        Write-Host "==> Validation des criteres du moteur..." -ForegroundColor Green
        Invoke-Py (@("-m", "viscocrowd.cli", "valider-moteur") + $ExtraArgs)
    }

    "interface" {
        Write-Host "==> Lancement de l'interface..." -ForegroundColor Green
        Invoke-Py (@("-m", "viscocrowd.cli", "interface") + $ExtraArgs)
    }

    "figures" {
        Write-Host "==> Generation des figures..." -ForegroundColor Green
        Invoke-Py (@("-m", "viscocrowd.cli", "valider-moteur", "--figures", "--sortie", "report/figures") + $ExtraArgs)
    }

    "clean" {
        Write-Host "==> Nettoyage des caches et artefacts..." -ForegroundColor Green
        $targets = @(
            Join-Path $Root ".pytest_cache",
            Join-Path $Root ".ruff_cache",
            Join-Path $Root "htmlcov",
            Join-Path $Root ".coverage"
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
