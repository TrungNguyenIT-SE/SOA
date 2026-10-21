using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PaymentService.Clients;
using PaymentService.Dtos;
using PaymentService.Models;

namespace PaymentService.Controllers;

[ApiController]
[Route("api/v1/admin/transactions")]
[Tags("Quản trị - Lịch sử giao dịch (Admin)")]
public class AdminTransactionsController : ControllerBase
{
    private readonly PaymentDbContext _db;
    private readonly AccountHttpClient _accountClient;
    private readonly TuitionHttpClient _tuitionClient;
    private readonly ILogger<AdminTransactionsController> _logger;

    public AdminTransactionsController(
        PaymentDbContext db,
        AccountHttpClient accountClient,
        TuitionHttpClient tuitionClient,
        ILogger<AdminTransactionsController> logger)
    {
        _db = db;
        _accountClient = accountClient;
        _tuitionClient = tuitionClient;
        _logger = logger;
    }

    [HttpGet]
    [EndpointSummary("Xem toàn bộ danh sách giao dịch thanh toán trong hệ thống")]
    public async Task<ActionResult<List<TransactionOutDto>>> ListAdminTransactions()
    {
        var items = await _db.Transactions
            .OrderByDescending(p => p.CreatedAt)
            .ToListAsync();

        return Ok(items.Select(TransactionOutDto.FromEntity).ToList());
    }

    [HttpGet("{id:guid}")]
    [EndpointSummary("Xem chi tiết giao dịch theo ID (Dành cho Quản trị viên)")]
    public async Task<ActionResult<TransactionOutDto>> GetAdminTransaction(Guid id)
    {
        var tx = await _db.Transactions.FindAsync(id);
        if (tx == null)
        {
            return NotFound(new { code = "TRANSACTION_NOT_FOUND", message = "Không tìm thấy giao dịch: " + id });
        }
        return Ok(TransactionOutDto.FromEntity(tx));
    }

    [HttpPut("{id:guid}")]
    [EndpointSummary("Cập nhật thông tin hoặc trạng thái giao dịch (Hoàn tiền / Succeeded / Compensated)")]
    public async Task<ActionResult<TransactionOutDto>> UpdateTransaction(Guid id, [FromBody] TransactionUpdateDto dto)
    {
        var tx = await _db.Transactions.FindAsync(id);
        if (tx == null)
        {
            return NotFound(new { code = "TRANSACTION_NOT_FOUND", message = "Không tìm thấy giao dịch: " + id });
        }

        var oldStatus = tx.Status;
        if (!string.IsNullOrEmpty(dto.Status))
        {
            tx.Status = dto.Status.Trim().ToUpper();
            if (tx.Status == "SUCCEEDED" && tx.CompletedAt == null)
            {
                tx.CompletedAt = DateTime.UtcNow;
            }
        }
        if (dto.Amount.HasValue) tx.Amount = dto.Amount.Value;
        if (!string.IsNullOrEmpty(dto.StudentName)) tx.StudentName = dto.StudentName.Trim();
        if (!string.IsNullOrEmpty(dto.Term)) tx.Term = dto.Term.Trim();
        if (dto.FailureCode != null) tx.FailureCode = dto.FailureCode.Trim();

        await _db.SaveChangesAsync();

        if (!string.IsNullOrEmpty(dto.Status) && !string.IsNullOrEmpty(tx.StudentCode))
        {
            if (tx.Status == "SUCCEEDED")
            {
                await _tuitionClient.SyncStudentStatusAsync(tx.StudentCode, "PAID");
            }
            else if (oldStatus == "SUCCEEDED" && tx.Status != "SUCCEEDED")
            {
                var otherSucceeded = await _db.Transactions.AnyAsync(p => p.StudentCode == tx.StudentCode && p.Status == "SUCCEEDED" && p.Id != tx.Id);
                if (!otherSucceeded)
                {
                    await _tuitionClient.SyncStudentStatusAsync(tx.StudentCode, "UNPAID");
                }
            }
        }

        return Ok(TransactionOutDto.FromEntity(tx));
    }

    [HttpDelete("{id:guid}")]
    [EndpointSummary("Xóa giao dịch khỏi hệ thống & Hoàn tiền cho người nộp")]
    public async Task<IActionResult> DeleteTransaction(Guid id)
    {
        var tx = await _db.Transactions.FindAsync(id);
        if (tx == null)
        {
            return NotFound(new { code = "TRANSACTION_NOT_FOUND", message = "Không tìm thấy giao dịch: " + id });
        }

        var studentCode = tx.StudentCode;
        var wasSucceeded = tx.Status == "SUCCEEDED";
        var amount = tx.Amount;
        var accountId = tx.AccountId;

        // 1. Nếu là giao dịch đã thanh toán thành công -> HOÀN TIỀN NGƯỜI NỘP
        if (wasSucceeded)
        {
            _logger.LogInformation("[REFUND ON DELETE] Refunding {Amount} to Account {AccountId} for tx {Id}", amount, accountId, id);
            await _accountClient.RefundAccountAsync(accountId, tx.PayerUserId, id, amount, $"Hoàn tiền do hủy giao dịch {id.ToString()[..8].ToUpper()}");

            // 2. Chuyển học phí sinh viên về CHƯA NỘP nếu không còn giao dịch thành công nào khác
            if (!string.IsNullOrEmpty(studentCode))
            {
                var otherSucceeded = await _db.Transactions.AnyAsync(p => p.StudentCode == studentCode && p.Status == "SUCCEEDED" && p.Id != id);
                if (!otherSucceeded)
                {
                    await _tuitionClient.SyncStudentStatusAsync(studentCode, "UNPAID");
                }
            }
        }

        // 3. Xóa giao dịch khỏi cơ sở dữ liệu
        _db.Transactions.Remove(tx);
        await _db.SaveChangesAsync();

        return Ok(new
        {
            status = "success",
            message = $"Đã xóa giao dịch {id.ToString()[..8].ToUpper()}, hoàn lại {amount:N0} đ cho người nộp và chuyển học phí sinh viên về Chưa nộp."
        });
    }
}
