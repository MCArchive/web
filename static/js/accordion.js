var accs = document.getElementsByClassName("accbtn");
for (i = 0; i < accs.length; i++) {
    accs[i].onclick = function() {
        this.classList.toggle("active");
        var div = this.nextElementSibling;
        // div.classList.toggle("hidden");
        if (div.style.maxHeight == 0) {
            console.log("expanding");
            div.style.maxHeight = div.scrollHeight + "px";
        } else {
            div.style.maxHeight = null;
        }
    };
}

