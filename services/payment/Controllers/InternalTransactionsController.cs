using Microsoft.AspNetCore.Mvc;
using PaymentService.Dtos;
using PaymentService.Models;
using System.Text.Json.Serialization;

namespace PaymentService.Controllers;

[ApiController]
[ApiExplorerSettings(IgnoreApi = true)]
public class InternalTransactionsController : ControllerBase
{
    private readonly PaymentDbContext _db;
    private readonly ILogger<InternalTransactionsController> _logger;

    public InternalTransactionsController(PaymentDbContext db, ILogger<InternalTransactionsController> logger)
    {
        _db = db;
        _logger = logger;
    }

    public class RecordTxRequest
    {
        [JsonPropertyName("id")]
        public string? Id { get; set; }

        [JsonPropertyName("payer_user_id")]
        public int PayerUserId { get; set; } = 1;

        [JsonPropertyName("account_id")]
        public string? AccountId { get; set; }

        [JsonPropertyName("payer_name")]
        public string PayerName { get; set; } = "Người nộp";

        [JsonPropertyName("payer_email")]
        public string PayerEmail { get; set; } = "user@example.com";

        [JsonPropertyName("student_code")]
        public string StudentCode { get; set; } = string.Empty;

        [JsonPropertyName("student_name")]
        public string StudentName { get; set; } = string.Empty;

        [JsonPropertyName("term")]
        public string Term { get; set; } = "HK1/2026-2027";

        [JsonPropertyName("amount")]
        public long Amount { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = "SUCCEEDED";
    }

    [HttpPost("internal/v1/transactions/record")]
    public async Task<IActionResult> RecordTransaction([FromBody] RecordTxRequest req)
    {
        var id = !string.IsNullOrEmpty(req.Id) && Guid.TryParse(req.Id, out var parsed) ? parsed : Guid.NewGuid();
        var accountId = !string.IsNullOrEmpty(req.AccountId) && Guid.TryParse(req.AccountId, out var accGuid) ? accGuid : Guid.Empty;
        var now = DateTime.UtcNow;

        var tx = new PaymentTransaction
        {
            Id = id,
            PayerUserId = req.PayerUserId,
            PayerName = req.PayerName,
            PayerEmail = req.PayerEmail,
            AccountId = accountId,
            TuitionInvoiceId = Guid.NewGuid(),
            StudentCode = req.StudentCode.Trim().ToUpper(),
            StudentName = req.StudentName.Trim(),
            Term = req.Term.Trim(),
            Amount = req.Amount,
            Status = req.Status.ToUpper(),
            SagaStep = "COMPLETED",
            CreatedAt = now,
            CompletedAt = now
        };

        _db.Transactions.Add(tx);
        await _db.SaveChangesAsync();
        _logger.LogInformation("[RECORD TRANSACTION SUCCESS] ID: {Id}, Student: {Code}, Amount: {Amount}", id, req.StudentCode, req.Amount);

        return Ok(new { status = "success", id = id.ToString() });
    }
}
