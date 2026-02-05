import os
import webbrowser
import requests
import threading
import logging
import secrets
from flask import Flask, request
from werkzeug.serving import make_server

# Suppress Flask CLI logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

class DiscordLogin:
    def __init__(self, client_id, client_secret, redirect_uri="http://localhost:5000/callback"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.user_info = None
        self.app = Flask(__name__)
        self.server = None
        self.thread = None
        self.auth_event = threading.Event()
        
        # Define routes
        self.app.add_url_rule('/callback', 'callback', self.callback_handler)

    def callback_handler(self):
        code = request.args.get('code')
        if code:
            success = self.exchange_code(code)
            if success:
                self.auth_event.set()  # SIGNAL SUCCESS!
                return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Jutsu Academy - Access Granted</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;800&display=swap');

            * {
                box-sizing: border-box;
            }

            html, body {
                margin: 0;
                height: 100%;
                font-family: 'Nunito Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: radial-gradient(circle at top, #1f2933 0%, #050608 55%, #050608 100%);
                color: #f9fafb;
                overflow: hidden;
            }

            .overlay {
                position: fixed;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                z-index: 2;
            }

            .card {
                position: relative;
                background: linear-gradient(180deg, #201d1a 0%, #141211 100%);
                border-radius: 22px;
                padding: 44px 54px 38px;
                max-width: 480px;
                text-align: center;
                box-shadow:
                    0 18px 45px rgba(0, 0, 0, 0.85),
                    0 0 0 1px rgba(249, 115, 22, 0.45);
            }

            .card::before {
                content: "";
                position: absolute;
                inset: 1px;
                border-radius: 20px;
                background: radial-gradient(circle at top, rgba(249, 115, 22, 0.08), transparent 55%);
                pointer-events: none;
                z-index: -1;
            }

            .ninja {
                width: 76px;
                height: 76px;
                border-radius: 50%;
                margin: 0 auto 18px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 42px;
                background: radial-gradient(circle, #22c55e 0%, #14532d 55%, #020617 100%);
                box-shadow: 0 0 18px rgba(34, 197, 94, 0.9);
            }

            .badge {
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.22em;
                color: #9ca3af;
                margin-bottom: 6px;
            }

            h1 {
                margin: 0;
                font-size: 26px;
                letter-spacing: 0.18em;
                text-transform: uppercase;
                color: #fed7aa;
            }

            .title-highlight {
                color: #f97316;
            }

            .divider {
                width: 80px;
                height: 2px;
                margin: 20px auto 18px;
                background: linear-gradient(90deg, transparent, #f97316, transparent);
            }

            p {
                margin: 0;
                font-size: 14px;
                line-height: 1.7;
                color: #e5e7eb;
            }

            .button {
                margin-top: 28px;
                padding: 12px 30px;
                border-radius: 999px;
                border: none;
                cursor: pointer;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                background: linear-gradient(135deg, #f59e0b, #f97316);
                color: #111827;
                box-shadow:
                    0 12px 25px rgba(15, 23, 42, 0.9),
                    0 0 24px rgba(249, 115, 22, 0.7);
                transition: transform 0.12s ease-out, box-shadow 0.12s ease-out, filter 0.12s ease-out;
            }

            .button:hover {
                transform: translateY(-1px);
                filter: brightness(1.05);
                box-shadow:
                    0 16px 35px rgba(15, 23, 42, 1),
                    0 0 30px rgba(249, 115, 22, 0.9);
            }

            .hint {
                margin-top: 14px;
                font-size: 11px;
                color: #9ca3af;
            }

            /* Warm chakra particles (kanji) */

            .particles {
                position: fixed;
                inset: 0;
                overflow: hidden;
                pointer-events: none;
                z-index: 1;
            }

            .particle {
                position: absolute;
                font-size: 20px;
                color: rgba(248, 184, 120, 0.35);
                animation: floatUp linear infinite;
                white-space: nowrap;
                text-shadow:
                    0 0 10px rgba(249, 115, 22, 0.95),
                    0 0 18px rgba(245, 158, 11, 0.8);
            }

            @keyframes floatUp {
                0% {
                    transform: translate3d(0, 110vh, 0) rotate(-6deg);
                    opacity: 0;
                }
                10% {
                    opacity: 0.9;
                }
                90% {
                    opacity: 0.9;
                }
                100% {
                    transform: translate3d(0, -15vh, 0) rotate(4deg);
                    opacity: 0;
                }
            }
        </style>
    </head>
    <body>
        <div class="particles" id="particles"></div>

        <div class="overlay">
            <div class="card">
                <div class="ninja">🥷</div>
                <div class="badge">Jutsu Academy · Authentication</div>
                <h1><span class="title-highlight">Access</span> Granted</h1>
                <div class="divider"></div>
                <p>
                    Your chakra signature has been verified.<br>
                    The village gates have opened for you, shinobi.
                </p>
                <button class="button" onclick="window.close()">Return to Jutsu Academy</button>
                <div class="hint">If this window doesn't close, you can close it manually.</div>
            </div>
        </div>

        <script>
            (function () {
                const kanji = ["忍", "炎", "心", "影", "光"];
                const particleCount = 18;
                const container = document.getElementById("particles");

                function random(min, max) {
                    return Math.random() * (max - min) + min;
                }

                for (let i = 0; i < particleCount; i++) {
                    const span = document.createElement("span");
                    span.className = "particle";
                    span.textContent = kanji[Math.floor(Math.random() * kanji.length)];

                    const startLeft = random(-5, 100);  // vw
                    const duration = random(11, 20);     // seconds
                    const delay = random(-duration, 0); // start at random point
                    const size = random(18, 30);        // px

                    span.style.left = startLeft + "vw";
                    span.style.animationDuration = duration + "s";
                    span.style.animationDelay = delay + "s";
                    span.style.fontSize = size + "px";
                    span.style.opacity = random(0.3, 0.8);

                    container.appendChild(span);
                }
            })();
        </script>
    </body>
    </html>
    """

        # Authentication failed (no code or exchange failed)
        return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Jutsu Academy - Access Denied</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;800&display=swap');

            * {
                box-sizing: border-box;
            }

            html, body {
                margin: 0;
                height: 100%;
                font-family: 'Nunito Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: radial-gradient(circle at top, #1f2933 0%, #050608 55%, #050608 100%);
                color: #f9fafb;
                overflow: hidden;
            }

            .overlay {
                position: fixed;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
                z-index: 2;
            }

            .card {
                position: relative;
                background: linear-gradient(180deg, #211715 0%, #140c0b 100%);
                border-radius: 22px;
                padding: 44px 54px 38px;
                max-width: 480px;
                text-align: center;
                box-shadow:
                    0 18px 45px rgba(0, 0, 0, 0.9),
                    0 0 0 1px rgba(239, 68, 68, 0.55);
            }

            .card::before {
                content: "";
                position: absolute;
                inset: 1px;
                border-radius: 20px;
                background: radial-gradient(circle at top, rgba(239, 68, 68, 0.12), transparent 55%);
                pointer-events: none;
                z-index: -1;
            }

            .icon {
                width: 70px;
                height: 70px;
                border-radius: 50%;
                margin: 0 auto 18px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 34px;
                background: radial-gradient(circle, #7f1d1d 0%, #450a0a 55%, #020617 100%);
                box-shadow: 0 0 16px rgba(248, 113, 113, 0.9);
            }

            .badge {
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.22em;
                color: #9ca3af;
                margin-bottom: 6px;
            }

            h1 {
                margin: 0;
                font-size: 24px;
                letter-spacing: 0.18em;
                text-transform: uppercase;
                color: #fecaca;
            }

            .title-highlight {
                color: #f87171;
            }

            .divider {
                width: 80px;
                height: 2px;
                margin: 20px auto 18px;
                background: linear-gradient(90deg, transparent, #f87171, transparent);
            }

            p {
                margin: 0;
                font-size: 14px;
                line-height: 1.7;
                color: #e5e7eb;
            }

            .button {
                margin-top: 28px;
                padding: 12px 30px;
                border-radius: 999px;
                border: none;
                cursor: pointer;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                background: linear-gradient(135deg, #f97373, #ef4444);
                color: #111827;
                box-shadow:
                    0 12px 25px rgba(15, 23, 42, 0.9),
                    0 0 24px rgba(239, 68, 68, 0.8);
                transition: transform 0.12s ease-out, box-shadow 0.12s ease-out, filter 0.12s ease-out;
            }

            .button:hover {
                transform: translateY(-1px);
                filter: brightness(1.05);
                box-shadow:
                    0 16px 35px rgba(15, 23, 42, 1),
                    0 0 30px rgba(239, 68, 68, 1);
            }

            .hint {
                margin-top: 14px;
                font-size: 11px;
                color: #9ca3af;
            }

            /* Warning chakra particles */

            .particles {
                position: fixed;
                inset: 0;
                overflow: hidden;
                pointer-events: none;
                z-index: 1;
            }

            .particle {
                position: absolute;
                font-size: 20px;
                color: rgba(248, 113, 113, 0.35);
                animation: floatUp linear infinite;
                white-space: nowrap;
                text-shadow:
                    0 0 10px rgba(248, 113, 113, 0.95),
                    0 0 18px rgba(220, 38, 38, 0.85);
            }

            @keyframes floatUp {
                0% {
                    transform: translate3d(0, 110vh, 0) rotate(5deg);
                    opacity: 0;
                }
                10% {
                    opacity: 0.9;
                }
                90% {
                    opacity: 0.9;
                }
                100% {
                    transform: translate3d(0, -15vh, 0) rotate(-4deg);
                    opacity: 0;
                }
            }
        </style>
    </head>
    <body>
        <div class="particles" id="particles"></div>

        <div class="overlay">
            <div class="card">
                <div class="icon">⚠️</div>
                <div class="badge">Jutsu Academy · Authentication</div>
                <h1><span class="title-highlight">Access</span> Denied</h1>
                <div class="divider"></div>
                <p>
                    The barrier seals rejected your chakra.<br>
                    This login attempt could not be verified.
                </p>
                <button class="button" onclick="window.close()">Close Window</button>
                <div class="hint">Return to Jutsu Academy and try logging in again.</div>
            </div>
        </div>

        <script>
            (function () {
                const kanji = ["封", "禁", "警", "影", "断"];
                const particleCount = 16;
                const container = document.getElementById("particles");

                function random(min, max) {
                    return Math.random() * (max - min) + min;
                }

                for (let i = 0; i < particleCount; i++) {
                    const span = document.createElement("span");
                    span.className = "particle";
                    span.textContent = kanji[Math.floor(Math.random() * kanji.length)];

                    const startLeft = random(-5, 100);  // vw
                    const duration = random(11, 20);     // seconds
                    const delay = random(-duration, 0); // start at random point
                    const size = random(18, 30);        // px

                    span.style.left = startLeft + "vw";
                    span.style.animationDuration = duration + "s";
                    span.style.animationDelay = delay + "s";
                    span.style.fontSize = size + "px";
                    span.style.opacity = random(0.35, 0.85);

                    container.appendChild(span);
                }
            })();
        </script>
    </body>
    </html>
    """


    def get_authorize_url(self):
        """Generate and return the OAuth authorization URL with random state."""
        state = secrets.token_urlsafe(16)  # Random state to prevent caching
        return (f"https://discord.com/api/oauth2/authorize?client_id={self.client_id}"
                f"&redirect_uri={self.redirect_uri}&response_type=code&scope=identify&state={state}")

    def login(self, timeout=120):
        """Starts the local server and waits for auth callback.
        
        Args:
            timeout: Maximum seconds to wait for auth (default 120)
            
        Returns:
            User info dict on success, None on timeout/failure
        """
        print(f"[AUTH] Starting Discord Login Flow (timeout={timeout}s)...")
        try:
            # Start server in thread
            self.server = make_server('localhost', 5000, self.app, threaded=True)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            print("[AUTH] Local callback server started on port 5000")
            
            # Wait for auth with timeout
            print("[AUTH] Waiting for user to authorize in browser...")
            auth_completed = self.auth_event.wait(timeout=timeout)
            
            if not auth_completed:
                print(f"[AUTH] Timeout after {timeout}s waiting for callback")
                return None
            
        except Exception as e:
            print(f"[AUTH] Discord Login Error: {e}")
            return None
        finally:
            self.shutdown()
                
        return self.user_info

    def shutdown(self):
        """Shutdown the local server."""
        if self.server:
            def shutdown_server(srv):
                try:
                    srv.shutdown()
                    print("[AUTH] Callback server shut down")
                except:
                    pass
            
            threading.Thread(target=shutdown_server, args=(self.server,), daemon=True).start()
            self.server = None

    def exchange_code(self, code):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
            r.raise_for_status()
            token = r.json().get('access_token')
            
            # Get User Info
            r2 = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {token}"})
            r2.raise_for_status()
            self.user_info = r2.json()
            self.user_info['access_token'] = token # Store token for refreshing
            print(f"[+] Discord User Authenticated: {self.user_info.get('username')}")
            return True
            
        except Exception as e:
            print(f"[!] Auth Code Exchange Error: {e}")
            return False
