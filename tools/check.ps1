$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "."

Write-Host "== Линтер контракта стиля ==" -ForegroundColor Magenta
python tools/lint_rules.py app projects tools tests
$lint = $LASTEXITCODE

Write-Host "== Тесты ==" -ForegroundColor Magenta
python -m pytest -q
$tests = $LASTEXITCODE

Write-Host "== Дымовой прогон API ==" -ForegroundColor Magenta
python tools/smoke.py
$smoke = $LASTEXITCODE

Write-Host "== Аудит фронтенда ==" -ForegroundColor Magenta
python tools/audit_ui.py
$audit = $LASTEXITCODE

$node = "C:\Program Files\nodejs\node.exe"
if (Test-Path $node) {
    Write-Host "== Синтаксис ES-модулей ==" -ForegroundColor Magenta
    $failed = 0
    Get-ChildItem -Recurse -Filter *.js "app\static" | ForEach-Object {
        & $node --check $_.FullName
        if ($LASTEXITCODE -ne 0) { $failed = $failed + 1; Write-Host ("FAIL " + $_.Name) -ForegroundColor Red }
    }
    Write-Host ("модулей с ошибками: " + $failed)
} else {
    Write-Host "Node.js не найден: проверка синтаксиса фронтенда пропущена" -ForegroundColor Yellow
}

if ($lint -ne 0 -or $tests -ne 0 -or $smoke -ne 0) {
    Write-Host "ЕСТЬ ЗАМЕЧАНИЯ" -ForegroundColor Red
    exit 1
}
Write-Host "ВСЕ ПРОВЕРКИ ЗЕЛЕНЫЕ" -ForegroundColor Green
