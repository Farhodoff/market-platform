// 📦 Admin panel funksiyalari

// Buyurtmalarni qayta yuklash
async function loadOrders() {
    const res = await fetch("/orders");
    const html = await res.text();
    document.open();
    document.write(html);
    document.close();
}

// Buyurtma statusini o'zgartirish
async function updateStatus(orderId, newStatus) {
    const res = await fetch(`/api/orders/${orderId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
    });

    const data = await res.json();
    if (data.status === "ok") {
        alert("✅ Status yangilandi!");
        loadOrders(); // qaytadan yuklash
    } else {
        alert("❌ Xatolik: " + data.msg);
    }
}

// 30 soniyada bir yangilash
setInterval(loadOrders, 30000);