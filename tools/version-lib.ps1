# Shared by version-bump/build/package. src/version.h is the sole version source.
function Get-FolderpadVersion([string]$Root) {
    $text = [IO.File]::ReadAllText((Join-Path $Root 'src/version.h'))
    $parts = foreach ($name in @('MAJOR','MINOR','PATCH')) {
        $matches = [regex]::Matches($text, "(?m)^#define FOLDERPAD_VERSION_$name (0|[1-9][0-9]*)\r?$")
        if ($matches.Count -ne 1) { throw "Invalid or duplicate version component: $name" }
        $value = [int]::Parse($matches[0].Groups[1].Value)
        if ($value -gt 65535) { throw 'Version components must be between 0 and 65535 (Windows VERSIONINFO).' }
        $value
    }
    return $parts -join '.'
}
