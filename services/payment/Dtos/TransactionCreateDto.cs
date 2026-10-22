using System.Text.Json.Serialization;

namespace PaymentService.Dtos;

public class TransactionCreateDto
{
    [JsonPropertyName("payer_user_id")]
    public int? PayerUserId { get; set; }

    [JsonPropertyName("account_id")]
    public Guid? AccountId { get; set; }

    [JsonPropertyName("payer_name")]
    public string PayerName { get; set; } = string.Empty;

    [JsonPropertyName("payer_email")]
    public string PayerEmail { get; set; } = string.Empty;

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
