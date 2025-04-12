document.addEventListener("DOMContentLoaded", function () {
    const openBtn = document.getElementById("open-btn");
    const closeBtn = document.getElementById("close-btn");
    const sidebar = document.querySelector(".sidebar");
    const mainContent = document.querySelector(".main-content");

    // Open de sidebar
    openBtn.addEventListener("click", function () {
        sidebar.style.width = "250px"; // Breedte van de sidebar
        mainContent.style.marginLeft = "250px"; // Schuif de inhoud naar rechts
    });

    // Sluit de sidebar
    closeBtn.addEventListener("click", function () {
        sidebar.style.width = "0";
        mainContent.style.marginLeft = "0";
    });
});