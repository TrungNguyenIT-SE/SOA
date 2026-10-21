using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PaymentService.Clients;
using PaymentService.Dtos;
using PaymentService.Models;
using System.Security.Cryptography;
using System.Text;

namespace PaymentService.Controllers;

[ApiController]
[Route("api/v1/transactions")]
[Tags("Người dùng - Giao dịch (User)")]
public class TransactionsController : ControllerBase
{
    private readonly PaymentDbContext _db;
    private readonly TuitionHttpClient _tuitionClient;
    private readonly ILogger<TransactionsController> _logger;

    public TransactionsController(
        PaymentDbContext db,
        TuitionHttpClient tuitionClient,
        ILogger<TransactionsController> logger)
    {
        _db = db;
        _tuitionClient = tuitionClient;
        _logger = logger;
    }

    [HttpGet]
    [EndpointSummary("Xem danh sách lịch sử giao dịch thanh toán")]
    public async Task<ActionResult<List<TransactionOutDto>>> ListTransactions()
    {
        var items = await _db.Transactions
            .OrderByDescending(p => p.CreatedAt)
            .ToListAsync();

        return Ok(items.Select(TransactionOutDto.FromEntity).ToList());
    }

    [HttpPost]
    [EndpointSummary("Tạo bản ghi giao dịch thanh toán mới")]
    public async Task<ActionResult<TransactionOutDto>> CreateTransaction([FromBody] TransactionCreateDto dto)
    {
        var paymentId = Guid.NewGuid();
        var now = DateTime.UtcNow;

        var tx = new PaymentTransaction
        {
            Id = paymentId,
            PayerUserId = 1,
            PayerName = dto.PayerName.Trim(),
            PayerEmail = dto.PayerEmail.Trim(),
            AccountId = Guid.NewGuid(),
            TuitionInvoiceId = Guid.NewGuid(),
            StudentCode = dto.StudentCode.Trim().ToUpper(),
            StudentName = dto.StudentName.Trim(),
            Term = dto.Term.Trim(),
            Amount = dto.Amount,
            Status = dto.Status.Trim().ToUpper(),
            IdempotencyKey = Guid.NewGuid().ToString(),
            RequestHash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(paymentId.ToString()))).ToLower(),
            CorrelationId = Guid.NewGuid().ToString(),
            SagaStep = dto.Status.ToUpper() == "SUCCEEDED" ? "COMPLETED" : "CREATED",
            CreatedAt = now,
            CompletedAt = dto.Status.ToUpper() == "SUCCEEDED" ? now : null
        };

        _db.Transactions.Add(tx);
        await _db.SaveChangesAsync();

        if (tx.Status == "SUCCEEDED" && !string.IsNullOrEmpty(tx.StudentCode))
        {
            await _tuitionClient.SyncStudentStatusAsync(tx.StudentCode, "PAID");
        }

        return CreatedAtAction(nameof(GetTransaction), new { id = tx.Id }, TransactionOutDto.FromEntity(tx));
    }

    [HttpGet("{id:guid}")]
    [EndpointSummary("Tra cứu chi tiết một giao dịch theo Transaction ID")]
    public async Task<ActionResult<TransactionOutDto>> GetTransaction(Guid id)
    {
        var tx = await _db.Transactions.FindAsync(id);
        if (tx == null)
        {
            return NotFound(new { code = "TRANSACTION_NOT_FOUND", message = "Không tìm thấy giao dịch với ID: " + id });
        }
        return Ok(TransactionOutDto.FromEntity(tx));
    }
}

