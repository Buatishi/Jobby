param(
    [string]$Python = "python",
    [string]$Pnpm = "pnpm"
)

$ErrorActionPreference = "Stop"

Write-Host "Installing Python backend dependencies..."
& $Python -m pip install -r requirements.txt

Write-Host "Installing Playwright browser runtime..."
& $Python -m playwright install chromium

Write-Host "Installing Node workspace dependencies..."
& $Pnpm install

Write-Host "Installation complete."
