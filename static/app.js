let cart = JSON.parse(localStorage.getItem("cart")) || [];

function addToCart(name, price) {
    cart.push({name, price});
    localStorage.setItem("cart", JSON.stringify(cart));
    alert(name + " savatchaga qo‘shildi!");
}

function renderCart() {
    const container = document.getElementById("cart");
    if (!container) return;
    container.innerHTML = "";
    let total = 0;
    cart.forEach((item, index) => {
        total += item.price;
        container.innerHTML += `<div>${item.name} - ${item.price} so'm
        <button onclick="removeFromCart(${index})">❌</button></div>`;
    });
    container.innerHTML += `<h3>Jami: ${total} so'm</h3>`;
    localStorage.setItem("cart", JSON.stringify(cart));
}

function removeFromCart(index) {
    cart.splice(index, 1);
    localStorage.setItem("cart", JSON.stringify(cart));
    renderCart();
}

function goCheckout() {
    let total = cart.reduce((sum, item) => sum + item.price, 0);
    localStorage.setItem("total_price", total);
    window.location.href = "/checkout";
}

// checkout sahifasida totalni to‘ldirish
window.onload = function() {
    if (document.getElementById("total_price")) {
        document.getElementById("total_price").value = localStorage.getItem("total_price") || 0;
    }
    renderCart();
}