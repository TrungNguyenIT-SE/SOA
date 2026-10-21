using System.Net.Http.Json;

namespace PaymentService.Clients;

public class TuitionHttpClient
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _config;
    private readonly ILogger<TuitionHttpClient> _logger;

    public TuitionHttpClient(HttpClient httpClient, IConfiguration config, ILogger<TuitionHttpClient> logger)
    {
        _httpClient = httpClient;
        _config = config;
        _logger = logger;
    }

    public async Task<bool> SyncStudentStatusAsync(string studentCode, string status)
    {
        try
        {
            var tuitionUrl = _config["TuitionServiceUrl"] ?? "http://tuition:8000";
            var token = _config["InternalToken"] ?? "dev-only-internal-token";

            var cleanCode = studentCode.Trim().ToUpper();
            var url = $"{tuitionUrl}/internal/v1/students/{cleanCode}/sync-status";
            using var req = new HttpRequestMessage(HttpMethod.Post, url);
            req.Headers.Add("X-Internal-Token", token);
            req.Content = JsonContent.Create(new { status = status });

            var resp = await _httpClient.SendAsync(req);
            if (resp.IsSuccessStatusCode)
            {
                _logger.LogInformation("[SYNC SUCCESS] Student: {StudentCode}, Status: {Status}", cleanCode, status);
                return true;
            }
            _logger.LogWarning("[SYNC FAILED] Student: {StudentCode}, Status: {StatusCode}", cleanCode, resp.StatusCode);
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[SYNC ERROR] Student: {StudentCode}", studentCode);
            return false;
        }
    }
}
