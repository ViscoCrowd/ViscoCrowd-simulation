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
    Write-Host "  simu        Lance une simulation (config en argument, piscine par defaut ; --fixer NOM=VALEUR ...)"
    Write-Host "  rejouer     Relit une archive (en argument, la plus recente de data par defaut ; options transmises, ex. --vitesse 5)"
    Write-Host "  menu        Parametre la piscine par questions, simule puis relit (config en argument)"
    Write-Host "  demo        Regenere les films de la soutenance dans data/demo/"
    Write-Host "  lancer      Simule puis ouvre la relecture (config en argument, piscine ou couloir ; options transmises a la relecture)"
    Write-Host "  comparer    Compare la piscine seche et mouillee sur dix graines (E1/E2)"
    Write-Host "  campagne-finale  Rejoue la campagne finale, avec reprise, dans data/finale"
    Write-Host "  lint        Verifie le style et le formatage avec ruff"
    Write-Host "  format      Reformate le code avec ruff"
    Write-Host "  valider     Rejoue les criteres de validation du moteur, chiffres"
    Write-Host "  maquette    Ouvre la maquette de la piscine, sans simulation"
    Write-Host "  figures     Regenere toutes les figures dans report/figures"
    Write-Host "  report      Compile le rapport LaTeX (report/main.tex)"
    Write-Host "  docker      Construit l'image Docker de reproductibilite"
    Write-Host "  clean       Supprime les caches et artefacts temporaires"
    Write-Host "  help        Affiche cette aide"
    Write-Host ""
    Write-Host "Apres test, test-all, valider, maquette et figures, les arguments sont transmis"
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
    "help", "install", "test", "test-all", "test-invariants", "test-lents",
    "lint", "format", "valider", "simu", "rejouer", "lancer", "menu", "demo", "comparer", "campagne-finale",
    "maquette", "figures", "report", "docker", "clean"
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
        # Configuration facultative en premier argument ; les options qui suivent sont
        # transmises a simuler : .\run.ps1 simu --fixer n_agents=150 largeur_porte=0.8
        $Options = @($ExtraArgs)
        $Config = "experiments/piscine.yaml"
        if ($Options.Count -gt 0 -and -not ([string]$Options[0]).StartsWith("-")) {
            $Config = $Options[0]
            $Options = @(if ($Options.Count -gt 1) { $Options[1..($Options.Count - 1)] })
        }
        $Nom = [IO.Path]::GetFileNameWithoutExtension($Config)
        $Sortie = "data/$Nom-$(Get-Date -Format 'yyyyMMdd-HHmmss').npz"
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "simuler", $Config, "--sortie", $Sortie) -MoreArgs $Options
    }

    "menu" {
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "menu") -MoreArgs $ExtraArgs
    }

    "demo" {
        Remove-Item -Recurse -Force data/demo -ErrorAction SilentlyContinue
        $Demo = "experiments/demo/duel-plage-glissante.yaml"
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "duel", $Demo, "--gif", "data/demo/duel.gif") -MoreArgs @()
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "comparer-variantes", $Demo, "--gif", "data/demo/variantes.gif",
            "--variante", "adherence_mouille=3.3", "--variante", "adherence_mouille=2",
            "--variante", "adherence_mouille=1") -MoreArgs @()
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "simuler", $Demo, "--sortie", "data/demo/plage-glissante.npz") -MoreArgs @()
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "pose-longue", "data/demo/plage-glissante.npz",
            "--image", "data/demo/pose-longue.png") -MoreArgs @()
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "pression", "experiments/demo/pression-porte-saturee.yaml",
            "--image", "data/demo/pression.png", "--instant", "35") -MoreArgs @()
    }

    "rejouer" {
        # L'archive en premier argument est facultative ; les options qui suivent sont
        # transmises a la relecture : .\run.ps1 rejouer --vitesse 5
        $Options = @($ExtraArgs)
        $Archive = $null
        if ($Options.Count -gt 0 -and -not ([string]$Options[0]).StartsWith("-")) {
            $Archive = $Options[0]
            $Options = @(if ($Options.Count -gt 1) { $Options[1..($Options.Count - 1)] })
        }
        if (-not $Archive) {
            # Les diagnostics de projection (#69) ne sont pas des trajectoires.
            $Archive = Get-ChildItem data/*.npz -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -notlike '*.diagnostic.npz' } |
                Sort-Object LastWriteTime | Select-Object -Last 1
        }
        if (-not $Archive) { throw "Aucune archive dans data/ : lancer d'abord .\run.ps1 simu" }
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "rejouer", "$Archive") -MoreArgs $Options
    }

    "lancer" {
        # Relit l'archive qui vient d'etre ecrite, pas « la plus recente de data » :
        # un autre calcul fini entre-temps serait relu a sa place. Invoke-Py quitte
        # le script si la simulation echoue, la relecture n'est alors pas lancee.
        # Comme pour rejouer : configuration facultative, options transmises a la
        # relecture (.\run.ps1 lancer --vitesse 5).
        $Options = @($ExtraArgs)
        $Config = "experiments/piscine.yaml"
        if ($Options.Count -gt 0 -and -not ([string]$Options[0]).StartsWith("-")) {
            $Config = $Options[0]
            $Options = @(if ($Options.Count -gt 1) { $Options[1..($Options.Count - 1)] })
        }
        $Nom = [IO.Path]::GetFileNameWithoutExtension($Config)
        $Sortie = "data/$Nom-$(Get-Date -Format 'yyyyMMdd-HHmmss').npz"
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "simuler", $Config, "--sortie", $Sortie) -MoreArgs @()
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "rejouer", $Sortie) -MoreArgs $Options
    }

    "comparer" {
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "comparer-piscine", "experiments/piscine.yaml", "--graines", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10") -MoreArgs @()
    }

    "campagne-finale" {
        Invoke-Py -BaseArgs @("-m", "viscocrowd.cli", "rejouer-campagne", "experiments/campagne-finale.yaml", "--sortie", "data/finale") -MoreArgs $ExtraArgs
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

    "maquette" {
        Write-Host "==> Ouverture de la maquette..." -ForegroundColor Green
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
