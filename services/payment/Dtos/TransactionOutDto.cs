using System.Text.Json.Serialization;
using PaymentService.Models;

namespace PaymentService.Dtos;

public class TransactionOutDto
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("payer_user_id")]
    public int PayerUserId { get; set; }

    [JsonPropertyName("payer_name")]
    public string PayerName { get; set; } = string.Empty;

    [JsonPropertyName("payer_email")]
    public string PayerEmail { get; set; } = string.Empty;

    [JsonPropertyName("student_code")]
    public string StudentCode { get; set; } = string.Empty;

    [JsonPropertyName("student_name")]
    public string StudentName { get; set; } = string.Empty;

    [JsonPropertyName("term")]
    public string Term { get; set; } = string.Empty;

    [JsonPropertyName("amount")]
    public long Amount { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("failure_code")]
    public string? FailureCode { get; set; }

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; set; } = string.Empty;

    [JsonPropertyName("completed_at")]
    public string? CompletedAt { get; set; }

    public static TransactionOutDto FromEntity(PaymentTransaction p)
    {
        return new TransactionOutDto
        {
            Id = p.Id.ToString(),
            PayerUserId = p.PayerUserId,
            PayerName = p.PayerName,
            PayerEmail = p.PayerEmail,
            StudentCode = p.StudentCode,
            StudentName = p.StudentName,
            Term = p.Term,
            Amount = p.Amount,
            Status = p.Status,
            FailureCode = p.FailureCode,
            CreatedAt = p.CreatedAt.ToString("o"),
            CompletedAt = p.CompletedAt?.ToString("o")
        };
    }
}
