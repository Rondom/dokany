param(
    [Parameter(Mandatory=$false)][String] $Version = (New-Object System.Version (Get-Content version.txt))
)

function Exec-External {
  param(
        [Parameter(Position=0,Mandatory=1)][scriptblock] $command
  )
  & $command
  if ($LASTEXITCODE -ne 0) {
        throw ("Command returned non-zero error-code ${LASTEXITCODE}: $command")
  }
}

Exec-External {doxygen}

