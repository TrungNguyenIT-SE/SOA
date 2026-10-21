const state = {
  token: sessionStorage.getItem("accessToken"),
  user: null,
  account: null,
  tuition: null,
  payment: null,
  countdown: null,
  resendCountdown: null,
  createKey: null,
  verifyKey: null,
  verifyOtp: null,
  admin: {
    users: [],
    students: [],
    transactions: [],
    activeTab: "users"
  }
};

const $ = (id) => document.getElementById(id);
const money = (value) => new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(Number(value));
const uuid = () => crypto.randomUUID();
const maskAccount = (value) => value ? `Tài khoản •••• ${String(value).slice(-4)}` : "Tài khoản —";

function setLoading(button, loading) {
  if (!button) return;
  button.disabled = loading;
  button.classList.toggle("is-loading", loading);
  button.setAttribute("aria-busy", String(loading));
}

function setStep(step) {
  document.querySelectorAll(".stepper li").forEach((item, index) => {
    item.classList.toggle("active", index + 1 === step);
    item.classList.toggle("done", index + 1 < step);
  });
  const badge = $("stepBadge");
  if (badge) badge.textContent = `Bước ${step}/3`;
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    let errText = body.message || body.detail || "Không thể xử lý yêu cầu.";
    if (typeof errText === "object" && errText.message) errText = errText.message;
    if (typeof errText === "string" && errText.startsWith("{")) {
      try {
        const parsed = JSON.parse(errText);
        if (parsed.message) errText = parsed.message;
        else if (parsed.detail) errText = typeof parsed.detail === "string" ? parsed.detail : (parsed.detail.message || errText);
      } catch (e) {}
    }
    const error = new Error(errText);
    error.code = body.code;
    error.status = response.status;
    throw error;
  }
  return body;
}

function showMessage(message, type = "error") {
  const el = $("paymentMessage");
  if (!el) return;
  el.textContent = message;
  el.className = `message ${type}`;
}

function clearMessage() {
  const el = $("paymentMessage");
  if (el) el.className = "message hidden";
}

// -------------------------------------------------------------
// CORE IBANKING DASHBOARD (STUDENT/PAYER VIEW)
// -------------------------------------------------------------
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

  const isAdmin = user.username === "admin";
  const badge = $("adminBadge");
  if (badge) badge.classList.toggle("hidden", !isAdmin);

  if (isAdmin) {
    switchView("admin");
  } else {
    switchView("payer");
  }
}

function renderHistory(items) {
  const root = $("historyList");
  if (!root) return;
  if (!items.length) {
    root.innerHTML = '<div class="empty">Chưa có giao dịch.</div>';
    return;
  }
  root.innerHTML = items
    .map(
      (item) => `
    <article class="history-item ${item.type === "DEBIT" ? "debit" : "credit"}">
      <strong>${item.type === "DEBIT" ? "Thanh toán học phí" : "Hoàn tiền giao dịch"}</strong>
      <span class="amount">${item.type === "DEBIT" ? "-" : "+"}${money(item.amount)}</span>
      <small>${new Date(item.created_at).toLocaleString("vi-VN")} · Mã GD ${item.payment_id.slice(0, 8).toUpperCase()}</small>
    </article>`
    )
    .join("");
}

function enterApp() {
  $("loginView").classList.add("hidden");
  $("logoutButton").classList.remove("hidden");
  $("navGroup").classList.remove("hidden");
  setStep(1);
}

function logout() {
  sessionStorage.removeItem("accessToken");
  sessionStorage.removeItem("refreshToken");
  state.token = null;
  location.reload();
}

// -------------------------------------------------------------
// VIEW SWITCHING (PAYER vs ADMIN)
// -------------------------------------------------------------
function switchView(target) {
  const isPayer = target === "payer";
  $("navPayerTab").classList.toggle("active", isPayer);
  $("navAdminTab").classList.toggle("active", !isPayer);

  if (isPayer) {
    $("appView").classList.remove("hidden");
    $("adminView").classList.add("hidden");
  } else {
    $("appView").classList.add("hidden");
    $("adminView").classList.remove("hidden");
    loadAdminData();
  }
}

$("navPayerTab").addEventListener("click", () => switchView("payer"));
$("navAdminTab").addEventListener("click", () => switchView("admin"));

// -------------------------------------------------------------
// ADMIN DASHBOARD LOGIC (CRUD USER, STUDENT, TRANSACTION)
// -------------------------------------------------------------
window.openModal = function (modalId) {
  const el = $(modalId);
  if (el) el.classList.remove("hidden");
};

window.closeModal = function (modalId) {
  const el = $(modalId);
  if (el) el.classList.add("hidden");
};

// Admin Sub-tabs switching
function switchAdminSubTab(tabName) {
  state.admin.activeTab = tabName;
  $("subTabUsers").classList.toggle("active", tabName === "users");
  $("subTabStudents").classList.toggle("active", tabName === "students");
  $("subTabTxs").classList.toggle("active", tabName === "txs");

  $("sectionUsers").classList.toggle("hidden", tabName !== "users");
  $("sectionStudents").classList.toggle("hidden", tabName !== "students");
  $("sectionTxs").classList.toggle("hidden", tabName !== "txs");
}

$("subTabUsers").addEventListener("click", () => switchAdminSubTab("users"));
$("subTabStudents").addEventListener("click", () => switchAdminSubTab("students"));
$("subTabTxs").addEventListener("click", () => switchAdminSubTab("txs"));
$("btnRefreshAdmin").addEventListener("click", loadAdminData);

async function loadAdminData() {
  await Promise.all([
    loadAdminStats(),
    loadAdminUsers(),
    loadAdminStudents(),
    loadAdminTransactions()
  ]);
}

async function loadAdminStats() {
  try {
    const stats = await api("/api/v1/admin/stats");
    $("statUsers").textContent = stats.total_users || 0;
    $("statStudents").textContent = stats.total_students || 0;
    $("statTransactions").textContent = stats.total_transactions || 0;
    $("statRevenue").textContent = money(stats.total_revenue || 0);
  } catch (err) {
    console.error("Error loading stats:", err);
  }
}

// 1. Users CRUD
async function loadAdminUsers() {
  try {
    const users = await api("/api/v1/users");
    state.admin.users = users || [];
    renderUsersTable(state.admin.users);
  } catch (err) {
    $("userTableBody").innerHTML = `<tr><td colspan="7" class="text-center" style="color:#ef4444">${err.message}</td></tr>`;
  }
}

function renderUsersTable(list) {
  const tbody = $("userTableBody");
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center">Chưa có người dùng nào.</td></tr>';
    return;
  }
  tbody.innerHTML = list
    .map(
      (u) => `
    <tr>
      <td><strong>#${u.id}</strong></td>
      <td><code>${u.username}</code></td>
      <td><strong>${u.full_name}</strong></td>
      <td>${u.email}</td>
      <td>${u.phone || "—"}</td>
      <td style="color:#4ade80;font-weight:600">${money(u.balance || 0)}</td>
      <td class="text-right">
        <div class="action-btns">
          <button class="btn-action edit" onclick="editUser(${u.id})">Sửa</button>
          <button class="btn-action delete" onclick="deleteUser(${u.id})">Xóa</button>
        </div>
      </td>
    </tr>`
    )
    .join("");
}

$("searchUser").addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase().trim();
  const filtered = state.admin.users.filter(
    (u) =>
      u.username.toLowerCase().includes(q) ||
      u.full_name.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q)
  );
  renderUsersTable(filtered);
});

$("btnOpenUserModal").addEventListener("click", () => {
  $("modalUserTitle").textContent = "Thêm Người Dùng Mới";
  $("userIdInput").value = "";
  $("userUsername").value = "";
  $("userUsername").disabled = false;
  $("userPasswordWrap").style.display = "flex";
  $("userPassword").value = "Password123@";
  $("userFullName").value = "";
  $("userPhone").value = "0901234567";
  $("userEmail").value = "";
  $("userBalance").value = "10000000";
  openModal("modalUser");
});

window.editUser = function (userId) {
  const u = state.admin.users.find((x) => x.id === userId);
  if (!u) return;
  $("modalUserTitle").textContent = `Cập Nhật Người Dùng #${u.id}`;
  $("userIdInput").value = u.id;
  $("userUsername").value = u.username;
  $("userUsername").disabled = true;
  $("userPasswordWrap").style.display = "none";
  $("userFullName").value = u.full_name;
  $("userPhone").value = u.phone || "";
  $("userEmail").value = u.email;
  $("userBalance").value = u.balance || 0;
  openModal("modalUser");
};

$("formUser").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = $("userIdInput").value;
  const isUpdate = Boolean(id);
  const payload = {
    full_name: $("userFullName").value.trim(),
    phone: $("userPhone").value.trim(),
    email: $("userEmail").value.trim(),
    balance: Number($("userBalance").value) || 0,
  };

  try {
    if (isUpdate) {
      await api(`/api/v1/users/${id}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      payload.username = $("userUsername").value.trim();
      payload.password = $("userPassword").value;
      await api("/api/v1/users", { method: "POST", body: JSON.stringify(payload) });
    }
    closeModal("modalUser");
    await loadAdminData();
  } catch (err) {
    alert("Lỗi: " + err.message);
  }
});

window.deleteUser = async function (userId) {
  if (!confirm(`Bạn có chắc muốn xóa người dùng ID #${userId} không?`)) return;
  try {
    await api(`/api/v1/users/${userId}`, { method: "DELETE" });
    await loadAdminData();
  } catch (err) {
    alert("Không thể xóa: " + err.message);
  }
};

// 2. Students CRUD
async function loadAdminStudents() {
  try {
    const students = await api("/api/v1/students");
    state.admin.students = students || [];
    renderStudentsTable(state.admin.students);
  } catch (err) {
    $("studentTableBody").innerHTML = `<tr><td colspan="6" class="text-center" style="color:#ef4444">${err.message}</td></tr>`;
  }
}

function renderStudentsTable(list) {
  const tbody = $("studentTableBody");
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center">Chưa có sinh viên nào.</td></tr>';
    return;
  }
  tbody.innerHTML = list
    .map(
      (s) => `
    <tr>
      <td><code>${s.student_code}</code></td>
      <td><strong>${s.student_name}</strong></td>
      <td>${s.term || "HK1/2026-2027"}</td>
      <td style="color:#38bdf8;font-weight:600">${money(s.amount || 0)}</td>
      <td><span class="badge ${s.status === "PAID" ? "success" : "warning"}">${s.status === "PAID" ? "Đã nộp" : "Chưa nộp"}</span></td>
      <td class="text-right">
        <div class="action-btns">
          <button class="btn-action edit" onclick="editStudent('${s.student_code}')">Sửa</button>
          <button class="btn-action delete" onclick="deleteStudent('${s.student_code}')">Xóa</button>
        </div>
      </td>
    </tr>`
    )
    .join("");
}

$("searchStudent").addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase().trim();
  const filtered = state.admin.students.filter(
    (s) =>
      s.student_code.toLowerCase().includes(q) ||
      s.student_name.toLowerCase().includes(q)
  );
  renderStudentsTable(filtered);
});

function checkDuplicateTerm() {
  if ($("studentCodeInput").disabled) return false;
  const code = $("studentCodeInput").value.trim().toUpperCase();
  const term = $("studentTermInput").value.trim();
  const hint = $("studentCodeHint");
  if (!code) {
    if (hint) { hint.style.display = "none"; hint.innerHTML = ""; }
    return false;
  }
  const existing = state.admin.students.find((s) => s.student_code.toUpperCase() === code);
  if (!existing) {
    if (hint) { hint.style.display = "none"; hint.innerHTML = ""; }
    return false;
  }
  const isDuplicateTerm = state.admin.students.some(
    (s) => s.student_code.toUpperCase() === code && s.term === term
  );
  if (isDuplicateTerm) {
    if (hint) {
      hint.style.display = "block";
      hint.style.color = "#f87171";
      hint.innerHTML = `⚠️ Sinh viên <strong>${existing.student_name} (${code})</strong> đã có học phí cho học kỳ <strong>${term}</strong> rồi! Vui lòng chọn học kỳ khác hoặc vào mục "Sửa".`;
    }
    return true;
  } else {
    if (hint) {
      hint.style.display = "block";
      hint.style.color = "#38bdf8";
      hint.innerHTML = `ℹ️ Đã tìm thấy sinh viên <strong>${existing.student_name}</strong>. Họ tên đã tự động điền, bạn chỉ cần nhập học kỳ và học phí mới.`;
    }
    return false;
  }
}

$("studentCodeInput").addEventListener("input", (e) => {
  if ($("studentCodeInput").disabled) return;
  const code = e.target.value.trim().toUpperCase();
  const existing = state.admin.students.find((s) => s.student_code.toUpperCase() === code);
  if (existing) {
    $("studentNameInput").value = existing.student_name;
    $("studentNameInput").readOnly = true;
    $("studentNameInput").style.backgroundColor = "rgba(255, 255, 255, 0.08)";
    $("studentNameInput").style.cursor = "not-allowed";
  } else {
    $("studentNameInput").readOnly = false;
    $("studentNameInput").style.backgroundColor = "";
    $("studentNameInput").style.cursor = "text";
  }
  checkDuplicateTerm();
});

$("studentTermInput").addEventListener("input", () => {
  checkDuplicateTerm();
});

$("btnOpenStudentModal").addEventListener("click", () => {
  $("modalStudentTitle").textContent = "Thêm Sinh Viên & Học Phí Mới";
  $("studentCodeInput").value = "";
  $("studentCodeInput").disabled = false;
  $("studentNameInput").value = "";
  $("studentNameInput").readOnly = false;
  $("studentNameInput").style.backgroundColor = "";
  $("studentNameInput").style.cursor = "text";
  $("studentTermInput").value = "HK1/2026-2027";
  $("studentAmountInput").value = "1200000";
  if ($("studentStatusInput")) $("studentStatusInput").value = "UNPAID";
  const hint = $("studentCodeHint");
  if (hint) { hint.style.display = "none"; hint.innerHTML = ""; }
  updateStudentPayerUI();
  openModal("modalStudent");
});


function updateStudentPayerUI() {
  const statusInput = $("studentStatusInput");
  const payerGroup = $("studentPayerGroup");
  const payerSelect = $("studentPayerInput");
  if (!statusInput || !payerGroup || !payerSelect) return;

  if (statusInput.value === "PAID") {
    payerGroup.classList.remove("hidden");
    const currentVal = payerSelect.value;
    payerSelect.innerHTML = (state.admin.users || []).map(u => {
      const bal = u.balance !== null && u.balance !== undefined ? formatVND(u.balance) : "0 đ";
      return `<option value="${u.id}">${u.full_name} (${u.username}) - Số dư: ${bal}</option>`;
    }).join("");
    if (currentVal && payerSelect.querySelector(`option[value="${currentVal}"]`)) {
      payerSelect.value = currentVal;
    }
    updatePayerBalanceHint();
  } else {
    payerGroup.classList.add("hidden");
  }
}

function updatePayerBalanceHint() {
  const payerSelect = $("studentPayerInput");
  const hint = $("studentPayerBalanceHint");
  const amount = Number($("studentAmountInput").value) || 0;
  if (!payerSelect || !hint) return;

  const selectedUserId = parseInt(payerSelect.value, 10);
  const user = (state.admin.users || []).find(u => u.id === selectedUserId);
  if (!user) {
    hint.innerHTML = "";
    return;
  }

  const balance = user.balance || 0;
  if (balance >= amount) {
    hint.style.color = "#10b981";
    hint.innerHTML = `✓ Số dư đủ thanh toán: <strong>${formatVND(balance)}</strong> (Còn dư: ${formatVND(balance - amount)})`;
  } else {
    hint.style.color = "#ef4444";
    hint.innerHTML = `⚠️ Không đủ số dư! Hiện có: <strong>${formatVND(balance)}</strong> (Còn thiếu: <strong>${formatVND(amount - balance)}</strong>)`;
  }
}

if ($("studentStatusInput")) {
  $("studentStatusInput").addEventListener("change", updateStudentPayerUI);
}
if ($("studentPayerInput")) {
  $("studentPayerInput").addEventListener("change", updatePayerBalanceHint);
}
if ($("studentAmountInput")) {
  $("studentAmountInput").addEventListener("input", updatePayerBalanceHint);
}

window.editStudent = function (studentCode) {
  const s = state.admin.students.find((x) => x.student_code === studentCode);
  if (!s) return;
  $("modalStudentTitle").textContent = `Cập Nhật Sinh Viên: ${s.student_code}`;
  $("studentCodeInput").value = s.student_code;
  $("studentCodeInput").disabled = true;
  $("studentNameInput").value = s.student_name;
  $("studentNameInput").readOnly = false;
  $("studentNameInput").style.backgroundColor = "";
  $("studentNameInput").style.cursor = "text";
  $("studentTermInput").value = s.term || "HK1/2026-2027";
  $("studentAmountInput").value = s.amount || 1000000;
  if ($("studentStatusInput")) $("studentStatusInput").value = (s.status === "PAID" ? "PAID" : "UNPAID");
  const hint = $("studentCodeHint");
  if (hint) { hint.style.display = "none"; hint.innerHTML = ""; }
  updateStudentPayerUI();
  openModal("modalStudent");
};

$("formStudent").addEventListener("submit", async (e) => {
  e.preventDefault();
  const code = $("studentCodeInput").value.trim().toUpperCase();
  const isUpdate = $("studentCodeInput").disabled;
  const term = $("studentTermInput").value.trim();
  const selectedStatus = $("studentStatusInput") ? $("studentStatusInput").value : "UNPAID";

  if (!isUpdate && checkDuplicateTerm()) {
    alert(`Thông báo: Mã sinh viên ${code} đã có hồ sơ học phí cho học kỳ "${term}". Không được tạo trùng mã sinh viên cho cùng một học kỳ!`);
    return;
  }

  let payerUserId = null;
  const amount = Number($("studentAmountInput").value) || 0;
  if (selectedStatus === "PAID") {
    const payerSelect = $("studentPayerInput");
    payerUserId = payerSelect ? parseInt(payerSelect.value, 10) : null;
    const user = (state.admin.users || []).find(u => u.id === payerUserId);
    if (user && (user.balance || 0) < amount) {
      alert(`Thông báo: Người dùng "${user.full_name}" không đủ số dư để nộp học phí!\n` +
            `- Học phí cần nộp: ${formatVND(amount)}\n` +
            `- Số dư hiện tại: ${formatVND(user.balance || 0)}\n` +
            `- Còn thiếu: ${formatVND(amount - (user.balance || 0))}\n\n` +
            `Vui lòng nạp thêm tiền cho người dùng hoặc chọn tài khoản khác.`);
      return;
    }
  }

  const payload = {
    full_name: $("studentNameInput").value.trim(),
    term: term,
    amount: amount,
    status: selectedStatus,
    payer_user_id: payerUserId,
  };

  try {
    if (isUpdate) {
      await api(`/api/v1/students/${code}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      const createPayload = {
        student_code: code,
        student_name: $("studentNameInput").value.trim(),
        term: term,
        amount: Number($("studentAmountInput").value) || 0,
        status: selectedStatus,
      };
      await api("/api/v1/students", { method: "POST", body: JSON.stringify(createPayload) });
    }
    closeModal("modalStudent");
    await loadAdminData();
  } catch (err) {
    alert("Thông báo: " + err.message);
  }
});

window.deleteStudent = async function (code) {
  if (!confirm(`Bạn có chắc muốn xóa sinh viên ${code} và toàn bộ hóa đơn liên quan?`)) return;
  try {
    await api(`/api/v1/students/${code}`, { method: "DELETE" });
    await loadAdminData();
  } catch (err) {
    alert("Không thể xóa: " + err.message);
  }
};

// 3. Transactions CRUD
async function loadAdminTransactions() {
  try {
    const txs = await api("/api/v1/transactions");
    state.admin.transactions = txs || [];
    renderTxsTable(state.admin.transactions);
  } catch (err) {
    $("txTableBody").innerHTML = `<tr><td colspan="8" class="text-center" style="color:#ef4444">${err.message}</td></tr>`;
  }
}

function renderTxsTable(list) {
  const tbody = $("txTableBody");
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center">Chưa có giao dịch nào.</td></tr>';
    return;
  }
  tbody.innerHTML = list
    .map((t) => {
      let badgeClass = "warning";
      if (t.status === "SUCCEEDED") badgeClass = "success";
      else if (["CANCELLED", "FAILED_TUITION_UNAVAILABLE", "FAILED_INSUFFICIENT_FUNDS"].includes(t.status)) badgeClass = "danger";
      else if (t.status === "COMPENSATED") badgeClass = "info";

      return `
    <tr>
      <td><code title="${t.id}">${t.id.slice(0, 8).toUpperCase()}...</code></td>
      <td><strong>${t.payer_name}</strong><br><small style="color:#94a3b8">${t.payer_email}</small></td>
      <td><code>${t.student_code}</code><br><small>${t.student_name}</small></td>
      <td>${t.term || "HK1/2026-2027"}</td>
      <td style="color:#facc15;font-weight:700">${money(t.amount || 0)}</td>
      <td><span class="badge ${badgeClass}">${t.status}</span></td>
      <td style="font-size:0.8rem;color:#94a3b8">${new Date(t.created_at).toLocaleString("vi-VN")}</td>
      <td class="text-right">
        <div class="action-btns">
          <button class="btn-action edit" onclick="editTx('${t.id}')">Sửa</button>
          <button class="btn-action delete" onclick="deleteTx('${t.id}')">Xóa</button>
        </div>
      </td>
    </tr>`;
    })
    .join("");
}

$("searchTx").addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase().trim();
  const filtered = state.admin.transactions.filter(
    (t) =>
      t.id.toLowerCase().includes(q) ||
      t.payer_name.toLowerCase().includes(q) ||
      t.student_code.toLowerCase().includes(q) ||
      t.student_name.toLowerCase().includes(q)
  );
  renderTxsTable(filtered);
});

$("btnOpenTxModal").addEventListener("click", () => {
  $("modalTxTitle").textContent = "Tạo Giao Dịch Thanh Toán Mới";
  $("txIdInput").value = "";
  $("txPayerName").value = "Hoàng Thái Đăng Khoa";
  $("txPayerEmail").value = "dangkhoa040706@gmail.com";
  $("txStudentCode").value = "52400001";
  $("txStudentName").value = "Nguyễn Minh Anh";
  $("txTerm").value = "HK1/2026-2027";
  $("txAmount").value = "1200000";
  $("txStatus").value = "SUCCEEDED";
  openModal("modalTx");
});

window.editTx = function (txId) {
  const t = state.admin.transactions.find((x) => x.id === txId);
  if (!t) return;
  $("modalTxTitle").textContent = `Cập Nhật Giao Dịch ${t.id.slice(0, 8).toUpperCase()}`;
  $("txIdInput").value = t.id;
  $("txPayerName").value = t.payer_name;
  $("txPayerEmail").value = t.payer_email;
  $("txStudentCode").value = t.student_code;
  $("txStudentName").value = t.student_name;
  $("txTerm").value = t.term || "HK1/2026-2027";
  $("txAmount").value = t.amount;
  $("txStatus").value = t.status;
  openModal("modalTx");
};

$("formTx").addEventListener("submit", async (e) => {
  e.preventDefault();
  const txId = $("txIdInput").value;
  const isUpdate = Boolean(txId);
  const payload = {
    payer_name: $("txPayerName").value.trim(),
    payer_email: $("txPayerEmail").value.trim(),
    student_code: $("txStudentCode").value.trim().toUpperCase(),
    student_name: $("txStudentName").value.trim(),
    term: $("txTerm").value.trim(),
    amount: Number($("txAmount").value) || 0,
    status: $("txStatus").value,
  };

  try {
    if (isUpdate) {
      await api(`/api/v1/transactions/${txId}`, {
        method: "PUT",
        body: JSON.stringify({
          status: payload.status,
          amount: payload.amount,
          student_name: payload.student_name,
          term: payload.term,
        }),
      });
    } else {
      await api("/api/v1/transactions", { method: "POST", body: JSON.stringify(payload) });
    }
    closeModal("modalTx");
    await loadAdminData();
  } catch (err) {
    alert("Lỗi: " + err.message);
  }
});

window.deleteTx = async function (txId) {
  if (!confirm(`Bạn có chắc muốn xóa vĩnh viễn giao dịch ${txId.slice(0, 8).toUpperCase()}?`)) return;
  try {
    await api(`/api/v1/transactions/${txId}`, { method: "DELETE" });
    await loadAdminData();
  } catch (err) {
    alert("Không thể xóa: " + err.message);
  }
};

// -------------------------------------------------------------
// EVENT LISTENERS & AUTH LOGIN
// -------------------------------------------------------------
$("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorEl = $("loginError");
  const submitButton = event.currentTarget.querySelector('button[type="submit"]');
  errorEl.classList.add("hidden");
  setLoading(submitButton, true);
  try {
    const result = await api("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: $("username").value, password: $("password").value }),
    });
    state.token = result.access;
    sessionStorage.setItem("accessToken", result.access);
    sessionStorage.setItem("refreshToken", result.refresh);
    enterApp();
    await loadDashboard();
  } catch (error) {
    errorEl.textContent = error.message;
    errorEl.classList.remove("hidden");
  } finally {
    setLoading(submitButton, false);
  }
});

$("lookupForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage();
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
    if (Number(state.account.available_balance) < Number(state.tuition.amount)) {
      showMessage("Số dư khả dụng không đủ để thanh toán toàn bộ học phí.");
    }
  } catch (error) {
    $("tuitionCard").classList.add("hidden");
    showMessage(error.message);
  } finally {
    setLoading(submitButton, false);
  }
});

$("acceptTerms").addEventListener("change", (event) => {
  $("createPaymentButton").disabled = !event.target.checked || Number(state.account.available_balance) < Number(state.tuition.amount);
});


function maskEmail(email) {
  if (!email || !email.includes("@")) return email || "";
  const [local, domain] = email.split("@");
  if (local.length <= 2) return `${local[0]}*@${domain}`;
  return `${local.slice(0, 2)}***${local.slice(-1)}@${domain}`;
}

$("createPaymentButton").addEventListener("click", async () => {
  clearMessage();
  setLoading($("createPaymentButton"), true);
  try {
    const userEmail = (state.user && state.user.email) ? state.user.email : (state.account && state.account.email ? state.account.email : "user@example.com");
    const otpRes = await api("/api/v1/otp/generate", {
      method: "POST",
      body: JSON.stringify({
        email: userEmail,
        student_code: state.tuition.student_code,
        amount: state.tuition.amount,
      }),
    });
    state.payment = {
      email: userEmail,
      masked_email: maskEmail(userEmail),
      otp_expires_at: otpRes.expires_at || new Date(Date.now() + 300000).toISOString(),
      student_code: state.tuition.student_code,
      amount: state.tuition.amount,
    };
    setLoading($("createPaymentButton"), false);
    $("lookupStep").classList.add("hidden");
    $("otpStep").classList.remove("hidden");
    setStep(2);
    $("maskedEmail").textContent = state.payment.masked_email;
    startCountdown(state.payment.otp_expires_at);
    startResendCooldown(60);
    showMessage(`Mã OTP đã được gửi đến email ${userEmail}. (Demo OTP: ${otpRes.otp_code})`, "success");
  } catch (error) {
    showMessage(error.message);
    setLoading($("createPaymentButton"), false);
  }
});

function startCountdown(expiresAt) {
  clearInterval(state.countdown);
  const tick = () => {
    const seconds = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
    $("otpCountdown").textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
    if (!seconds) clearInterval(state.countdown);
  };
  tick();
  state.countdown = setInterval(tick, 1000);
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
  tick();
  state.resendCountdown = setInterval(tick, 1000);
}

async function showSuccess(result) {
  clearInterval(state.countdown);
  clearInterval(state.resendCountdown);
  $("otpStep").classList.add("hidden");
  $("resultStep").classList.remove("hidden");
  setStep(3);
  $("resultTitle").textContent = "Giao dịch thành công";
  $("resultMessage").textContent = "Khoản học phí đã được thanh toán và email xác nhận đang được gửi.";
  await loadDashboard();
  $("resultDetails").innerHTML = `
    <dt>Mã giao dịch</dt><dd>${result.id.slice(0, 8)}</dd>
    <dt>MSSV</dt><dd>${result.student_code}</dd>
    <dt>Sinh viên</dt><dd>${result.student_name}</dd>
    <dt>Số tiền</dt><dd>${money(result.amount)}</dd>
    <dt>Số dư mới</dt><dd>${money(state.account.available_balance)}</dd>
    <dt>Thời gian</dt><dd>${new Date(result.completed_at).toLocaleString("vi-VN")}</dd>
    <dt>Trạng thái</dt><dd>${result.status}</dd>
  `;
}

async function pollPayment() {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const result = await api(`/api/v1/payments/${state.payment.id}`);
    if (result.status === "SUCCEEDED") return showSuccess(result);
    if (!["PROCESSING", "OTP_PENDING"].includes(result.status)) {
      throw new Error(`Giao dịch kết thúc với trạng thái ${result.status}.`);
    }
  }
  throw new Error("Giao dịch vẫn đang xử lý. Bạn có thể kiểm tra lại trong lịch sử.");
}

$("otpForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage();
  const button = $("verifyOtpButton");
  setLoading(button, true);
  try {
    const otp = $("otpCode").value.trim();
    // 1. Xác thực OTP qua Dịch vụ Java của Nguyên
    await api("/api/v1/otp/verify", {
      method: "POST",
      body: JSON.stringify({
        otp: otp,
        email: state.payment ? state.payment.email : "",
      }),
    });

    // 2. Chuyển học phí sang ĐÃ NỘP (Nguyên) -> Tự động kiểm tra số dư, trừ tiền (Account) và ghi lịch sử (Phong C#)
    await api(`/api/v1/students/${encodeURIComponent(state.tuition.student_code)}`, {
      method: "PUT",
      body: JSON.stringify({
        status: "PAID",
        payer_user_id: state.user ? state.user.id : 1,
      }),
    });

    await showSuccess({
      id: uuid(),
      student_code: state.tuition.student_code,
      student_name: state.tuition.student_name,
      amount: state.tuition.amount,
      status: "SUCCEEDED",
      completed_at: new Date().toISOString(),
    });
  } catch (error) {
    showMessage(error.message);
  } finally {
    setLoading(button, false);
  }
});

$("resendOtpButton").addEventListener("click", async () => {
  const button = $("resendOtpButton");
  setLoading(button, true);
  clearMessage();
  try {
    const userEmail = state.payment ? state.payment.email : ((state.user && state.user.email) ? state.user.email : "user@example.com");
    const otpRes = await api("/api/v1/otp/generate", {
      method: "POST",
      body: JSON.stringify({
        email: userEmail,
        student_code: state.tuition.student_code,
        amount: state.tuition.amount,
      }),
    });
    $("otpCode").value = "";
    setLoading(button, false);
    state.payment.otp_expires_at = otpRes.expires_at || new Date(Date.now() + 300000).toISOString();
    startCountdown(state.payment.otp_expires_at);
    startResendCooldown(60);
    showMessage(`Mã OTP mới đã được gửi tới email của bạn. (Demo OTP: ${otpRes.otp_code})`, "success");
  } catch (error) {
    showMessage(error.message);
    setLoading(button, false);
    if (error.code === "OTP_RESEND_COOLDOWN") startResendCooldown(60);
  }
});

$("newPaymentButton").addEventListener("click", () => {
  state.tuition = null;
  state.payment = null;
  state.createKey = null;
  state.verifyKey = null;
  state.verifyOtp = null;
  setLoading($("createPaymentButton"), false);
  $("studentCode").value = "";
  $("otpCode").value = "";
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
