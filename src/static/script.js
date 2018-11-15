"use strict";


function submitForm(form) {
    var xhr = new XMLHttpRequest();
    xhr.onload = function(){ alert (xhr.responseText); }
    xhr.onerror = function(){ alert (xhr.responseText); }
    xhr.open(form.method, form.action, true);
    // xhr.setRequestHeader("Content-Type", "application/json");
    var data = new FormData(form)

    // append date
    var current_day = window.location.href.split("/day/")[1];  // that's questionable
    data.append("date", current_day)

    console.log(data)
    xhr.send(data);
    return false;
}


function selectQuantity(elt_id) {
    var nb = parseInt(elt_id.slice(-1));
    var name = elt_id.slice(0, -1);

    for (var i = 0; i < nb; i++) {
        document.getElementById(name + String(i)).checked = true;
    }
}