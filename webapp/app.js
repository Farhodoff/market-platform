// Fake user info (aslida DB'dan olish kerak)
let user = JSON.parse(localStorage.getItem("user") ||
  '{"id":1,"name":"Farhod Soyilov","phone":"+998901234567","address":"Toshkent"}');

// Checkout sahifasi
if (document.getElementById("checkout-form")) {
  // Foydalanuvchi ma'lumotlari
  let $info = document.getElementById("user-info");
  $info.innerHTML = `
    <li class="list-group-item"><strong>Ism:</strong> ${user.name}</li>
    <li class="list-group-item"><strong>Telefon:</strong> ${user.phone}</li>
    <li class="list-group-item"><strong>Manzil:</strong> ${user.address}</li>
  `;
  document.getElementById("user_id").value = user.id;

  // Buyurtma ro'yxati
  let $sum = document.getElementById("order-summary");
  let items = [];
  let total = 0;
  for (let id in cart) {
    let prod = JSON.parse(localStorage.getItem("prod_" + id));
    if (!prod) continue;
    items.push({product_id: id, qty: cart[id]});
    total += prod.price * cart[id];
    $sum.innerHTML += `<li class="list-group-item d-flex justify-content-between">
        <span>${prod.name} x${cart[id]}</span>
        <strong>${(prod.price*cart[id]).toLocaleString("uz-UZ")} so'm</strong>
    </li>`;
  }
  $sum.innerHTML += `<li class="list-group-item fw-bold d-flex justify-content-between">
      <span>Jami:</span><span>${total.toLocaleString("uz-UZ")} so'm</span>
  </li>`;
  document.getElementById("items").value = JSON.stringify(items);

  // Form yuborish
  document.getElementById("checkout-form").onsubmit = async (e) => {
    e.preventDefault();
    let formData = new FormData(e.target);

    let res = await fetch("/api/checkout", {
      method: "POST",
      body: formData
    });
    let data = await res.json();
    alert(data.msg);

    // Cartni tozalash
    cart = {};
    saveCart();
    window.location.href = "index.html";
  };
}