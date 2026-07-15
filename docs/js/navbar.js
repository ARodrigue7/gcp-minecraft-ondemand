(function() {
    function initNavbar() {
        // 1. Render Top Navbar (if container exists)
        const container = document.getElementById("global-navbar");
        let activeTab = "landing";
        
        if (container) {
            activeTab = container.getAttribute("data-active-tab") || "landing";
            container.innerHTML = `
            <header class="bg-surface/90 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <nav class="flex justify-between items-center w-full px-base md:px-margin max-w-container-max mx-auto h-14">
                    <div class="flex items-center gap-3 cursor-pointer" onclick="window.location.href='index.html'">
                        <span class="font-headline-lg text-[20px] font-bold text-primary uppercase tracking-[0.1em]">GCP Minecraft</span>
                    </div>
                    <div class="hidden md:flex gap-8 items-center h-full">
                        <a class="${activeTab === 'landing' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface/60 hover:text-on-surface'} px-1 py-1 transition-all duration-200 text-label-lg h-full flex items-center" href="index.html">LANDING</a>
                        <a class="${activeTab === 'getting-started' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface/60 hover:text-on-surface'} px-1 py-1 transition-all duration-200 text-label-lg h-full flex items-center" href="getting-started.html">GETTING STARTED</a>
                        <a class="${activeTab === 'servers' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface/60 hover:text-on-surface'} px-1 py-1 transition-all duration-200 text-label-lg h-full flex items-center" href="play.html">SERVERS</a>
                        <a class="${activeTab === 'admin' ? 'text-primary font-bold border-b-2 border-primary' : 'text-on-surface/60 hover:text-on-surface'} px-1 py-1 transition-all duration-200 text-label-lg h-full flex items-center" href="admin.html">ADMIN</a>
                    </div>
                    <div class="flex items-center">
                        <!-- Right side kept empty for clean, minimalist layout -->
                    </div>
                </nav>
            </header>
            `;
        } else {
            // Determine active tab based on path fallback for pages without global-navbar (like admin panel)
            const path = window.location.pathname;
            if (path.includes("play.html")) {
                activeTab = "servers";
            } else if (path.includes("admin.html")) {
                activeTab = "admin";
            } else if (path.includes("getting-started.html")) {
                activeTab = "getting-started";
            }
        }

        // 2. Render Bottom Navbar for Mobile (on all pages)
        const existingBottomNav = document.getElementById("global-bottom-navbar");
        if (existingBottomNav) {
            existingBottomNav.remove();
        }

        const bottomNav = document.createElement("nav");
        bottomNav.id = "global-bottom-navbar";
        bottomNav.className = "fixed bottom-0 left-0 w-full flex justify-around items-center h-16 md:hidden bg-grass-deep/95 backdrop-blur-sm border-t border-white/10 z-50";
        
        bottomNav.innerHTML = `
            <a class="flex items-center justify-center ${activeTab === 'landing' ? 'text-primary' : 'text-on-surface-variant'} transition-transform duration-100 active:scale-95 w-full h-full" href="index.html">
                <span class="material-symbols-outlined text-[28px]">dns</span>
            </a>
            <a class="flex items-center justify-center ${activeTab === 'getting-started' ? 'text-primary' : 'text-on-surface-variant'} transition-transform duration-100 active:scale-95 w-full h-full" href="getting-started.html">
                <span class="material-symbols-outlined text-[28px]">description</span>
            </a>
            <a class="flex items-center justify-center ${activeTab === 'servers' ? 'text-primary' : 'text-on-surface-variant'} transition-transform duration-100 active:scale-95 w-full h-full" href="play.html">
                <span class="material-symbols-outlined text-[28px]">sports_esports</span>
            </a>
            <a class="flex items-center justify-center ${activeTab === 'admin' ? 'text-primary' : 'text-on-surface-variant'} transition-transform duration-100 active:scale-95 w-full h-full" href="admin.html">
                <span class="material-symbols-outlined text-[28px]">shield</span>
            </a>
        `;

        document.body.appendChild(bottomNav);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initNavbar);
    } else {
        initNavbar();
    }
})();
