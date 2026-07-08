(function() {
    function ensureToastContainer() {
        let globalToast = document.getElementById("global-toast");
        if (!globalToast) {
            globalToast = document.createElement("div");
            globalToast.id = "global-toast";
            globalToast.className = "hidden";
            document.body.appendChild(globalToast);
        }
    }

    window.showToast = function(message, type) {
        ensureToastContainer();
        const globalToast = document.getElementById("global-toast");
        globalToast.textContent = message;
        
        // Class settings based on severity type
        if (type === "error") {
            globalToast.className = "fixed bottom-6 right-6 z-50 p-4 border-4 border-error bg-surface-container-high/90 text-error font-mono text-sm";
        } else if (type === "success") {
            globalToast.className = "fixed bottom-6 right-6 z-50 p-4 border-4 border-secondary bg-surface-container-high/90 text-secondary font-mono text-sm";
        } else {
            globalToast.className = "fixed bottom-6 right-6 z-50 p-4 border-4 border-primary bg-surface-container-high/90 text-primary font-mono text-sm";
        }
        
        globalToast.classList.remove("hidden");
        
        // Automatically close after 4 seconds
        if (window.toastTimeout) clearTimeout(window.toastTimeout);
        window.toastTimeout = setTimeout(() => {
            globalToast.classList.add("hidden");
        }, 4000);
    };
})();
