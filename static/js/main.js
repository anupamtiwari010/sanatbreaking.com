console.log("Sanat Breaking Loaded");



const menuToggle = document.getElementById("menuToggle");
const navMenu = document.getElementById("navMenu");
const dropdownToggle = document.querySelector(".dropdown-toggle");

// Mobile menu open/close
menuToggle.addEventListener("click", function () {
    navMenu.classList.toggle("active");
    menuToggle.classList.toggle("active");
});

// Mobile dropdown click
dropdownToggle.addEventListener("click", function (e) {
    if (window.innerWidth <= 768) {
        e.preventDefault();
        this.parentElement.classList.toggle("active");
    }
});


