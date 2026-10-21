using Microsoft.AspNetCore.Mvc;

namespace PaymentService.Controllers;

[ApiController]
[ApiExplorerSettings(IgnoreApi = true)]
public class HealthController : ControllerBase
{
    [HttpGet("health")]
    public IActionResult Health()
    {
        return Ok(new { status = "ok", service = "payment" });
    }

    [HttpGet("ready")]
    public IActionResult Ready()
    {
        return Ok(new { status = "ready", service = "payment" });
    }

    [HttpGet("docs")]
    public IActionResult Docs()
    {
        return Redirect("/swagger/index.html");
    }
}
