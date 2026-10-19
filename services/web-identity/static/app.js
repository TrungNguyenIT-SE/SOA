const state = { token: sessionStorage.getItem("accessToken"), user: null, account: null, tuition: null, payment: null, countdown: null, resendCountdown: null, createKey: null, verifyKey: null, verifyOtp: null };
const $ = (id) => document.getElementById(id);
const money = (value) => new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(Number(value));
const uuid = () => crypto.randomUUID();
const maskAccount = (value) => value ? `Tài khoản •••• ${String(value).slice(-4)}` : "Tài khoản —";

function setLoading(button, loading) {
  button.disabled = loading;
  button.classList.toggle("is-loading", loading);
  button.setAttribute("aria-busy", String(loading));
}

function setStep(step) {
  document.querySelectorAll(".stepper li").forEach((item, index) => {
    item.classList.toggle("active", index + 1 === step);
    item.classList.toggle("done", index + 1 < step);
  });
  $("stepBadge").textContent = `Bước ${step}/3`;
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.message || "Không thể xử lý yêu cầu.");
    error.code = body.code;
    error.status = response.status;
    throw error;
  }
  return body;
}

function showMessage(message, type = "error") {
  const el = $("paymentMessage");
  el.textContent = message;
  el.className = `message ${type}`;
}

function clearMessage() { $("paymentMessage").className = "message hidden"; }

async function loadDashboard() {
  const [user, account, history] = await Promise.all([
    api("/api/v1/users/me"),
    api("/api/v1/accounts/me"),
    api("/api/v1/accounts/me/transactions"),
  ]);
  state.user = user;
  state.account = account;
  $("welcomeName").textContent = `Xin chào, ${user.full_name}`;
  $("profileEmail").textContent = user.email;
  $("profilePhone").textContent = user.phone;
  $("payerName").value = user.full_name;
  $("payerPhone").value = user.phone;
  $("payerEmail").value = user.email;
  $("availableBalance").textContent = money(account.available_balance);
  $("accountNumber").textContent = maskAccount(account.account_number);
  renderHistory(history.items || []);
}

function renderHistory(items) {
  const root = $("historyList");
  if (!items.length) { root.innerHTML = '<div class="empty">Chưa có giao dịch.</div>'; return; }
  root.innerHTML = items.map((item) => `<article class="history-item ${item.type === "DEBIT" ? "debit" : "credit"}"><strong>${item.type === "DEBIT" ? "Thanh toán học phí" : "Hoàn tiền giao dịch"}</strong><span class="amount">${item.type === "DEBIT" ? "-" : "+"}${money(item.amount)}</span><small>${new Date(item.created_at).toLocaleString("vi-VN")} · Mã GD ${item.payment_id.slice(0, 8).toUpperCase()}</small></article>`).join("");
}

function enterApp() {
  $("loginView").classList.add("hidden");
  $("appView").classList.remove("hidden");
  $("logoutButton").classList.remove("hidden");
  setStep(1);
}

function logout() {
  sessionStorage.removeItem("accessToken");
  sessionStorage.removeItem("refreshToken");
  state.token = null;
  location.reload();
}

$("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = $("loginError");
  const submitButton = event.currentTarget.querySelector('button[type="submit"]');
  errorEl.classList.add("hidden");
  setLoading(submitButton, true);
  try {
    const result = await api("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username: $("username").value, password: $("password").value }) });
    state.token = result.access;
    sessionStorage.setItem("accessToken", result.access);
    sessionStorage.setItem("refreshToken", result.refresh);
    enterApp();
    await loadDashboard();
  } catch (error) {
    errorEl.textContent = error.message;
    errorEl.classList.remove("hidden");
  } finally { setLoading(submitButton, false); }
});

$("lookupForm").addEventListener("submit", async (event) => {
  event.preventDefault(); clearMessage();
  const submitButton = event.currentTarget.querySelector('button[type="submit"]');
  setLoading(submitButton, true);
  try {
    state.tuition = await api(`/api/v1/tuition-invoices/by-student/${encodeURIComponent($("studentCode").value.trim())}`);
    state.createKey = uuid();
    $("tuitionStudentCode").textContent = state.tuition.student_code;
    $("tuitionStudentName").textContent = state.tuition.student_name;
    $("tuitionTerm").textContent = state.tuition.term;
    $("tuitionAmount").textContent = money(state.tuition.amount);
    $("tuitionCard").classList.remove("hidden");
    $("acceptTerms").checked = false;
    $("createPaymentButton").disabled = true;
    if (Number(state.account.available_balance) < Number(state.tuition.amount)) showMessage("Số dư khả dụng không đủ để thanh toán toàn bộ học phí.");
  } catch (error) { $("tuitionCard").classList.add("hidden"); showMessage(error.message); }
  finally { setLoading(submitButton, false); }
});

$("acceptTerms").addEventListener("change", (event) => { $("createPaymentButton").disabled = !event.target.checked || Number(state.account.available_balance) < Number(state.tuition.amount); });

$("createPaymentButton").addEventListener("click", async () => {
  clearMessage(); setLoading($("createPaymentButton"), true);
  try {
    state.payment = await api("/api/v1/payments", { method: "POST", headers: { "Idempotency-Key": state.createKey }, body: JSON.stringify({ student_code: state.tuition.student_code, accepted_terms: true }) });
    setLoading($("createPaymentButton"), false);
    $("lookupStep").classList.add("hidden");
    $("otpStep").classList.remove("hidden");
    setStep(2);
    $("maskedEmail").textContent = state.payment.masked_email;
    startCountdown(state.payment.otp_expires_at);
    startResendCooldown(60);
  } catch (error) { showMessage(error.message); setLoading($("createPaymentButton"), false); }
});

function startCountdown(expiresAt) {
  clearInterval(state.countdown);
  const tick = () => {
    const seconds = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
    $("otpCountdown").textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
    if (!seconds) clearInterval(state.countdown);
  };
  tick(); state.countdown = setInterval(tick, 1000);
}

function startResendCooldown(seconds) {
  clearInterval(state.resendCountdown);
  const button = $("resendOtpButton");
  let remaining = seconds;
  button.disabled = true;
  const tick = () => {
    button.textContent = remaining > 0 ? `Gửi lại OTP sau ${remaining} giây` : "Gửi lại OTP";
    button.disabled = remaining > 0;
    if (remaining <= 0) clearInterval(state.resendCountdown);
    remaining -= 1;
  };
  tick(); state.resendCountdown = setInterval(tick, 1000);
}

async function showSuccess(result) {
  clearInterval(state.countdown); clearInterval(state.resendCountdown);
  $("otpStep").classList.add("hidden"); $("resultStep").classList.remove("hidden"); setStep(3);
  $("resultTitle").textContent = "Giao dịch thành công";
  $("resultMessage").textContent = "Khoản học phí đã được thanh toán và email xác nhận đang được gửi.";
  await loadDashboard();
  $("resultDetails").innerHTML = `<dt>Mã giao dịch</dt><dd>${result.id.slice(0, 8)}</dd><dt>MSSV</dt><dd>${result.student_code}</dd><dt>Sinh viên</dt><dd>${result.student_name}</dd><dt>Số tiền</dt><dd>${money(result.amount)}</dd><dt>Số dư mới</dt><dd>${money(state.account.available_balance)}</dd><dt>Thời gian</dt><dd>${new Date(result.completed_at).toLocaleString("vi-VN")}</dd><dt>Trạng thái</dt><dd>${result.status}</dd>`;
}

async function pollPayment() {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const result = await api(`/api/v1/payments/${state.payment.id}`);
    if (result.status === "SUCCEEDED") return showSuccess(result);
    if (!["PROCESSING", "OTP_PENDING"].includes(result.status)) throw new Error(`Giao dịch kết thúc với trạng thái ${result.status}.`);
  }
  throw new Error("Giao dịch vẫn đang xử lý. Bạn có thể kiểm tra lại trong lịch sử.");
}

$("otpForm").addEventListener("submit", async (event) => {
  event.preventDefault(); clearMessage();
  const button = $("verifyOtpButton"); setLoading(button, true);
  try {
    const otp = $("otpCode").value.trim();
    if (state.verifyOtp !== otp) { state.verifyOtp = otp; state.verifyKey = uuid(); }
    const result = await api(`/api/v1/payments/${state.payment.id}/otp/verify`, { method: "POST", headers: { "Idempotency-Key": state.verifyKey }, body: JSON.stringify({ otp }) });
    await showSuccess(result);
  } catch (error) {
    if (error.code === "SAGA_RECOVERY_PENDING") { showMessage("Giao dịch đang được tự động phục hồi, vui lòng chờ…", "success"); try { await pollPayment(); } catch (pollError) { showMessage(pollError.message); } }
    else showMessage(error.message);
  } finally { setLoading(button, false); }
});

$("resendOtpButton").addEventListener("click", async () => {
  const button = $("resendOtpButton"); setLoading(button, true); clearMessage();
  try {
    const result = await api(`/api/v1/payments/${state.payment.id}/otp/resend`, { method: "POST" });
    state.verifyOtp = null; state.verifyKey = null; $("otpCode").value = "";
    setLoading(button, false); startCountdown(result.otp_expires_at); startResendCooldown(60); showMessage("OTP mới đã được gửi tới email của bạn.", "success");
  } catch (error) { showMessage(error.message); setLoading(button, false); if (error.code === "OTP_RESEND_COOLDOWN") startResendCooldown(60); }
});

$("newPaymentButton").addEventListener("click", () => {
  state.tuition = null; state.payment = null; state.createKey = null; state.verifyKey = null; state.verifyOtp = null;
  setLoading($("createPaymentButton"), false);
  $("studentCode").value = ""; $("otpCode").value = "";
  $("tuitionCard").classList.add("hidden");
  $("resultStep").classList.add("hidden");
  $("lookupStep").classList.remove("hidden");
  setStep(1);
  clearMessage();
});

$("logoutButton").addEventListener("click", logout);

if (state.token) {
  enterApp();
  loadDashboard().catch(logout);
}

