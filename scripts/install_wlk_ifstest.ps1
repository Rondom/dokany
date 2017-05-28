# How to prevent downloading gigabytes of stuff (I am sure there are easier ways)
# Step 4 and 5 are not necessary if you already know that you need HLK Filter.Driver Content-x86_en-us.msi
# 1. Get the desired version of HLKSetup.exe
# 2. Run exe, choose to download only, log downloaded urls with proxy
#    (probably there also exist some logs with the urls, but that was the easiest for me)
# 3. Install lessmsi: choco install lessmsi
# 4. Extract all MSIs (lessmsi will create a dir for each MSI-package)
#        Get-ChildItem -Filter *.msi | ForEach-Object { & lessmsi x $_.FullName }
# 5. Search the files you need in those folders
# 6. Try putting only the MSI in an empty dir and see if LessMSI can still extract it.
#    There might be cab-files required in the same directory. Add the cabs, rinse and repeat.
#
Set-StrictMode -Version 2
# TODO: I have not managed to change the installation path
# $installation_dir = ''
$log_file = "ifstest_install.log"
$temp_dir = '.\ifstest_installer'
if (Get-Item env:WLK_INST_CACHE -ErrorAction SilentlyContinue) {
    $temp_dir = $env:WLK_INST_CACHE
}

$base_url = 'http://download.microsoft.com/download/7/A/F/7AFE783C-59E6-49F9-80B4-D2F49917FFE6/hlk/Installers/'
$dl_files = @{
    'HLK Filter.Driver Content-x86_en-us.msi' = '10DD59CA8B47320C685EA6FBEB64BC4548AFCCE3D7CF7E143CEA68618A679D62';
    '4c5579196433c53cc1ec3d7b40ae5fd2.cab' = '233ED34266101E2D88BB3C6EA032DC6321B83F39A7EDBB8356DF3104B241CCCF';
    '6119459287e24c3503279ff684647c83.cab' = '32CD817A442181325F513DE3D30FAE62D2AFE4A3136CDD3BC57EA365AFE54C69';
    'e54a669f7bfb1c6c6ee7bba08b02a6dc.cab' = 'FFABDD814B114457A084B80BEAC4500B2C64AD7F55007495D9551EA53CE18485';
    'fd0d8d2173424e55667bc3e935e1e376.cab' = 'ADBC46F9064B5DFCC94681B1210ACDCA255646DD434EF3AFDF3FD9BFB303BFA4'
}
$installer_file = "HLK Filter.Driver Content-x86_en-us.msi"

New-Item -Type Directory -Force $temp_dir | Out-Null
foreach ($kv in $dl_files.GetEnumerator()) {
    $dl_filename = $kv.Name
    $sha256 = $kv.Value
    $out_file = "${temp_dir}/${dl_filename}"
    $url = "${base_url}/${dl_filename}"
    if ( !(Test-Path $out_file) -Or $(Get-FileHash -Algorithm SHA256 $out_file).Hash -ne $sha256) {
        Write-Host "File $out_file not existing or hash not matching, downloading..."
        Invoke-WebRequest $url -OutFile $out_file
    }
    else {
        Write-Host "Skipping already downloaded file $out_file"
    }
}

Write-Host Installing MSI
Push-Location $temp_dir
$msi_proc = Start-Process -PassThru -Wait -FilePath msiexec.exe -ArgumentList @("/qn", "/norestart", "/lv*", $log_file, "/i", "`"$installer_file`"")
Pop-Location
if ($msi_proc.ExitCode -ne 0) {
    Write-Error "IFSTest-Installation failed. Log below this line:"
    Get-Content $log_file
    throw "IFSTest-Installation failed. Log above this line"
}

# We copy some files into the same dir as the exe.
# Setting the PATH is cumbersome, because IFSTest launches itself under a different user for some tests!
$nttest_path = "C:\Program Files (x86)\Windows Kits\10\Hardware Lab Kit\Tests\${env:PROCESSOR_ARCHITECTURE}\NTTEST"
$ifstest_dir = "${nttest_path}\BASETEST\core_file_services\ifs_test_kit\"
$needed_files = @(
    "${nttest_path}\BASETEST\core_file_services\shared_libs\fbslog\FbsLog.dll",
    "${nttest_path}\commontest\ntlog\ntlogger.ini"
    "${nttest_path}\commontest\ntlog\ntlog.dll"
)
Copy-Item $needed_files $ifstest_dir

Write-Host "Installation successful."
