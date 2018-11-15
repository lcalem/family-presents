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
