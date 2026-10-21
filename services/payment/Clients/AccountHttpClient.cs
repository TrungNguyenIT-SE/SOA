using System.Net.Http.Json;

namespace PaymentService.Clients;

public class AccountHttpClient
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _config;
    private readonly ILogger<AccountHttpClient> _logger;

    public AccountHttpClient(HttpClient httpClient, IConfiguration config, ILogger<AccountHttpClient> logger)
    {
        _httpClient = httpClient;
        _config = config;
        _logger = logger;
    }

    public async Task<bool> RefundAccountAsync(Guid accountId, int payerUserId, Guid paymentId, long amount, string description)
    {
        try
        {
            var accountUrl = _config["AccountServiceUrl"] ?? "http://account:8000";
            var token = _config["InternalToken"] ?? "dev-only-internal-token";

            if (accountId == Guid.Empty && payerUserId > 0)
            {
                using var userReq = new HttpRequestMessage(HttpMethod.Get, $"{accountUrl}/internal/v1/accounts/by-user/{payerUserId}");
                userReq.Headers.Add("X-Internal-Token", token);
                var userResp = await _httpClient.SendAsync(userReq);
                if (userResp.IsSuccessStatusCode)
                {
                    var userAccount = await userResp.Content.ReadFromJsonAsync<System.Text.Json.Nodes.JsonObject>();
                    if (userAccount != null && userAccount["id"] != null)
                    {
                        accountId = Guid.Parse(userAccount["id"]!.ToString());
                    }
                }
            }

            var url = $"{accountUrl}/internal/v1/accounts/{accountId}/compensating-credits";
            using var req = new HttpRequestMessage(HttpMethod.Post, url);
            req.Headers.Add("X-Internal-Token", token);
            req.Content = JsonContent.Create(new
            {
                payment_id = paymentId.ToString(),
                amount = amount,
                description = description
            });

            var resp = await _httpClient.SendAsync(req);
            if (resp.IsSuccessStatusCode)
            {
                _logger.LogInformation("[REFUND SUCCESS] Account: {AccountId}, Amount: {Amount}", accountId, amount);
                return true;
            }
            _logger.LogWarning("[REFUND FAILED] Account: {AccountId}, Status: {StatusCode}", accountId, resp.StatusCode);
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[REFUND ERROR] Account: {AccountId}", accountId);
            return false;
        }
    }
}
