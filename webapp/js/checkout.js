document.getElementById("checkout-form").onsubmit = async (e) => {
  e.preventDefault();

  let formData = new FormData();
  formData.append("user_id", document.getElementById("user_id").value);
  formData.append("items", localStorage.getItem("cart") || "[]");
  formData.append("receipt", document.getElementById("receipt").files[0]);

  let res = await fetch("/api/checkout", {
    method: "POST",
    body: formData
  });

  let data = await res.json();
  alert(data.msg);
};


let tg = window.Telegram.WebApp;
let tg_id = tg.initDataUnsafe?.user?.id;

if (tg_id) {
  fetch(`/api/user/${tg_id}`)
    .then(r => r.json())
    .then(user => {
      if (user.error) {
        alert("Foydalanuvchi topilmadi! /start orqali ro‘yxatdan o‘ting.");
        return;
      }

      document.getElementById("user-info").innerHTML = `
        <li class="list-group-item"><b>Ism:</b> ${user.name}</li>
        <li class="list-group-item"><b>Telefon:</b> ${user.phone}</li>
        <li class="list-group-item"><b>Manzil:</b> ${user.address}</li>
      `;
      document.getElementById("user_id").value = user.id;
    });
}