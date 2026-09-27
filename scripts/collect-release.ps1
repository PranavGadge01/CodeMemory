param([string]$Destination = "build/release")
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$release = Get-Content -LiteralPath (Join-Path $repoRoot "release.json") -Raw | ConvertFrom-Json
$destinationPath = [IO.Path]::GetFullPath((Join-Path $repoRoot $Destination))
New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
$bundleRoot = Join-Path $repoRoot "frontend/src-tauri/target/release/bundle"
$checksums = @()
foreach ($artifact in $release.platforms[0].artifacts) {
    $name = $artifact.file.Replace('{version}', $release.version)
    $source = Get-ChildItem -LiteralPath $bundleRoot -Recurse -File | Where-Object { $_.Name -eq $name }
    if (@($source).Count -ne 1) { throw "Expected one built artifact: $name" }
    $target = Join-Path $destinationPath $name
    Copy-Item -LiteralPath $source.FullName -Destination $target -Force
    $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash.ToLower()) { throw "Copy verification failed: $name" }
    $checksums += "$hash  $name"
}
$checksums | Set-Content -LiteralPath (Join-Path $destinationPath "SHA256SUMS.txt") -Encoding utf8
Write-Output "Verified release artifacts: $destinationPath"
