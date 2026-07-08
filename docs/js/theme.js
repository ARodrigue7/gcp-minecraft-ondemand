tailwind.config = {
    theme: {
        extend: {
            "colors": {
                "primary": "#F39C12",
                "gold-accent": "#ffbe70",
                "surface": "#15221b",
                "surface-bright": "#202d25",
                "surface-variant": "#2a3830",
                "on-surface": "#d7e6db",
                "on-surface-variant": "#a2b5aa",
                "grass-lush": "#1c3b2b",
                "grass-deep": "#09160f",
                "background": "#05110a",
                "error": "#ffb4ab",
                "error-container": "#93000a",
                "secondary": "#a3d2a1",
                "secondary-container": "#264f2a",
                "primary-container": "#ffddb9",
                "on-primary-container": "#311b00",
                "on-primary-fixed-variant": "#663e00",
                "primary-fixed": "#ffddb9",
                "secondary-fixed-dim": "#a3d2a1",
                "surface-container": "#15221b",
                "wood-bark": "#E67E22"
            },
            "borderRadius": {
                "DEFAULT": "0.125rem",
                "lg": "0.25rem",
                "xl": "0.5rem",
                "full": "0.75rem"
            },
            "spacing": {
                "container-max": "1200px",
                "gutter": "16px",
                "margin": "24px",
                "base": "8px"
            },
            "fontFamily": {
                "headline-lg": ["Space Mono"],
                "label-lg": ["JetBrains Mono"],
                "headline-lg-mobile": ["Space Mono"],
                "display-lg": ["Space Mono"],
                "body-md": ["Be Vietnam Pro"],
                "body-lg": ["Be Vietnam Pro"],
                "label-sm": ["JetBrains Mono"],
                "title-md": ["Space Mono"]
            },
            "fontSize": {
                "headline-lg": ["28px", {"lineHeight": "1.2", "fontWeight": "700"}],
                "label-lg": ["13px", {"lineHeight": "1.0", "fontWeight": "600"}],
                "headline-lg-mobile": ["22px", {"lineHeight": "1.2", "fontWeight": "700"}],
                "display-lg": ["36px", {"lineHeight": "1.1", "letterSpacing": "-0.02em", "fontWeight": "700"}],
                "body-md": ["14px", {"lineHeight": "1.6", "fontWeight": "400"}],
                "body-lg": ["16px", {"lineHeight": "1.6", "fontWeight": "400"}],
                "label-sm": ["11px", {"lineHeight": "1.0", "fontWeight": "500"}],
                "title-md": ["18px", {"lineHeight": "1.4", "fontWeight": "700"}]
            }
        }
    }
};
