using Microsoft.EntityFrameworkCore;
using Microsoft.OpenApi.Models;
using PaymentService.Clients;
using PaymentService.Models;

var builder = WebApplication.CreateBuilder(args);

// Port configuration
builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenAnyIP(8000);
});

// Add DbContext
var connectionString = builder.Configuration.GetConnectionString("PaymentDb")
    ?? "Host=postgres;Port=5432;Database=payment_db;Username=soa;Password=soa_dev_password";

builder.Services.AddDbContext<PaymentDbContext>(options =>
    options.UseNpgsql(connectionString));

// Register HttpClients
builder.Services.AddHttpClient<AccountHttpClient>();
builder.Services.AddHttpClient<TuitionHttpClient>();

// Add Controllers
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.SnakeCaseLower;
    });

// Add Swagger / OpenAPI
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "Quản lý Lịch sử giao dịch & Hoàn tiền (Phong)",
        Version = "v1",
        Description = "Microservice phụ trách Quản lý Lịch sử giao dịch thanh toán và Xử lý hoàn tiền cho người nộp (C# 12 - ASP.NET Core 8)."
    });
    c.DocumentFilter<PaymentTagDescriptionsDocumentFilter>();
});

var app = builder.Build();

// Ensure Database is created if needed
using (var scope = app.Services.CreateScope())
{
    try
    {
        var db = scope.ServiceProvider.GetRequiredService<PaymentDbContext>();
        db.Database.EnsureCreated();
    }
    catch (Exception ex)
    {
        Console.WriteLine($"[DB WARN] EnsureCreated: {ex.Message}");
    }
}

app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.SwaggerEndpoint("/swagger/v1/swagger.json", "Phong - Transactions API v1");
    c.RoutePrefix = "swagger";
});

app.UseAuthorization();
app.MapControllers();

app.Run();

public class PaymentTagDescriptionsDocumentFilter : Swashbuckle.AspNetCore.SwaggerGen.IDocumentFilter
{
    public void Apply(OpenApiDocument swaggerDoc, Swashbuckle.AspNetCore.SwaggerGen.DocumentFilterContext context)
    {
        swaggerDoc.Tags = new List<OpenApiTag>
        {
            new OpenApiTag
            {
                Name = "Người dùng - Giao dịch (User)",
                Description = "Dịch vụ Tra cứu và Ghi nhận Lịch sử nộp học phí của Người dùng (Phong)."
            },
            new OpenApiTag
            {
                Name = "Quản trị - Lịch sử giao dịch (Admin)",
                Description = "Quản trị Toàn bộ Lịch sử Giao dịch và Xử lý Hoàn tiền SAGA / Giao dịch bồi hoàn tự động (Phong)."
            }
        };
    }
}
