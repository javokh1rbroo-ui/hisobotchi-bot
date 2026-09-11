const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const initData = tg ? tg.initData : "";

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Init-Data": initData,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

const fmt = (n) => Math.round(n).toLocaleString("ru-RU") + " so'm";

let currentType = "chiqim";
let categories = { kirim: [], chiqim: [] };
let selectedCategory = null;

// ---------- Tabs ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "report") loadReport();
    if (btn.dataset.tab === "history") loadHistory();
  });
});

// ---------- Balance ----------
async function loadBalance() {
  try {
    const b = await api("/api/balance");
    document.getElementById("balanceValue").textContent = fmt(b.balans);
    document.getElementById("kirimValue").textContent = fmt(b.kirim);
    document.getElementById("chiqimValue").textContent = fmt(b.chiqim);
  } catch (e) { console.error(e); }
}

// ---------- Add transaction ----------
function renderCategories() {
  const grid = document.getElementById("categoryGrid");
  grid.innerHTML = "";
  selectedCategory = null;
  categories[currentType].forEach((cat) => {
    const chip = document.createElement("div");
    chip.className = "category-chip";
    chip.textContent = cat;
    chip.addEventListener("click", () => {
      document.querySelectorAll(".category-chip").forEach((c) => c.classList.remove("selected"));
      chip.classList.add("selected");
      selectedCategory = cat;
    });
    grid.appendChild(chip);
  });
}

document.getElementById("typeIncome").addEventListener("click", () => {
  currentType = "kirim";
  document.getElementById("typeIncome").classList.add("active");
  document.getElementById("typeExpense").classList.remove("active");
  renderCategories();
});
document.getElementById("typeExpense").addEventListener("click", () => {
  currentType = "chiqim";
  document.getElementById("typeExpense").classList.add("active");
  document.getElementById("typeIncome").classList.remove("active");
  renderCategories();
});

document.getElementById("saveBtn").addEventListener("click", async () => {
  const amount = parseFloat(document.getElementById("amountInput").value);
  const comment = document.getElementById("commentInput").value.trim();
  if (!amount || amount <= 0) { tg?.showAlert("Summani kiriting"); return; }
  if (!selectedCategory) { tg?.showAlert("Kategoriyani tanlang"); return; }

  const btn = document.getElementById("saveBtn");
  btn.disabled = true;
  try {
    await api("/api/transaction", {
      method: "POST",
      body: JSON.stringify({ type: currentType, amount, category: selectedCategory, comment }),
    });
    document.getElementById("amountInput").value = "";
    document.getElementById("commentInput").value = "";
    document.querySelectorAll(".category-chip").forEach((c) => c.classList.remove("selected"));
    selectedCategory = null;
    tg?.HapticFeedback?.notificationOccurred("success");
    loadBalance();
  } catch (e) {
    tg?.showAlert("Xatolik yuz berdi");
  } finally {
    btn.disabled = false;
  }
});

// ---------- Report ----------
function populateMonths() {
  const select = document.getElementById("monthSelect");
  const now = new Date();
  select.innerHTML = "";
  for (let i = 0; i < 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${d.getFullYear()}-${d.getMonth() + 1}`;
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    select.appendChild(opt);
  }
  select.addEventListener("change", loadReport);
}

async function loadReport() {
  const [year, month] = document.getElementById("monthSelect").value.split("-").map(Number);
  const content = document.getElementById("reportContent");
  content.innerHTML = "Yuklanmoqda...";
  try {
    const rows = await api(`/api/report?year=${year}&month=${month}`);
    if (rows.length === 0) {
      content.innerHTML = '<div class="empty-state">Bu oy uchun ma\'lumot yo\'q</div>';
      return;
    }
    let totalKirim = 0, totalChiqim = 0;
    let html = "";
    const kirimRows = rows.filter((r) => r.type === "kirim");
    const chiqimRows = rows.filter((r) => r.type === "chiqim");
    if (kirimRows.length) {
      html += '<div class="report-group-title">Kirimlar</div>';
      kirimRows.forEach((r) => {
        totalKirim += r.total;
        html += `<div class="report-row kirim"><span>${r.category} (${r.count})</span><span class="amt">${fmt(r.total)}</span></div>`;
      });
    }
    if (chiqimRows.length) {
      html += '<div class="report-group-title">Chiqimlar</div>';
      chiqimRows.forEach((r) => {
        totalChiqim += r.total;
        html += `<div class="report-row chiqim"><span>${r.category} (${r.count})</span><span class="amt">${fmt(r.total)}</span></div>`;
      });
    }
    html += `<div class="report-total"><span>Sof natija</span><span>${fmt(totalKirim - totalChiqim)}</span></div>`;
    content.innerHTML = html;
  } catch (e) {
    content.innerHTML = '<div class="empty-state">Xatolik yuz berdi</div>';
  }
}

// ---------- History ----------
async function loadHistory() {
  const content = document.getElementById("historyContent");
  content.innerHTML = "Yuklanmoqda...";
  try {
    const rows = await api("/api/recent");
    if (rows.length === 0) {
      content.innerHTML = '<div class="empty-state">Hali yozuvlar yo\'q</div>';
      return;
    }
    content.innerHTML = rows.map((r) => {
      const date = new Date(r.created_at).toLocaleDateString("uz-UZ", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
      return `<div class="history-row ${r.type}">
        <div>
          <div>${r.category}${r.comment ? " — " + r.comment : ""}</div>
          <div class="meta">${date}</div>
        </div>
        <span class="amt">${r.type === "kirim" ? "+" : "-"}${fmt(r.amount)}</span>
      </div>`;
    }).join("");
  } catch (e) {
    content.innerHTML = '<div class="empty-state">Xatolik yuz berdi</div>';
  }
}

// ---------- Init ----------
(async function init() {
  try {
    categories = await api("/api/categories");
  } catch (e) {
    categories = { kirim: [], chiqim: [] };
  }
  renderCategories();
  populateMonths();
  loadBalance();
})();
