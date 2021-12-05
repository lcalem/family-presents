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

function popDeleteGift(gift_id, gift_name) {
    console.log("hello");
    var alert = document.getElementById('message');
    var alertMessage = document.getElementById('actual-message');
    alertMessage.innerHTML = 'Êtes-vous sûr.e de vouloir supprimer le souhait "' + gift_name + '" ?';

    var deleteLink = document.getElementById('delete-msg-yes');
    deleteLink.href = '/deletegift/' + gift_id;

    alert.style.display = 'block';

}

function hideError() {
    var alert = document.getElementById('message');
    alert.style.display = 'none';
}

function participate(btn_id) {
    var btnParticipate = document.getElementById('btn-participate-' + btn_id);
    var divGift = document.getElementById('div-gift-' + btn_id);

    btnParticipate.style.display = 'none';
    divGift.style.display = 'flex';
}

function checkNumber(evt, gift_remaining_price) {
    var charCode = (evt.which) ? evt.which : event.keyCode
    if (charCode > 31 && (charCode < 48 || charCode > 57))
        return false;
    return true;
}

var span = document.querySelectorAll('.contrib-highlight');
for (var i = span.length; i--;) {
    (function () {
        var t;
        span[i].onmouseover = function () {
            hideAll();
            clearTimeout(t);
            this.className = 'contrib-highlight-on';
        };
        span[i].onmouseout = function () {
            var self = this;
            t = setTimeout(function () {
                self.className = 'contrib-highlight';
            }, 300);
        };
    })();
}

function highlightOn() {
    hideAll();
    clearTimeout(t);
    this.className = 'contrib-highlight-on';
};

function highlightoff() {
    var self = this;
    t = setTimeout(function () {
        self.className = 'contrib-highlight';
    }, 300);
};

function hideAll() {
    for (var i = span.length; i--;) {
        span[i].className = 'contrib-highlight';
    }
};

// function gift(div_id, gift_id, gift_price) {
//     hideError();
//     var amount = document.getElementById('gift-amount-' + div_id.toString()).value;

//     if (isNaN(amount)) {
//         popError("Veuillez entrer un nombre valide !")
//         return false;
//     }
//     if (amount == 0) {
//         popError("Impossible de participer à hauteur de 0€ !")
//         return false;
//     }
//     // if (amount > gift_price) {
//     //     popError("Impossible de participer plus que le prix du cadeau !")
//     //     return false;
//     // }

//     console.log("participating " + amount.toString() + " to gift " + gift_id);
//     const url = "/participate";
//     fetch(url, {
//         method : "POST",
//         headers: {
//             'Accept': 'application/json',
//             'Content-Type': 'application/json'
//         },
//         body : JSON.stringify({
//             participation : amount,
//             gift_id : gift_id.toString()
//         })
//     }).then(
//         error => popError(error.text())
//         // same as function(response) {return response.text();}
//     ).then(
//         html => console.log(html)
//     );

// }