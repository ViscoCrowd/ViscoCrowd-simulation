# ViscoCrowd — raccourcis de developpement pour Windows (PowerShell)
# Equivalent multiplateforme du Makefile pour les environnements PowerShell.

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
    Write-Host "  test-invariants  Lance uniquement les invariants physiques"
    Write-Host "  test-lents  Lance uniquement les scenarios lents"
    Write-Host "  simu        Lance une simulation (config en argument, piscine par defaut)"
    Write-Host "  rejouer     Relit une archive (en argument, la plus recente de data par defaut)"
    Write-Host "  comparer    Compare la piscine seche et mouillee sur dix graines (E1/E2)"
    Write-Host "  lint        Verifie le style et le formatage avec ruff"
    Write-Host "  format      Reformate le code avec ruff"
    Write-Host "  valider     Rejoue les criteres de validation du moteur, chiffres"
    Write-Host "  interface   Ouvre l'apercu de la piscine (affichage local)"
    Write-Host "  figures     Regenere toutes les figures dans report/figures"
    Write-Host "  report      Compile le rapport LaTeX (report/main.tex)"
    Write-Host "  docker      Construit l'image Docker de reproductibilite"
    Write-Host "  clean       Supprime les caches et artefacts temporaires"
    Write-Host "  help        Affiche cette aide"
    Write-Host ""
    Write-Host "Apres test, test-all, valider, interface et figures, les arguments sont transmis"
    Write-Host "tels quels, par exemple : .\run.ps1 test -v -k milieu"
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

# Pas de bloc param : avec [CmdletBinding()] ou [Parameter()], PowerShell ajoute au
# script ses parametres communs (-Verbose, -Debug, -PipelineVariable...) et prendrait
# pour eux les options de pytest qui commencent pareil : `test -v` perdait son -v,
# `test -p no:cacheprovider` echouait. On lit donc $args a la main.
$Commandes = @(
    "help", "install", "test", "test-all", "lint", "format",
    "valider", "interface", "figures", "report", "docker", "clean"
)
$Command = if ($args.Count -gt 0) { [string]$args[0] } else { "help" }
$ExtraArgs = @(if ($args.Count -gt 1) { $args[1..($args.Count - 1)] })  # @() : jamais $null
if ($Commandes -notcontains $Command) {
    Write-Host "Commande inconnue : $Command" -ForegroundColor Red
    Show-Help
    exit 1
}
# lint et format enchainent deux commandes ruff aux options differentes, comme le
# Makefile : un argument accepte par l'une ferait echouer l'autre.
if ($Command -in @("lint", "format") -and $ExtraArgs.Count -gt 0) {
    Write-Host "$Command ne prend pas d'argument ; appeler ruff directement pour des options." -ForegroundColor Red
    exit 1
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

    "test-invariants" {
        Invoke-Py -BaseArgs @("-m", "pytest", "-m", "invariant") -MoreArgs $ExtraArgs
    }

    "test-lents" {
        Invoke-Py -BaseArgs @("-m", "pytest", "-m", "slow") -MoreArgs $ExtraArgs
    }

    "simu" {
        $Config = if ($ExtraArgs) { $ExtraArgs[0] } else { "experiments/piscine.yaml" }
        $Nom = [IO.Path]::GetFileNameWithoutExtension($Config)
        $Sortie = "data/$Nom-$(Get-Date -Format 'yyyyMMdd-HHmmss').npz"
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "simuler", $Config, "--sortie", $Sortie) -MoreArgs @()
    }

    "rejouer" {
        $Archive = if ($ExtraArgs) { $ExtraArgs[0] } else {
            Get-ChildItem data/*.npz -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
        }
        if (-not $Archive) { throw "Aucune archive dans data/ : lancer d'abord .\run.ps1 simu" }
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "rejouer", "$Archive") -MoreArgs @()
    }

    "comparer" {
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "comparer-piscine", "experiments/piscine.yaml", "--graines", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10") -MoreArgs @()
    }

    "lint" {
        Write-Host "==> Verification ruff check..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "ruff", "check", ".")
        Write-Host "==> Verification ruff format..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "ruff", "format", "--check", ".")
    }

    "format" {
        Write-Host "==> Formatage du code avec ruff..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "ruff", "format", ".")
        Write-Host "==> Correction automatique des imports et lints..." -ForegroundColor Green
        Invoke-Py -BaseArgs @("-m", "ruff", "check", "--fix", ".")
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
