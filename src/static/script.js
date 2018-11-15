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

function participate(btn_id) {
    console.log("switching buttons " + btn_id)
    var btnParticipate = document.getElementById('btn-participate-' + btn_id);
    var divGift = document.getElementById('div-gift-' + btn_id);

    btnParticipate.style.display = 'none';
    divGift.style.display = 'flex';
}

function gift(div_id) {
    var amount = document.getElementById('gift-amount-' + div_id);
}