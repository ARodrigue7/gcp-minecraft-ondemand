def get_whitelist_approved_html(username):
    """Generates the HTML landing page for successful whitelist approval."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Whitelist Approved</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&display=swap');
        
        body {{
            font-family: 'Fredoka', sans-serif;
            background: radial-gradient(circle at center, #102e1c 0%, #091a10 70%, #040d08 100%);
            color: #fffbeb;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            overflow: hidden;
            position: relative;
            padding: 1.5rem;
        }}
        
        /* Fireflies animation */
        .firefly {{
            position: absolute;
            width: 6px;
            height: 6px;
            background: #fde047;
            border-radius: 50%;
            filter: drop-shadow(0 0 4px #fbbf24);
            opacity: 0;
            animation: float-glow 8s infinite ease-in-out;
            pointer-events: none;
        }}
        
        .ff-1 {{ top: 15%; left: 10%; animation-delay: 0s; }}
        .ff-2 {{ top: 45%; left: 85%; animation-delay: 2s; }}
        .ff-3 {{ top: 75%; left: 25%; animation-delay: 4.5s; }}
        .ff-4 {{ top: 25%; left: 70%; animation-delay: 1s; }}
        .ff-5 {{ top: 85%; left: 80%; animation-delay: 6s; }}
        
        @keyframes float-glow {{
            0%, 100% {{ transform: translateY(0) scale(0.8); opacity: 0; }}
            50% {{ transform: translateY(-20px) scale(1.2); opacity: 0.8; }}
        }}
        
        /* Woodland wooden card */
        .card {{
            background-color: rgba(16, 37, 24, 0.85);
            border: 4px solid #422006;
            border-radius: 28px;
            padding: 3rem 2.5rem;
            text-align: center;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.7),
                        inset 0 0 20px rgba(0, 0, 0, 0.5);
            position: relative;
            z-index: 10;
        }}
        
        .card::before {{
            content: "";
            position: absolute;
            top: 4px;
            left: 4px;
            right: 4px;
            bottom: 4px;
            border: 2px dashed rgba(255, 255, 255, 0.08);
            border-radius: 22px;
            pointer-events: none;
        }}
        
        /* Checkmark badge */
        .badge-circle {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 76px;
            height: 76px;
            background: linear-gradient(135deg, #10b981, #047857);
            border: 3px solid #143520;
            border-radius: 50%;
            margin-bottom: 1.5rem;
            color: #fffbeb;
            box-shadow: 0 6px 0 #143520,
                        inset 0 2px 4px rgba(255, 255, 255, 0.3);
        }}
        
        .badge-circle svg {{
            filter: drop-shadow(0 2px 2px rgba(0,0,0,0.3));
        }}
        
        /* Header 3D outline styling */
        h1 {{
            font-family: 'Fredoka', sans-serif;
            font-size: 2.2rem;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 1.25rem;
            color: #ffffff;
            text-shadow: 2px 2px 0 #422006,
                         -2px -2px 0 #422006,
                         2px -2px 0 #422006,
                         -2px 2px 0 #422006,
                         0 4px 0 #422006,
                         0 8px 12px rgba(0, 0, 0, 0.5);
        }}
        
        p {{
            color: #a7f3d0;
            line-height: 1.6;
            font-size: 1.05rem;
            margin-bottom: 1.75rem;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
        }}
        
        /* Wood-plank-style username badge */
        .username-badge {{
            display: inline-block;
            background: linear-gradient(to bottom, #c2844a, #8c5325);
            border: 3px solid #422006;
            color: #fffbeb;
            padding: 0.6rem 1.75rem;
            border-radius: 14px;
            font-weight: 700;
            font-size: 1.25rem;
            margin-bottom: 1.75rem;
            box-shadow: 0 5px 0 #422006,
                        inset 0 1px 0 rgba(255, 255, 255, 0.3);
            letter-spacing: 0.03em;
            text-shadow: 2px 2px 0 #422006;
        }}
        
        .note {{
            font-size: 0.9rem;
            color: #a7f3d0;
            opacity: 0.8;
            border-top: 2px dashed rgba(255, 255, 255, 0.08);
            padding-top: 1.5rem;
            margin-bottom: 0;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="firefly ff-1"></div>
    <div class="firefly ff-2"></div>
    <div class="firefly ff-3"></div>
    <div class="firefly ff-4"></div>
    <div class="firefly ff-5"></div>
    <div class="card">
        <div class="badge-circle">
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <h1>✓ Whitelist Approved</h1>
        <p>The player's request has been authorized and queued.</p>
        <div class="username-badge">{username}</div>
        <p class="note">The watchdog on the GCE server checks metadata changes and will execute the whitelist sync within 60 seconds.</p>
    </div>
</body>
</html>"""

def get_whitelist_denied_html(username):
    """Generates the HTML landing page for a denied/dismissed whitelist request."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Request Denied</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&display=swap');
        
        body {{
            font-family: 'Fredoka', sans-serif;
            background: radial-gradient(circle at center, #2e1010 0%, #1a0909 70%, #0d0404 100%);
            color: #fffbeb;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            overflow: hidden;
            position: relative;
            padding: 1.5rem;
        }}
        
        /* Woodland wooden card */
        .card {{
            background-color: rgba(37, 16, 16, 0.85);
            border: 4px solid #422006;
            border-radius: 28px;
            padding: 3rem 2.5rem;
            text-align: center;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.7),
                        inset 0 0 20px rgba(0, 0, 0, 0.5);
            position: relative;
            z-index: 10;
        }}
        
        .card::before {{
            content: "";
            position: absolute;
            top: 4px;
            left: 4px;
            right: 4px;
            bottom: 4px;
            border: 2px dashed rgba(255, 255, 255, 0.08);
            border-radius: 22px;
            pointer-events: none;
        }}
        
        /* Denied badge */
        .badge-circle {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            width: 76px;
            height: 76px;
            background: linear-gradient(135deg, #ef4444, #b91c1c);
            border: 3px solid #351414;
            border-radius: 50%;
            margin-bottom: 1.5rem;
            color: #fffbeb;
            box-shadow: 0 6px 0 #351414,
                        inset 0 2px 4px rgba(255, 255, 255, 0.3);
        }}
        
        .badge-circle svg {{
            filter: drop-shadow(0 2px 2px rgba(0,0,0,0.3));
        }}
        
        /* Header 3D outline styling */
        h1 {{
            font-family: 'Fredoka', sans-serif;
            font-size: 2.2rem;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 1.25rem;
            color: #ffffff;
            text-shadow: 2px 2px 0 #422006,
                         -2px -2px 0 #422006,
                         2px -2px 0 #422006,
                         -2px 2px 0 #422006,
                         0 4px 0 #422006,
                         0 8px 12px rgba(0, 0, 0, 0.5);
        }}
        
        p {{
            color: #fca5a5;
            line-height: 1.6;
            font-size: 1.05rem;
            margin-bottom: 1.75rem;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
        }}
        
        /* Wood-plank-style username badge */
        .username-badge {{
            display: inline-block;
            background: linear-gradient(to bottom, #c2844a, #8c5325);
            border: 3px solid #422006;
            color: #fffbeb;
            padding: 0.6rem 1.75rem;
            border-radius: 14px;
            font-weight: 700;
            font-size: 1.25rem;
            margin-bottom: 1.75rem;
            box-shadow: 0 5px 0 #422006,
                        inset 0 1px 0 rgba(255, 255, 255, 0.3);
            letter-spacing: 0.03em;
            text-shadow: 2px 2px 0 #422006;
        }}
        
        .note {{
            font-size: 0.9rem;
            color: #fca5a5;
            opacity: 0.8;
            border-top: 2px dashed rgba(255, 255, 255, 0.08);
            padding-top: 1.5rem;
            margin-bottom: 0;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="badge-circle">
            <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </div>
        <h1>✗ Request Denied</h1>
        <p>The player's request has been denied and dismissed.</p>
        <div class="username-badge">{username}</div>
        <p class="note">The Discord channel alert has been removed. The player must submit a new request if this was a mistake.</p>
    </div>
</body>
</html>"""
