"use strict";


function submitGift(form) {

    var xhr = new XMLHttpRequest();
    xhr.onload = function(){ alert (xhr.responseText); }
    xhr.onerror = function(){ alert (xhr.responseText); }
    xhr.open(form.method, form.action, true);
    // xhr.setRequestHeader("Content-Type", "application/json");
    var data = new FormData(form)

    console.log(data)
    xhr.send(data);
    return false;
}

function popError(message) {
    var alert = document.getElementById('message');
    var alertMessage = document.getElementById('actual-message');
    alertMessage.innerHTML = message;
    alert.style.display = 'block';
}

function hideError(message) {
    var alert = document.getElementById('message');
    alert.style.display = 'none';
}

function participate(btn_id) {
    var btnParticipate = document.getElementById('btn-participate-' + btn_id);
    var divGift = document.getElementById('div-gift-' + btn_id);

    btnParticipate.style.display = 'none';
    divGift.style.display = 'flex';
}

function gift(div_id, gift_id, gift_price) {
    var amount = document.getElementById('gift-amount-' + div_id.toString()).value;

    if (amount > gift_price) {
        popError("Impossible de participer plus que le prix du cadeau !")
    }
    console.log("participating " + amount.toString() + " to gift " + gift_id);
}