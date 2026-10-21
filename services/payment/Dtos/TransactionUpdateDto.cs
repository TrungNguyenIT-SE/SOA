using System.Text.Json.Serialization;

namespace PaymentService.Dtos;

public class TransactionUpdateDto
{
    [JsonPropertyName("status")]
    public string? Status { get; set; }

    [JsonPropertyName("amount")]
    public long? Amount { get; set; }

    [JsonPropertyName("student_name")]
    public string? StudentName { get; set; }

    [JsonPropertyName("term")]
    public string? Term { get; set; }

    [JsonPropertyName("failure_code")]
    public string? FailureCode { get; set; }
}
