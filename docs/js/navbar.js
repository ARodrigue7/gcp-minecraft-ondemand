(function() {
    function initNavbar() {
        const container = document.getElementById("global-navbar");
        if (!container) return;

        const activeTab = container.getAttribute("data-active-tab");

        container.innerHTML = `
        <header class="bg-surface/90 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
            <nav class="flex justify-between items-center w-full px-base md:px-margin max-w-container-max mx-auto h-14">
                <div class="flex items-center gap-3 cursor-pointer" onclick="window.location.href='index.html'">
                    <span class="font-headline-lg text-[20px] font-bold text-primary uppercase tracking-[0.1em]">GCP Minecraft</span>
                </div>
                <div class="hidden md:flex gap-8 items-center h-full">
                    <a class="${activeTab === 'landing' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface/60 hover:text-on-surface'} px-1 py-1 transition-all duration-200 text-label-lg h-full flex items-center" href="index.html">LANDING</a>
                    <a class="${activeTab === 'servers' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface/60 hover:text-on-surface'} px-1 py-1 transition-all duration-200 text-label-lg h-full flex items-center" href="play.html">SERVERS</a>
                    <a class="${activeTab === 'admin' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface/60 hover:text-on-surface'} px-1 py-1 transition-all duration-200 text-label-lg h-full flex items-center" href="admin.html">ADMIN</a>
                </div>
                <div class="flex items-center">
                    <!-- Right side kept empty for clean, minimalist layout -->
                </div>
            </nav>
        </header>
        `;
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initNavbar);
    } else {
        initNavbar();
    }
})();
