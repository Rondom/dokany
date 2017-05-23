Set-StrictMode -Version 2
#TODO: Get Path via some MSI-CmdLet or Registry instead of hardcoding it
$nttest_path = "C:\Program Files (x86)\Windows Kits\10\Hardware Lab Kit\Tests\${env:PROCESSOR_ARCHITECTURE}\NTTEST"
$ifstest_exe = "${nttest_path}\BASETEST\core_file_services\ifs_test_kit\ifstest.exe"

if (!(Test-Path $ifstest_exe)) {
    throw "$ifstest_exe not found!"
}

& $ifstest_exe $args

if ($LASTEXITCODE -ne 0) {
   Write-Error "Non-zero exit-code: $LASTEXITCODE"
   Exit $LASTEXITCODE
}

