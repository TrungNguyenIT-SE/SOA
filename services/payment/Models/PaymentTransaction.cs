using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace PaymentService.Models;

[Table("payments")]
public class PaymentTransaction
{
    [Key]
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Column("payer_user_id")]
    public int PayerUserId { get; set; } = 1;

    [Column("payer_name")]
    [MaxLength(160)]
    public string PayerName { get; set; } = string.Empty;

    [Column("payer_email")]
    [MaxLength(254)]
    public string PayerEmail { get; set; } = string.Empty;

    [Column("account_id")]
    public Guid AccountId { get; set; } = Guid.NewGuid();

    [Column("tuition_invoice_id")]
    public Guid TuitionInvoiceId { get; set; } = Guid.NewGuid();

    [Column("student_code")]
    [MaxLength(20)]
    public string StudentCode { get; set; } = string.Empty;

    [Column("student_name")]
    [MaxLength(160)]
    public string StudentName { get; set; } = string.Empty;

    [Column("term")]
    [MaxLength(40)]
    public string Term { get; set; } = "HK1/2026-2027";

    [Column("amount")]
    public long Amount { get; set; }

    [Column("status")]
    [MaxLength(32)]
    public string Status { get; set; } = "SUCCEEDED";

    [Column("failure_code")]
    [MaxLength(64)]
    public string? FailureCode { get; set; }

    [Column("idempotency_key")]
    [MaxLength(64)]
    public string IdempotencyKey { get; set; } = Guid.NewGuid().ToString();

    [Column("request_hash")]
    [MaxLength(64)]
    public string RequestHash { get; set; } = string.Empty;

    [Column("correlation_id")]
    [MaxLength(64)]
    public string CorrelationId { get; set; } = Guid.NewGuid().ToString();

    [Column("saga_step")]
    [MaxLength(32)]
    public string SagaStep { get; set; } = "COMPLETED";

    [Column("recovery_attempts")]
    public int RecoveryAttempts { get; set; } = 0;

    [Column("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    [Column("updated_at")]
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;

    [Column("completed_at")]
    public DateTime? CompletedAt { get; set; } = DateTime.UtcNow;
}
