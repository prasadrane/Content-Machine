# Cloudflare Workers AI setup on Windows

Verified against official documentation on November 6, 2026 UTC. Cloudflare is the selected first evaluation provider. These steps prepare account access. The compatible application adapter and live editorial evaluation have their own implementation checkpoints.

## 1. Create the account and token

1. Sign in to the Cloudflare dashboard and open Workers AI.
2. Review the Workers plan and daily usage. The free allocation is 10,000 neurons per day, resetting at 00:00 UTC. Select a model eligible for free inference. The pricing page identifies models requiring paid billing.
3. Choose **Use REST API**, then **Create a Workers AI API Token**.
4. Name the token `Content Machine evaluation`. Review its Workers AI Read and Edit permissions and restrict Account Resources to the selected account. Set an expiry suitable for evaluation.
5. Create the token and copy it for the secure PowerShell prompt in the next step.
6. Copy the Account ID shown on the Workers AI REST API page.

Official instructions cover the token template and required permissions. [REST setup](https://developers.cloudflare.com/workers-ai/get-started/rest-api/) · [Pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)

## 2. Save access for the local controller

Run this in Windows PowerShell under the same Windows account used for Codex. Enter the Account ID and paste the token only into the masked token prompt. Windows protects the exported credential using DPAPI tied to this Windows user and computer.

```powershell
$cfRepository = 'C:\Users\mamat\Github\Content-Machine'
$cfCredentialPath = Join-Path $cfRepository '.orchestration\controller\cloudflare.credentials.clixml'

git -C $cfRepository check-ignore --quiet -- $cfCredentialPath
if ($LASTEXITCODE -ne 0) {
    throw 'The controller credential location must be Git-ignored.'
}

$cfAccountId = Read-Host 'Cloudflare Account ID'
if ($cfAccountId -notmatch '^[a-fA-F0-9]{32}$') {
    throw 'Copy the 32-character Account ID from Workers AI.'
}
$cfSecureToken = Read-Host 'Workers AI API token' -AsSecureString
if ($cfSecureToken.Length -eq 0) {
    throw 'An API token is required.'
}

$cfCredential = [System.Management.Automation.PSCredential]::new(
    $cfAccountId,
    $cfSecureToken
)
$cfCredential | Export-Clixml -LiteralPath $cfCredentialPath
Remove-Variable cfCredential, cfSecureToken
Write-Output 'Cloudflare credential saved for the local controller.'
```

The controller loads this credential explicitly for bounded live checks. Freebuff receives source, test fixtures and redacted results. The offline-test guard blocks access to this credential file and real repository `.env` files. It also disables dotenv discovery while offline tests run.

## 3. Verify token status

This read-only request checks the user token's active status. Workers AI permission, selected-account access, model eligibility and response quality are covered by the later live inference check. [Token verification endpoint](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)

```powershell
$cfCredentialPath = 'C:\Users\mamat\Github\Content-Machine\.orchestration\controller\cloudflare.credentials.clixml'
$cfCredential = Import-Clixml -LiteralPath $cfCredentialPath
$cfHeaders = @{
    Authorization = 'Bearer ' + $cfCredential.GetNetworkCredential().Password
}
try {
    $cfVerification = Invoke-RestMethod `
        -Method Get `
        -Uri 'https://api.cloudflare.com/client/v4/user/tokens/verify' `
        -Headers $cfHeaders `
        -TimeoutSec 30
    [pscustomobject]@{
        RequestSucceeded = [bool]$cfVerification.success
        TokenActive = ($cfVerification.result.status -eq 'active')
    }
} catch {
    Write-Output 'Token verification failed. Review token status and permissions in Cloudflare.'
} finally {
    Remove-Variable cfCredential, cfHeaders, cfVerification -ErrorAction SilentlyContinue
}
```

The expected result has both fields set to `True`. The commands print status fields and keep the token value out of console output.

## 4. Hand off the configured account

After saving the credential, tell Codex **Cloudflare credentials are ready**. Codex can then verify credential presence, ask Freebuff to implement the adapter using mocked HTTP tests, independently review it and run the bounded source-grounded live evaluation. The controller supplies the account ID and token to its own live process through `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`.

The compatible API base is `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1`. The initial text adapter uses `/chat/completions` and an explicit current model ID. [Compatible API](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/)

## Completion checks

- The chosen account's Workers plan and remaining allocation have been reviewed.
- The token is scoped to Workers AI on that account.
- The controller credential file exists at the exact ignored path above.
- Token verification reports success and active status.
- The subsequent live report identifies the actual model and records grounding, structured-output validity, latency and usage.

Provider comparison and the evaluation sequence are in [the research note](../research/free-ai-providers-2026-11-06.md).
