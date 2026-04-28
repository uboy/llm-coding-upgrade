param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 (Join-Path $ScriptDir "model_suite.py") @Args
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python (Join-Path $ScriptDir "model_suite.py") @Args
    exit $LASTEXITCODE
}

throw "Python 3 is required to run model_suite.py"
