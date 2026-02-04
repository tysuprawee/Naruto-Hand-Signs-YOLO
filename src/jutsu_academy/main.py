import customtkinter as ctk
import sys
import os
import cv2
import threading
from PIL import Image
import numpy as np
import webbrowser
import requests
import json
from io import BytesIO
import pygame  # Add pygame import
import base64

try:
    from pygrabber.dshow_graph import FilterGraph
    import comtypes
except ImportError:
    FilterGraph = None

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.jutsu_academy.game_engine import GameSession, NetworkManager

# --- Supabase Cloud Integration (Secure) ---
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client, Client
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None



ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class LauncherApp(ctk.CTk):
    APP_VERSION = "1.0.0"  # Current app version
    
    def __init__(self):
        super().__init__()

        self.title(f"Jutsu Academy v{self.APP_VERSION}")
        self.geometry("1024x768")
        
        # State
        self.current_session = None
        self.is_game_active = False
        self.selected_camera_index = 0
        self.username = "Ninja" # Default user
        self.camera_map = {}
        self.announcements = []  # Store fetched announcements
        
        self.load_session() # Load persistent login
        
        # --- ONLINE STATUS ---
        self.online = supabase is not None  # Check if Supabase client was created
        
        # --- FETCH ANNOUNCEMENTS (Background) ---
        if self.online:
            threading.Thread(target=self._fetch_announcements, daemon=True).start()

        # --- AUDIO ---
        self.music_volume = 0.35
        self.is_muted = False
        self.try_play_music()
    
    def _fetch_announcements(self):
        """Fetch announcements from Supabase in background."""
        try:
            # Only fetch active announcements (not version entries)
            response = supabase.table("app_config").select("*").eq("type", "announcement").eq("is_active", True).order("priority", desc=True).order("created_at", desc=True).limit(10).execute()
            self.announcements = response.data if response.data else []
            if self.announcements:
                print(f"[+] Loaded {len(self.announcements)} announcement(s)")
                # Show popup on main thread after short delay
                self.after(1500, self._show_announcement_popup)
        except Exception as e:
            print(f"[!] Failed to fetch announcements: {e}")
    
    def _show_announcement_popup(self):
        """Show paginated announcement popup as overlay in main window."""
        if not self.announcements:
            return
        
        # Create dark overlay backdrop (covers entire window)
        self.announcement_overlay = ctk.CTkFrame(self, fg_color="#000000")
        self.announcement_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.announcement_overlay.configure(fg_color=("#000000", "#000000"))  # Semi-dark backdrop
        
        # Create popup card (centered)
        popup_card = ctk.CTkFrame(self.announcement_overlay, fg_color="#2a2a2f", corner_radius=20, width=450, height=300)
        popup_card.place(relx=0.5, rely=0.5, anchor="center")
        popup_card.pack_propagate(False)
        
        # Inner card
        inner_card = ctk.CTkFrame(popup_card, fg_color="#18181b", corner_radius=18)
        inner_card.pack(fill="both", expand=True, padx=3, pady=3)
        
        # State for pagination
        current_page = [0]
        total_pages = len(self.announcements)
        
        # Title
        ctk.CTkLabel(inner_card, text="📢 ANNOUNCEMENTS", font=("Impact", 28), text_color="#f59e0b").pack(pady=(25, 10))
        
        # Page indicator
        page_label = ctk.CTkLabel(inner_card, text=f"1 / {total_pages}", font=("Arial", 12), text_color="#666")
        page_label.pack()
        
        # Message content
        message_label = ctk.CTkLabel(inner_card, text="", font=("Arial", 15), text_color="white", wraplength=400, justify="center")
        message_label.pack(pady=25, padx=30, fill="both", expand=True)
        
        def close_popup():
            self.announcement_overlay.destroy()
        
        def update_content():
            idx = current_page[0]
            msg = self.announcements[idx].get("message", "No message")
            if isinstance(msg, list):
                msg = msg[0] if msg else "No message"
            message_label.configure(text=str(msg))
            page_label.configure(text=f"{idx + 1} / {total_pages}")
            btn_prev.configure(state="normal" if idx > 0 else "disabled")
            btn_next.configure(state="normal" if idx < total_pages - 1 else "disabled")
        
        def prev_page():
            if current_page[0] > 0:
                current_page[0] -= 1
                update_content()
        
        def next_page():
            if current_page[0] < total_pages - 1:
                current_page[0] += 1
                update_content()
        
        # Navigation buttons
        nav_frame = ctk.CTkFrame(inner_card, fg_color="transparent")
        nav_frame.pack(pady=20)
        
        btn_prev = ctk.CTkButton(nav_frame, text="< Prev", width=90, height=35, fg_color="#333", hover_color="#555", font=("Arial", 13), command=prev_page)
        btn_prev.pack(side="left", padx=8)
        
        ctk.CTkButton(nav_frame, text="Close", width=90, height=35, fg_color="#f59e0b", hover_color="#d97706", font=("Arial", 13, "bold"), command=close_popup).pack(side="left", padx=8)
        
        btn_next = ctk.CTkButton(nav_frame, text="Next >", width=90, height=35, fg_color="#333", hover_color="#555", font=("Arial", 13), command=next_page)
        btn_next.pack(side="left", padx=8)
        
        # Initial content
        update_content()
        
        # Lift overlay to top
        self.announcement_overlay.lift()
    
    def _count_custom_jutsus(self):
        """Count custom jutsus from local storage."""
        try:
            custom_path = os.path.join("src", "custom_jutsus.dat")
            if not os.path.exists(custom_path):
                return 0
            with open(custom_path, "rb") as f:
                encoded = f.read()
                data = json.loads(base64.b64decode(encoded).decode('utf-8'))
                return len(data)
        except:
            return 0

    def try_play_music(self):
        try:
            pygame.mixer.init()
            music_path = os.path.join("src", "sounds", "music2.mp3")
            if os.path.exists(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1, fade_ms=2000)
                print("[+] Music started")
            else:
                print(f"[!] Music file not found: {music_path}")
        except Exception as e:
            print(f"[!] Audio Init Failed: {e}")

    # --- LAYOUT MANAGEMENT ---

        # --- LAYOUT MANAGEMENT ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Menu Frame (Visible by default)
        self.menu_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.menu_frame.grid(row=0, column=0, sticky="nsew")
        
        self.setup_menu() # Call setup_menu

        # 2. Game Frame (Hidden by default)
        self.game_frame = ctk.CTkFrame(self, fg_color="black")
        self.game_frame.grid(row=0, column=0, sticky="nsew")
        self.game_frame.grid_remove() # Hide initially
        
        # Display Label for Game (Where we blit the image)
        self.game_label = ctk.CTkLabel(self.game_frame, text="")
        self.game_label.pack(expand=True, fill="both")
        
        # Overlay        button_bg = "#333" # Default dark
        
        # --- UI OVERLAY ---
        # Exit (Top Left)
        self.btn_exit = ctk.CTkButton(
            self.game_frame,
            text="EXIT TO MENU",
            font=("Arial", 12, "bold"),
            fg_color="#D32F2F",
            hover_color="#b91c1c",
            width=120, height=35,
            corner_radius=0, # Square to avoid black corners
            command=self.stop_game
        )
        self.btn_exit.place(x=20, y=20)
        
        # Settings (Top Left, next to Exit)
        self.btn_ingame_settings = ctk.CTkButton(
            self.game_frame,
            text="SETTINGS",
            font=("Arial", 12, "bold"),
            fg_color="#333",
            hover_color="#555",
            width=100, height=35,
            corner_radius=0, # Square
            command=self.show_settings_menu
        )
        self.btn_ingame_settings.place(x=150, y=20)
        
        # --- GAME CONTROLS OVERLAY ---
        # Jutsu Name
        self.lbl_jutsu_name = ctk.CTkLabel(
            self.game_frame,
            text="",
            font=("Impact", 24),
            text_color="#00EE00",
            fg_color="#202020", # Keep this or make transparent if possible? Transparent implies parent color (black).
            corner_radius=0, # Square
            width=200, height=40
        )
        self.lbl_jutsu_name.place(relx=0.5, y=40, anchor="center")

        # ... (Prev/Next Buttons remain) ...
        self.btn_prev = ctk.CTkButton(
            self.game_frame,
            text="<",
            font=("Arial", 20, "bold"),
            width=50, height=50,
            corner_radius=0, # Square
            fg_color="#404040",
            hover_color="#606060",
            command=self.prev_jutsu
        )
        self.btn_prev.place(relx=0.05, rely=0.5, anchor="center")
        
        self.btn_next = ctk.CTkButton(
            self.game_frame,
            text=">",
            font=("Arial", 20, "bold"),
            width=50, height=50,
            corner_radius=0, # Square
            fg_color="#404040",
            hover_color="#606060",
            command=self.next_jutsu
        )
        self.btn_next.place(relx=0.95, rely=0.5, anchor="center")
        
        # Async Camera Load (Start AFTER UI is ready)
        threading.Thread(target=self.load_cameras_async, daemon=True).start()
        
    def load_cameras_async(self):
        cameras = self.get_available_cameras()
        # Schedule update on UI thread
        self.after(0, lambda: self.update_camera_dropdown(cameras))

    def update_camera_dropdown(self, cameras):
        self.available_cameras = cameras
        
        # Update Menu Dropdown
        if hasattr(self, 'camera_dropdown'):
            self.camera_dropdown.configure(values=cameras)
            if cameras:
                self.camera_dropdown.set(cameras[0])
                
        # Update In-Game Dropdown
        if hasattr(self, 'ingame_camera_dropdown'):
            self.ingame_camera_dropdown.configure(values=cameras)
            if cameras:
                self.ingame_camera_dropdown.set(cameras[0])
        
        if cameras:
            default = cameras[0]
            self.on_camera_select(default)
        
        self.camera_dropdown_ready = True
            
        
    def on_ingame_camera_select(self, choice):
        if choice in self.camera_map:
            new_index = self.camera_map[choice]
            self.selected_camera_index = new_index
            
            # Hot swap if game is running
            if self.current_session:
                self.current_session.switch_camera(new_index)
                
            # Sync menu dropdown
            self.camera_dropdown.set(choice)
        
    def get_available_cameras(self):
        # 1. Try PyGrabber (Best for Windows Names)
        if FilterGraph:
            try:
                # Initialize COM for this thread
                comtypes.CoInitialize()
                
                graph = FilterGraph()
                devices = graph.get_input_devices()
                print(f"[DEBUG] PyGrabber found devices: {devices}")
                if devices:
                    self.camera_map = {name: i for i, name in enumerate(devices)}
                    return devices
            except Exception as e:
                print(f"[ERROR] PyGrabber failed: {e}")
        else:
            print("[WARN] PyGrabber not imported (FilterGraph is None)")
        
        # 2. Fallback: Check Indexes 0-3 Manually
        print("[INFO] Falling back to OpenCV index search...")
        available = []
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                name = f"Camera Index {i}"
                available.append(name)
                self.camera_map[name] = i
                cap.release()
        
        if not available:
            return ["No Camera Found"]
            
        return available

    # --- SESSION MANAGEMENT ---
    def save_session(self):
        try:
            data = {
                "username": self.username,
                "discord_user": getattr(self, 'discord_user', None)
            }
            with open("user_session.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Failed to save session: {e}")

    def load_session(self):
        try:
            if os.path.exists("user_session.json"):
                with open("user_session.json", "r") as f:
                    data = json.load(f)
                    self.username = data.get("username", "Ninja")
                    self.discord_user = data.get("discord_user", None)
                    if self.discord_user:
                        print(f"[+] Loaded session for {self.username}")
                        # Auto-refresh profile in background
                        threading.Thread(target=self.refresh_profile_background, daemon=True).start()
        except Exception as e:
            print(f"Failed to load session: {e}")

    def refresh_profile_background(self):
        if not self.discord_user or 'access_token' not in self.discord_user:
            return
            
        try:
            token = self.discord_user['access_token']
            print("[*] Validating session token...")
            r = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
            if r.status_code == 200:
                new_info = r.json()
                # Preserve token in new info
                new_info['access_token'] = token 
                
                # Update State
                self.discord_user = new_info
                self.username = new_info['username']
                self.save_session()
                print(f"[+] Profile refreshed: {self.username}")
                
                # Refresh UI if app is running
                self.after(0, self.refresh_auth_ui)
            else:
                print(f"[-] Token invalid ({r.status_code}). Please relogin.")
        except Exception as e:
            print(f"[!] Profile refresh failed: {e}")

    def clear_session(self):
        self.username = "Ninja"
        self.discord_user = None
        if os.path.exists("user_session.json"):
            try:
                os.remove("user_session.json")
            except:
                pass


    def setup_menu(self):
        # 1. Background Image Handling
        try:
            bg_path = os.path.join("src", "socials", "vl2.png")
            if os.path.exists(bg_path):
                self.original_bg = Image.open(bg_path)
                self.bg_photo = ctk.CTkImage(self.original_bg, size=(1024, 768))
                self.bg_label = ctk.CTkLabel(self.menu_frame, image=self.bg_photo, text="")
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                self.menu_frame.bind("<Configure>", self.resize_bg)
        except Exception as e:
            print(f"Failed to load BG: {e}")

        # 2. Center wrapper (just for positioning)
        self.login_outer = ctk.CTkFrame(self.menu_frame, fg_color="transparent")
        self.login_outer.place(relx=0.5, rely=0.5, anchor="center")

        # 3. Card built as TWO frames (this fixes the weird double-edge)
        # Outer border layer
        self.center_panel = ctk.CTkFrame(
            self.login_outer,
            fg_color="#2a2a2f",     # border color
            corner_radius=26
        )
        self.center_panel.pack()

        # Inner content layer (slightly inset)
        inner = ctk.CTkFrame(
            self.center_panel,
            fg_color="#18181b",     # actual card background
            corner_radius=24
        )
        inner.pack(padx=2, pady=2)  # thickness of the "border"

        # Inner container with padding away from the rounded edges
        pnl = ctk.CTkFrame(inner, fg_color="transparent")
        pnl.pack(padx=40, pady=35, fill="both", expand=True)

        # Title
        try:
            pil_img = Image.open("src/pics/logo.png")
            # Calculate aspect ratio to fit width=380, max height=100
            w, h = pil_img.size
            aspect = w / h
            target_w = 380
            target_h = int(target_w / aspect)
            if target_h > 120:
                target_h = 120
                target_w = int(target_h * aspect)
                
            logo_img = ctk.CTkImage(pil_img, size=(target_w, target_h))
            ctk.CTkLabel(pnl, text="", image=logo_img).pack(pady=(0, 5))
        except:
            title_frame = ctk.CTkFrame(pnl, fg_color="transparent")
            title_frame.pack(pady=(0, 5))
            ctk.CTkLabel(title_frame, text="JUTSU", font=("Impact", 42), text_color="#f59e0b").pack(side="left")
            ctk.CTkLabel(title_frame, text=" ACADEMY", font=("Impact", 42), text_color="#f4f4f5").pack(side="left")
        ctk.CTkLabel(pnl, text="TRAIN • MASTER • RANK UP", font=("Arial", 11, "bold"), text_color="#71717a").pack(pady=(0, 35))

        # --- AUTH SECTION ---
        self.auth_frame = ctk.CTkFrame(
            pnl,
            fg_color="#27272a",
            corner_radius=14
        )
        self.auth_frame.pack(pady=(0, 20), fill="x", ipady=10)

        self.refresh_auth_ui()

        # --- ENTER ACTION ---
        ctk.CTkButton(
            pnl,
            text="ENTER ACADEMY",
            font=("Arial", 16, "bold"),
            height=55,
            corner_radius=10,
            fg_color="#f59e0b",
            hover_color="#d97706",
            text_color="black",
            command=self.show_practice_menu
        ).pack(fill="x", pady=10)

        # --- MUTE BUTTON (Top Right) ---
        try:
            self.icon_unmute = ctk.CTkImage(Image.open("src/pics/unmute.png"), size=(24, 24))
            self.icon_mute = ctk.CTkImage(Image.open("src/pics/mute.png"), size=(24, 24))
        except:
             self.icon_unmute = None
             self.icon_mute = None

        self.btn_mute = ctk.CTkButton(
            self.menu_frame,
            text="" if self.icon_unmute else "🔊",
            image=self.icon_unmute,
            width=40, height=40,
            font=("Arial", 20),
            fg_color="#333",
            hover_color="#555",
            command=self.toggle_mute
        )
        self.btn_mute.place(relx=0.95, rely=0.05, anchor="ne")


        # Social Icons
        social_frame = ctk.CTkFrame(pnl, fg_color="transparent")
        social_frame.pack(pady=(0, 10))

        def load_icon(filename):
            try:
                path = os.path.join("src", "socials", filename)
                img = Image.open(path)
                return ctk.CTkImage(img, size=(24, 24))
            except Exception:
                return None

        def social_btn(img, link):
            if img:
                ctk.CTkButton(
                    social_frame,
                    text="",
                    image=img,
                    width=32,
                    height=32,
                    fg_color="transparent",
                    hover_color="#27272a",
                    corner_radius=8,
                    command=lambda: webbrowser.open(link)
                ).pack(side="left", padx=5)

        social_btn(load_icon("ig.png"), "https://www.instagram.com/james.uzumaki_/")
        social_btn(load_icon("yt.png"), "https://www.youtube.com/@James_Uzumaki")
        social_btn(load_icon("discord.png"), "https://discord.gg/7xBQ22SnN2")

        # Meta Links
        ctk.CTkButton(
            pnl,
            text="About Jutsu Academy",
            font=("Arial", 11),
            fg_color="transparent",
            text_color="#71717a",
            hover_color="#27272a",
            height=20,
            width=0,
            command=self.show_specs_page
        ).pack()

        ctk.CTkLabel(pnl, text="Developed by James Uzumaki", font=("Arial", 9), text_color="#52525b").pack()
        
        # Version label in bottom right corner
        self.version_label = ctk.CTkLabel(
            self.menu_frame,
            text=f"v{self.APP_VERSION}",
            font=("Arial", 10),
            text_color="#555",
            fg_color="transparent"
        )
        self.version_label.place(relx=0.99, rely=0.99, anchor="se")



    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.set_volume(0)
            if hasattr(self, 'btn_mute'):
                 if self.icon_mute: self.btn_mute.configure(image=self.icon_mute)
                 else: self.btn_mute.configure(text="🔇", fg_color="#550000")
        else:
            pygame.mixer.music.set_volume(self.music_volume)
            if hasattr(self, 'btn_mute'):
                 if self.icon_unmute: self.btn_mute.configure(image=self.icon_unmute)
                 else: self.btn_mute.configure(text="🔊", fg_color="#333")

    def show_specs_page(self):
        self.menu_frame.grid_remove()
        
        self.specs_frame = ctk.CTkFrame(self, fg_color="#101010")
        self.specs_frame.grid(row=0, column=0, sticky="nsew")
        self.specs_frame.grid_columnconfigure(0, weight=1)
        
        # Back Button
        ctk.CTkButton(self.specs_frame, text="< Back", width=80, command=self.back_to_main).place(x=20, y=20)
        
        # Content
        ctk.CTkLabel(self.specs_frame, text="SYSTEM REQUIREMENTS", font=("Impact", 32), text_color="gold").pack(pady=(50, 30))
        
        msg = ("MINIMUM REQUIREMENTS:\n\n"
               "- GPU: NVIDIA GTX 1050 or equivalent\n"
               "- CPU: Intel Core i5 8th Gen / Ryzen 5 2600\n"
               "- RAM: 8GB\n"
               "- Camera: 720p 30fps Webcam\n"
               "\n"
               "RECOMMENDED:\n\n"
               "- GPU: RTX 2060 or better (for smooth tracking)\n"
               "- CPU: i7 10th Gen / Ryzen 7 3700X\n"
               "- RAM: 16GB\n"
               "- Camera: 1080p 60fps Webcam")
               
        ctk.CTkLabel(self.specs_frame, text=msg, font=("Arial", 18), justify="left", text_color="#DDD").pack(padx=20, pady=10)

    def refresh_auth_ui(self):
        # Clear existing
        if hasattr(self, 'auth_frame'):
            for w in self.auth_frame.winfo_children(): w.destroy()
            
            if getattr(self, 'discord_user', None):
                # Logged In
                try:
                    avatar_url = f"https://cdn.discordapp.com/avatars/{self.discord_user['id']}/{self.discord_user['avatar']}.png"
                    response = requests.get(avatar_url, timeout=2)
                    pil_img = Image.open(BytesIO(response.content))
                    avatar_ctk = ctk.CTkImage(pil_img, size=(40, 40))
                    ctk.CTkLabel(self.auth_frame, text="", image=avatar_ctk).pack(side="left", padx=15)
                except:
                    ctk.CTkLabel(self.auth_frame, text="👤", font=("Arial", 24)).pack(side="left", padx=15)
                    
                ctk.CTkLabel(self.auth_frame, text=self.username, font=("Arial", 18, "bold"), text_color="white").pack(side="left", fill="x", expand=True)
                ctk.CTkButton(self.auth_frame, text="LOGOUT", width=60, height=25, fg_color="#ef4444", hover_color="#dc2626", 
                              command=self.logout_discord).pack(side="right", padx=10)
            else:
                # Guest
                ctk.CTkLabel(self.auth_frame, text="Guest", font=("Arial", 18, "bold"), text_color="gray").pack(side="left", padx=15)
                ctk.CTkButton(self.auth_frame, text="LOGIN WITH DISCORD", font=("Arial", 12, "bold"), height=30,
                              fg_color="#5865F2", hover_color="#4752C4",
                              command=self.handle_discord_login).pack(side="right", padx=10)

    def scan_cameras_async(self):
         threading.Thread(target=self.get_available_cameras, daemon=True).start()

    def resize_bg(self, event):
        if not hasattr(self, 'original_bg'): return
        
        # Small optimization: only resize if dimensions changed significantly to avoid lag during drag
        if hasattr(self, 'last_bg_size'):
            w, h = self.last_bg_size
            if abs(w - event.width) < 50 and abs(h - event.height) < 50:
                return
        
        self.last_bg_size = (event.width, event.height)
        
        try:
            from PIL import ImageOps
            # Scale and Crop to fill the new window size
            new_bg = ImageOps.fit(self.original_bg, (event.width, event.height), method=Image.Resampling.LANCZOS)
            self.bg_photo = ctk.CTkImage(new_bg, size=(event.width, event.height))
            self.bg_label.configure(image=self.bg_photo)
        except Exception:
            pass

    def on_camera_select(self, choice):
        if choice in self.camera_map:
            self.selected_camera_index = self.camera_map[choice]
        else:
            self.selected_camera_index = 0
        print(f"Selected Camera: {choice} (Index {self.selected_camera_index})")

    def launch_practice(self):
        # Instead of direct launch, show Practice Menu
        self.show_practice_menu()
        
    def show_practice_menu(self):
        # Hide LOGIN card, keep BG
        if hasattr(self, 'login_outer'):
             self.login_outer.place_forget()
        
        # Create Practice Card Wrapper
        self.practice_outer = ctk.CTkFrame(self.menu_frame, fg_color="transparent")
        self.practice_outer.place(relx=0.5, rely=0.5, anchor="center")
        
        # Card Border & Body (Reusing the style)
        self.practice_border = ctk.CTkFrame(self.practice_outer, fg_color="#2a2a2f", corner_radius=26)
        self.practice_border.pack()
        
        self.practice_inner = ctk.CTkFrame(self.practice_border, fg_color="#18181b", corner_radius=24)
        self.practice_inner.pack(padx=2, pady=2)
        
        # Content Padding
        pnl = ctk.CTkFrame(self.practice_inner, fg_color="transparent")
        pnl.pack(padx=50, pady=40, fill="both", expand=True)

        # Title
        ctk.CTkLabel(pnl, text="SELECT GAME MODE", font=("Impact", 42), text_color="#00EE00").pack(pady=(0, 10))
        
        # --- ANNOUNCEMENTS (if any) ---
        if self.announcements:
            latest = self.announcements[0]
            msg = latest.get("message", "")
            if msg:
                ctk.CTkLabel(pnl, text=f"📢 {msg}", font=("Arial", 12), 
                            text_color="#f59e0b", wraplength=350).pack(pady=(0, 5))
        
        # --- CUSTOM JUTSU COUNT (only if > 0) ---
        custom_count = self._count_custom_jutsus()
        if custom_count > 0:
            ctk.CTkLabel(pnl, text=f"💾 {custom_count} custom jutsu(s) on this device", 
                        font=("Arial", 11), text_color="#888").pack(pady=(0, 15))
        else:
            ctk.CTkLabel(pnl, text="", height=10).pack()  # Spacer

        # --- MODES ---
        btn_font = ("Arial", 20, "bold")
        
        # Free Play
        ctk.CTkButton(pnl, text="FREE PLAY", font=btn_font, width=300, height=60,
                      fg_color="#444", hover_color="#666",
                      command=lambda: self.start_game_with_user("practice")).pack(pady=10)
                      
        # Competitive (Requires Online)
        ctk.CTkButton(pnl, text="COMPETITIVE", font=btn_font, width=300, height=60,
                      fg_color="#D32F2F", hover_color="#B71C1C",
                      command=self.handle_competitive_click).pack(pady=10)

        # Multiplayer
        ctk.CTkButton(pnl, text="MULTIPLAYER (Locked)", font=btn_font, width=300, height=60,
                      fg_color="#222", text_color="#555",
                      state="disabled").pack(pady=10)
        
        # Settings
        ctk.CTkButton(pnl, text="SETTINGS", font=btn_font, width=300, height=60,
                      fg_color="#333", hover_color="#555",
                      command=self.show_settings_menu).pack(pady=10)
        
        # CREATE JUTSU (Always visible, but checks login)
        ctk.CTkButton(pnl, text="CREATE JUTSU (+)", font=("Arial", 16, "bold"), width=300, height=50,
                      fg_color="#3b82f6", hover_color="#2563eb",
                      command=self.handle_create_jutsu_click).pack(pady=10)

        # Leaderboard with Back Link
        link_frame = ctk.CTkFrame(pnl, fg_color="transparent")
        link_frame.pack(pady=20)
        
        ctk.CTkButton(link_frame, text="< Back", font=("Arial", 14), 
                      fg_color="transparent", text_color="gray", hover_color="#222", width=60,
                      command=self.back_to_main_from_practice).pack(side="left", padx=20)
                      
        ctk.CTkButton(link_frame, text="View Leaderboards", font=("Arial", 14), 
                      fg_color="transparent", text_color="gold", hover_color="#222", width=120,
                      command=self.handle_leaderboard_click).pack(side="left", padx=20)

    def back_to_main_from_practice(self):
        if hasattr(self, 'practice_outer'):
            self.practice_outer.destroy()
        # Restore Login Card
        if hasattr(self, 'login_outer'):
            self.login_outer.place(relx=0.5, rely=0.5, anchor="center")

    def show_settings_menu(self):
        if self.is_game_active:
             self.game_frame.grid_remove()
        else:
             if hasattr(self, 'practice_outer'):
                 self.practice_outer.place_forget()
             
        self.settings_frame = ctk.CTkFrame(self, fg_color="#101010")
        self.settings_frame.grid(row=0, column=0, sticky="nsew")
        self.settings_frame.grid_columnconfigure(0, weight=1)
        
        # Back
        ctk.CTkButton(self.settings_frame, text="< Back", width=80, 
                      command=self.close_settings_menu).place(x=20, y=20)
        
        ctk.CTkLabel(self.settings_frame, text="SETTINGS", font=("Impact", 42), text_color="white").pack(pady=(60, 30))
        
        # --- CAMERA ---
        ctk.CTkLabel(self.settings_frame, text="ACTIVE CAMERA", font=("Arial", 16, "bold")).pack(pady=(0, 10))
        self.camera_dropdown = ctk.CTkOptionMenu(
            self.settings_frame, 
            values=getattr(self, 'available_cameras', ["Scanning..."]),
            width=300,
            command=self.on_camera_select,
            fg_color="#333", button_color="#555"
        )
        self.camera_dropdown.pack(pady=(0, 40))
        # Set current
        current_cam = None
        for name, idx in self.camera_map.items():
            if idx == self.selected_camera_index:
                current_cam = name; break
        if current_cam: self.camera_dropdown.set(current_cam)

        # Music
        ctk.CTkLabel(self.settings_frame, text="MUSIC VOLUME", font=("Arial", 16, "bold")).pack(pady=(0, 10))
        mus_slider = ctk.CTkSlider(self.settings_frame, from_=0, to=1, number_of_steps=100, width=400, command=self.updated_music_vol)
        mus_slider.set(self.music_volume)
        mus_slider.pack(pady=(0, 40))
        
        # SFX
        ctk.CTkLabel(self.settings_frame, text="SFX VOLUME", font=("Arial", 16, "bold")).pack(pady=(0, 10))
        sfx_slider = ctk.CTkSlider(self.settings_frame, from_=0, to=1, number_of_steps=100, width=400, command=self.updated_sfx_vol)
        sfx_slider.set(getattr(self, 'sfx_volume', 0.5))
        sfx_slider.pack(pady=(0, 40))

    def close_settings_menu(self):
        self.settings_frame.destroy()
        if self.is_game_active:
            self.game_frame.grid()
        else:
            if hasattr(self, 'practice_outer'):
                self.practice_outer.place(relx=0.5, rely=0.5, anchor="center")

    def updated_music_vol(self, val):
        self.music_volume = val
        try: pygame.mixer.music.set_volume(val)
        except: pass

    def updated_sfx_vol(self, val):
        self.sfx_volume = val

    def handle_discord_login(self):
        # We need credentials. For now, try to load from env or prompt user?
        # Since this is a local app, putting secrets in code is bad practice if distributed, 
        # but for a personal project generated by AI, we can check .env or ask.
        
        env = {}
        try:
            # Quick parse of .env.local if available
            with open(os.path.join("web", ".env.local"), "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        env[k] = v.strip()
        except:
            pass
            
        client_id = env.get("DISCORD_CLIENT_ID")
        client_secret = env.get("DISCORD_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            print("[!] Missing Discord Credentials in web/.env.local")
            # For demo purposes, we can't proceed without them.
            ctk.CTkLabel(self.practice_frame, text="Missing API Keys!", text_color="red").pack()
            return

        from src.jutsu_academy.discord_auth import DiscordLogin
        auth = DiscordLogin(client_id, client_secret)
        
        # Run in thread to not freeze UI? 
        # But we need to open browser. threading is handled inside DiscordLogin for the server.
        # But the `login()` call blocks waiting for the event. So yes, run in thread.
        
        def run_auth():
            user = auth.login()
            if user:
                self.discord_user = user
                self.username = user['username']
                self.save_session() # Persist
                print(f"Logged in as {self.username}")
                # Update UI (Needs to be on main thread? Tkinter isn't thread safe)
                self.after(100, self.refresh_auth_ui)
        
        threading.Thread(target=run_auth, daemon=True).start()

    def logout_discord(self):
        self.clear_session()
        self.refresh_auth_ui()

    def back_to_main(self):
        if hasattr(self, 'practice_frame'):
            self.practice_frame.grid_remove()
        if hasattr(self, 'leaderboard_frame'):
            self.leaderboard_frame.grid_remove()
        if hasattr(self, 'specs_frame'):
            self.specs_frame.grid_remove()
        self.menu_frame.grid()
        
    def start_game_with_user(self, mode):
        # Use current state (set by Login or Default)
        if not self.username or self.username == "Ninja":
             self.username = "Guest"
             
        self.start_game(mode=mode, room_id=None)

    def handle_leaderboard_click(self):
        """Check online before showing leaderboards."""
        if not self.online:
            self.show_offline_popup("Leaderboards")
            return
        self.show_leaderboard()

    def show_leaderboard(self):
        # Hide Main Menu (since button is now there)
        self.menu_frame.grid_remove()
        
        self.leaderboard_frame = ctk.CTkFrame(self, fg_color="#101010")
        self.leaderboard_frame.grid(row=0, column=0, sticky="nsew")
        self.leaderboard_frame.grid_columnconfigure(0, weight=1)
        
        # Layout
        ctk.CTkButton(self.leaderboard_frame, text="< Back", width=80, command=self.back_to_main).place(x=20, y=20)
        ctk.CTkLabel(self.leaderboard_frame, text="HALL OF FAME", font=("Impact", 48), text_color="gold").pack(pady=(40, 10))
        
        # Jutsu Selector
        self.lbl_category = ctk.CTkLabel(self.leaderboard_frame, text="SELECT CATEGORY:", font=("Arial", 12), text_color="gray")
        self.lbl_category.pack(pady=(0, 5))
        
        jutsu_list = ["Fireball", "Chidori", "Water Dragon", "Shadow Clone", "Phoenix Flower", "Sharingan", "Rasengan"]
        self.combo_jutsu = ctk.CTkOptionMenu(
            self.leaderboard_frame, 
            values=jutsu_list,
            command=self.refresh_leaderboard_data
        )
        self.combo_jutsu.pack(pady=(0, 20))
        self.combo_jutsu.set("Fireball")
        
        # Table Header
        header = ctk.CTkFrame(self.leaderboard_frame, fg_color="#202020", corner_radius=5)
        header.pack(fill="x", padx=50, pady=5)
        
        # Use grid for header for alignment
        header.grid_columnconfigure(0, weight=1) # Rank
        header.grid_columnconfigure(1, weight=0) # Avatar
        header.grid_columnconfigure(2, weight=2) # Name
        header.grid_columnconfigure(3, weight=1) # Time
        header.grid_columnconfigure(4, weight=1) # Title
        
        ctk.CTkLabel(header, text="RANK", font=("Arial", 14, "bold"), text_color="white").grid(row=0, column=0, pady=10)
        ctk.CTkLabel(header, text="", width=40).grid(row=0, column=1, pady=10) # Avatar
        ctk.CTkLabel(header, text="NINJA", font=("Arial", 14, "bold"), text_color="white").grid(row=0, column=2, pady=10, sticky="w")
        ctk.CTkLabel(header, text="TIME", font=("Arial", 14, "bold"), text_color="white").grid(row=0, column=3, pady=10)
        ctk.CTkLabel(header, text="TITLE", font=("Arial", 14, "bold"), text_color="white").grid(row=0, column=4, pady=10)

        # Scrollable Area
        self.scroll_ranks = ctk.CTkScrollableFrame(self.leaderboard_frame, width=700, height=450, fg_color="transparent")
        self.scroll_ranks.pack(pady=5, padx=50, fill="both", expand=True)
        
        # Initial Load
        self.refresh_leaderboard_data("Fireball")

    def refresh_leaderboard_data(self, jutsu_name):
        # Clear existing
        for widget in self.scroll_ranks.winfo_children():
            widget.destroy()
            
        # Loading Indicator
        self.loading_lbl = ctk.CTkLabel(self.scroll_ranks, text="Loading Rankings...", font=("Arial", 16), text_color="gray")
        self.loading_lbl.pack(pady=50)
        
        def fetch_thread():
            nm = NetworkManager()
            rows = nm.get_leaderboard(limit=50, mode=jutsu_name.upper())
            self.after(0, lambda: self.render_leaderboard_rows(rows))
            
        threading.Thread(target=fetch_thread, daemon=True).start()

    def render_leaderboard_rows(self, rows):
        # Remove Loading
        if hasattr(self, 'loading_lbl'):
             self.loading_lbl.destroy()
             
        if not rows:
            ctk.CTkLabel(self.scroll_ranks, text="No records yet. Be the first!", font=("Arial", 16), text_color="gray").pack(pady=50)
            return

        for i, row in enumerate(rows):
            rank = i + 1
            
            # Rank Logic
            if rank == 1:
                title = "HOKAGE"
                color = "#FFD700" # Gold
                bg_color = "#332b00"
            elif rank <= 5:
                title = "JONIN"
                color = "#00EE00" # Green
                bg_color = "#003300"
            elif rank <= 15:
                title = "CHUNIN"
                color = "#3B8ED0" # Blue
                bg_color = "#001a33"
            else:
                title = "GENIN"
                color = "#888888" # Gray
                bg_color = "#1a1a1a"
                
            r_frame = ctk.CTkFrame(self.scroll_ranks, fg_color=bg_color, corner_radius=10)
            r_frame.pack(fill="x", pady=2)
            
            r_frame.grid_columnconfigure(0, weight=1) # Rank
            r_frame.grid_columnconfigure(1, weight=0) # Avatar
            r_frame.grid_columnconfigure(2, weight=2) # Name
            r_frame.grid_columnconfigure(3, weight=1) # Time
            r_frame.grid_columnconfigure(4, weight=1) # Title
            
            # Default Avatar logic
            # Avatar Logic
            avatar_img = None
            try:
                # 1. Try DB Avatar
                avatar_url = row.get('avatar_url')
                if avatar_url:
                     response = requests.get(avatar_url, timeout=2)
                     if response.status_code == 200:
                         img_data = BytesIO(response.content)
                         pil_img = Image.open(img_data)
                         avatar_img = ctk.CTkImage(pil_img, size=(30, 30))
                
                # 2. Fallback to Shadow
                if not avatar_img:
                    shadow_path = os.path.join("src", "pics", "shadow.jpg")
                    if os.path.exists(shadow_path):
                         pil_img = Image.open(shadow_path)
                         avatar_img = ctk.CTkImage(pil_img, size=(30, 30))
            except Exception as e:
                print(f"Avatar load error: {e}")
                avatar_img = None

            ctk.CTkLabel(r_frame, text=f"#{rank}", font=("Impact", 18), text_color=color).grid(row=0, column=0, pady=10)
            
            if avatar_img:
                 ctk.CTkLabel(r_frame, text="", image=avatar_img).grid(row=0, column=1, pady=10, padx=(0,5))
            else:
                 ctk.CTkLabel(r_frame, text="👤").grid(row=0, column=1, pady=10)

            ctk.CTkLabel(r_frame, text=row['username'], font=("Arial", 16, "bold"), text_color="white").grid(row=0, column=2, pady=10, sticky="w")
            ctk.CTkLabel(r_frame, text=f"{row['score_time']:.2f}s", font=("Arial", 16), text_color=color).grid(row=0, column=3, pady=10)
            ctk.CTkLabel(r_frame, text=title, font=("Arial", 12, "bold"), text_color=color).grid(row=0, column=4, pady=10)

    def back_to_practice(self):
        # Obsolete, redirect to main instead if called
        self.back_to_main()

    def launch_multiplayer_menu(self):
        dialog = ctk.CTkInputDialog(text="Enter Room ID to Join (or leave empty to Host):", title="Multiplayer")
        room_id = dialog.get_input()
        mode = "host" if not room_id else "join"
        self.start_game(mode="multiplayer", room_id=room_id)

    def start_game(self, mode, room_id=None):
        # 1. Hide Menus
        self.menu_frame.grid_remove()
        if hasattr(self, 'practice_frame'):
            self.practice_frame.grid_remove()
        
        self.loading_frame = ctk.CTkFrame(self, fg_color="black")
        self.loading_frame.grid(row=0, column=0, sticky="nsew")
        
        lbl_loading = ctk.CTkLabel(self.loading_frame, text="ENTERING DOJO...", font=("Impact", 32), text_color="white")
        lbl_loading.pack(pady=(250, 20))
        
        self.progress = ctk.CTkProgressBar(self.loading_frame, width=400, mode="indeterminate")
        self.progress.pack(pady=10)
        self.progress.start()
        
        self.lbl_status_load = ctk.CTkLabel(self.loading_frame, text="Loading AI Models...", font=("Arial", 14), text_color="gray")
        self.lbl_status_load.pack(pady=5)
        
        
        # 2. Initialize Game in Background Thread
        t = threading.Thread(target=self._init_game_session, args=(mode, room_id))
        t.daemon = True
        t.start()

    def _init_game_session(self, mode, room_id):
        try:
            # Simulate steps if needed or just run the heavy init
            # NOTE: Updating UI directly from thread is risky in Tkinter, but typically works for simple text
            # Ideally use a queue or after(), but for this quick feedback:
            self.lbl_status_load.configure(text="Initializing Neural Network...")
            
            # We can't easily hook into the constructor's progress without refactoring GameSession,
            # but we can try to update text before specific slow parts if we split them.
            # For now, just show that something is happening.
            
            self.current_session = GameSession(
                mode=mode, 
                room_id=room_id, 
                camera_index=self.selected_camera_index, 
                username=self.username,
                discord_user=getattr(self, 'discord_user', None)
            )
            
            self.lbl_status_load.configure(text="Connecting to Server...")
            # Initialization Done -> Switch to Game UI on Main Thread
            self.after(0, self._finalize_start_game)
        except Exception as e:
            print(f"Failed to start game: {e}")
            self.after(0, self.stop_game)
            
    def handle_space_bar(self, event):
        if self.current_session and self.is_game_active:
            if self.current_session.game_finished:
                 # Restart to Lobby
                 self.current_session.reset_to_lobby()
            else:
                self.current_session.start_challenge()

    def handle_esc(self, event):
        self.stop_game()
            
    def prev_jutsu(self):
        if self.current_session and self.is_game_active:
            # Practice mode: Allow change anytime when not doing a jutsu
            if self.current_session.mode == "practice":
                if not self.current_session.jutsu_active:
                    self.current_session.prev_jutsu()
                    self.update_jutsu_label()
            # Challenge mode: Only allow change if Waiting and NOT in countdown
            elif self.current_session.waiting_for_start and not self.current_session.countdown_start_time:
                self.current_session.prev_jutsu()
                self.update_jutsu_label()

    def next_jutsu(self):
        if self.current_session and self.is_game_active:
            # Practice mode: Allow change anytime when not doing a jutsu
            if self.current_session.mode == "practice":
                if not self.current_session.jutsu_active:
                    self.current_session.next_jutsu()
                    self.update_jutsu_label()
            # Challenge mode: Only allow change if Waiting and NOT in countdown
            elif self.current_session.waiting_for_start and not self.current_session.countdown_start_time:
                self.current_session.next_jutsu()
                self.update_jutsu_label()
            
    def update_jutsu_label(self):
        if self.current_session:
            name = self.current_session.get_current_jutsu_name()
            self.lbl_jutsu_name.configure(text=name)

    def _finalize_start_game(self):
        # Hide Loading, Show Game
        if hasattr(self, 'loading_frame'):
            self.loading_frame.grid_remove()
            
        self.game_frame.grid(row=0, column=0, sticky="nsew") # Explicit grid options
        self.game_frame.tkraise() # Ensure top z-order
        
        self.is_game_active = True
        self.update_jutsu_label() # Init label
        
        # Bind Keys
        # Bind Keys
        self.bind('<space>', self.handle_space_bar)
        self.bind('<Escape>', self.handle_esc)
        
        # Force Layout Update (Fixes "freeze until move" bug)
        self.update_idletasks()
        
        # Super-force geometry refresh
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"{w}x{h}")
        self.update()
        
        self.update_game_loop()

    def stop_game(self):
        self.is_game_active = False
        if self.current_session:
            self.current_session.cap.release()
            if self.current_session.network:
                self.current_session.network.close()
            self.current_session = None
            
        self.game_frame.grid_remove()
        if hasattr(self, 'loading_frame'):
            self.loading_frame.grid_remove()
            
        self.menu_frame.grid()

    def update_game_loop(self):
        if not self.is_game_active or not self.current_session:
            return

        # 1. Process 1 Frame
        frame = self.current_session.process_frame()
        
        if frame is None:
            self.stop_game()
            return

        # 2. Convert to Tkinter Image
        # BGR -> RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 3. Maintain Aspect Ratio (Fit within Window)
        win_w = self.game_frame.winfo_width()
        win_h = self.game_frame.winfo_height()
        
        if win_w > 1 and win_h > 1:
            pil_img = Image.fromarray(frame)
            
            # Calculate aspect ratio
            img_w, img_h = pil_img.size
            ratio = min(win_w / img_w, win_h / img_h)
            new_w = int(img_w * ratio)
            new_h = int(img_h * ratio)
            
            # Resize (High Quality)
            # Use LANCZOS (formerly ANTIALIAS) for high quality downscaling, or NEAREST for speed/pixel art look
            # Given user wants FPS, maybe bilinear/bicubic is balance. 
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
            
            # Create CTkImage (no scaling by CTk needed now)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
            self.game_label.configure(image=ctk_img)
            
        # 4. Update UI Visibility (Arrows for jutsu selection)
        if self.current_session:
            if self.current_session.mode == "practice":
                # Free Play: Always show arrows (can change jutsu anytime when not performing)
                if not self.current_session.jutsu_active:
                    self.btn_prev.place(relx=0.05, rely=0.5, anchor="center")
                    self.btn_next.place(relx=0.95, rely=0.5, anchor="center")
                    # Update jutsu label to show current move
                    self.update_jutsu_label()
                else:
                    self.btn_prev.place_forget()
                    self.btn_next.place_forget()
            elif self.current_session.mode == "challenge":
                # Challenge: Only show arrows during waiting phase
                show_arrows = (self.current_session.waiting_for_start and 
                               not self.current_session.countdown_start_time)
                
                if show_arrows:
                    self.btn_prev.place(relx=0.05, rely=0.5, anchor="center")
                    self.btn_next.place(relx=0.95, rely=0.5, anchor="center")
                else:
                    self.btn_prev.place_forget()
                    self.btn_next.place_forget()
        
        # 5. Schedule next update (Target ~60 FPS = 16ms)
        self.after(16, self.update_game_loop)
    
    def show_offline_popup(self, feature_name="This feature"):
        """Show popup when trying to use an online feature while offline."""
        popup = ctk.CTkToplevel(self)
        popup.title("Internet Required")
        popup.geometry("380x200")
        popup.attributes("-topmost", True)
        
        ctk.CTkLabel(popup, text="📡 No Internet Connection", font=("Impact", 22), text_color="#ef4444").pack(pady=15)
        ctk.CTkLabel(popup, text=f"{feature_name} requires an internet connection.\n\nPlease check your network and try again.", 
                     font=("Arial", 13), text_color="#ccc", wraplength=340).pack(pady=5)
        
        ctk.CTkButton(popup, text="OK", width=100, fg_color="#333", command=popup.destroy).pack(pady=15)
    
    def handle_competitive_click(self):
        """Check online before starting Competitive mode."""
        if not self.online:
            self.show_offline_popup("Competitive Mode")
            return
        self.start_game_with_user("challenge")
    
    def handle_create_jutsu_click(self):
        """Check login and online before allowing jutsu creation."""
        # Check online first
        if not self.online:
            self.show_offline_popup("Create Jutsu")
            return
            
        # Check login
        if getattr(self, 'discord_user', None):
            # Logged in - open the creator
            self.open_create_jutsu_dialog()
        else:
            # Guest - show sign in prompt
            popup = ctk.CTkToplevel(self)
            popup.title("Login Required")
            popup.geometry("350x180")
            popup.attributes("-topmost", True)
            
            ctk.CTkLabel(popup, text="🔒 Login Required", font=("Impact", 22), text_color="#f59e0b").pack(pady=15)
            ctk.CTkLabel(popup, text="You must sign in with Discord\nto create custom jutsus!", font=("Arial", 14), text_color="#ccc").pack(pady=5)
            
            ctk.CTkButton(popup, text="OK", width=100, fg_color="#333", command=popup.destroy).pack(pady=15)

    def open_create_jutsu_dialog(self):
        """Opens a modal to create a custom jutsu with sound, video, and tracking options."""
        from tkinter import filedialog
        import shutil
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Create New Jutsu")
        dialog.geometry("550x750")
        dialog.attributes("-topmost", True)
        
        # Scrollable container for all content
        scroll = ctk.CTkScrollableFrame(dialog, width=510, height=700)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Heading
        ctk.CTkLabel(scroll, text="🔥 Design Your Jutsu", font=("Impact", 28), text_color="#f59e0b").pack(pady=10)
        
        # Name Input
        ctk.CTkLabel(scroll, text="Jutsu Name:", font=("Arial", 14, "bold")).pack(pady=(10, 5))
        name_var = ctk.StringVar()
        entry_name = ctk.CTkEntry(scroll, textvariable=name_var, width=350, height=40, font=("Arial", 14))
        entry_name.pack(pady=5)
        
        # Sequence Tracker
        sequence = []
        lbl_sequence = ctk.CTkLabel(scroll, text="Sequence: (Empty)", font=("Arial", 14, "bold"), text_color="#f59e0b", wraplength=480)
        lbl_sequence.pack(pady=10)
        
        def update_seq_label():
            if not sequence:
                lbl_sequence.configure(text="Sequence: (Empty)")
            else:
                lbl_sequence.configure(text=f"Sequence: {' → '.join(sequence)}")
        
        def add_sign(sign):
            if len(sequence) >= 12:
                return # Max limit
            sequence.append(sign)
            update_seq_label()
            
        def clear_seq():
            sequence.clear()
            update_seq_label()
            
        # Sign Buttons Grid (With Picture Previews)
        ctk.CTkLabel(scroll, text="Hand Signs (click to add):", font=("Arial", 12), text_color="#888").pack()
        signs_frame = ctk.CTkFrame(scroll, fg_color="#1a1a1a", corner_radius=10)
        signs_frame.pack(pady=10, padx=10, fill="x")
        
        available_signs = ["tiger", "boar", "snake", "ram", "bird", "dragon", "dog", "rat", "horse", "monkey", "ox", "hare"]
        
        # Pre-load sign icons
        sign_icons = {}
        for sign in available_signs:
            try:
                icon_path = os.path.join("src", "pics", f"{sign}.png")
                if os.path.exists(icon_path):
                    pil_img = Image.open(icon_path).resize((40, 40))
                    sign_icons[sign] = ctk.CTkImage(pil_img, size=(40, 40))
                else:
                    sign_icons[sign] = None
            except:
                sign_icons[sign] = None
        
        row = 0
        col = 0
        for sign in available_signs:
            btn_frame = ctk.CTkFrame(signs_frame, fg_color="transparent")
            btn_frame.grid(row=row, column=col, padx=6, pady=6)
            
            if sign_icons.get(sign):
                btn = ctk.CTkButton(
                    btn_frame,
                    text="",
                    image=sign_icons[sign],
                    width=50, height=50,
                    fg_color="#333",
                    hover_color="#555",
                    command=lambda s=sign: add_sign(s)
                )
            else:
                btn = ctk.CTkButton(
                    btn_frame,
                    text=sign[:3].upper(),
                    width=50, height=50,
                    fg_color="#333",
                    hover_color="#555",
                    command=lambda s=sign: add_sign(s)
                )
            btn.pack()
            ctk.CTkLabel(btn_frame, text=sign.capitalize(), font=("Arial", 9), text_color="#666").pack()
            
            col += 1
            if col > 5:
                col = 0
                row += 1
                
        ctk.CTkButton(scroll, text="Clear Sequence", fg_color="#D32F2F", hover_color="#b91c1c", width=150, command=clear_seq).pack(pady=8)
        
        # === EFFECT TRACKING TARGET ===
        ctk.CTkLabel(scroll, text="━" * 50, text_color="#333").pack(pady=5)
        ctk.CTkLabel(scroll, text="Effect Tracking Target:", font=("Arial", 14, "bold")).pack(pady=(10, 5))
        ctk.CTkLabel(scroll, text="Where should the effect appear?", font=("Arial", 11), text_color="#888").pack()
        
        tracking_var = ctk.StringVar(value="hand")
        tracking_options = [
            ("🖐️ Hand (Palm)", "hand"),
            ("👄 Mouth", "mouth"),
            ("👁️ Eyes", "eyes"),
            ("🎯 Center Screen", "center")
        ]
        
        tracking_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        tracking_frame.pack(pady=10)
        
        for text, value in tracking_options:
            ctk.CTkRadioButton(
                tracking_frame, 
                text=text, 
                variable=tracking_var, 
                value=value,
                font=("Arial", 13),
                fg_color="#f59e0b",
                hover_color="#d97706"
            ).pack(anchor="w", pady=3)
        
        # === SOUND EFFECT UPLOAD ===
        ctk.CTkLabel(scroll, text="━" * 50, text_color="#333").pack(pady=5)
        ctk.CTkLabel(scroll, text="Sound Effect (Optional):", font=("Arial", 14, "bold")).pack(pady=(10, 5))
        
        sound_path_var = ctk.StringVar(value="")
        lbl_sound = ctk.CTkLabel(scroll, text="No sound selected", font=("Arial", 11), text_color="#666")
        lbl_sound.pack(pady=3)
        
        def browse_sound():
            path = filedialog.askopenfilename(
                title="Select Sound Effect",
                filetypes=[("Audio Files", "*.mp3 *.wav *.ogg"), ("All Files", "*.*")]
            )
            if path:
                sound_path_var.set(path)
                lbl_sound.configure(text=f"✓ {os.path.basename(path)}", text_color="#22c55e")
        
        ctk.CTkButton(scroll, text="📁 Browse Sound", fg_color="#333", hover_color="#555", width=180, command=browse_sound).pack(pady=5)
        
        # === VIDEO EFFECT UPLOAD ===
        ctk.CTkLabel(scroll, text="━" * 50, text_color="#333").pack(pady=5)
        ctk.CTkLabel(scroll, text="Video Effect (Optional):", font=("Arial", 14, "bold")).pack(pady=(10, 5))
        ctk.CTkLabel(scroll, text="Use MP4 with BLACK background for overlay effect", font=("Arial", 10), text_color="#888").pack()
        
        video_path_var = ctk.StringVar(value="")
        lbl_video = ctk.CTkLabel(scroll, text="No video selected", font=("Arial", 11), text_color="#666")
        lbl_video.pack(pady=3)
        
        def browse_video():
            path = filedialog.askopenfilename(
                title="Select Video Effect (Black Background)",
                filetypes=[("Video Files", "*.mp4 *.webm *.avi"), ("All Files", "*.*")]
            )
            if path:
                video_path_var.set(path)
                lbl_video.configure(text=f"✓ {os.path.basename(path)}", text_color="#22c55e")
        
        ctk.CTkButton(scroll, text="🎬 Browse Video", fg_color="#333", hover_color="#555", width=180, command=browse_video).pack(pady=5)
        
        # === FILE SIZE LIMITS ===
        MAX_SOUND_SIZE_MB = 5
        MAX_VIDEO_SIZE_MB = 20
        
        # === SAVE FUNCTION (Local Storage Only) ===
        def save_jutsu():
            name = name_var.get().strip()
            if not name:
                ctk.CTkLabel(scroll, text="⚠️ Name is required!", text_color="red").pack()
                return
            if not sequence:
                ctk.CTkLabel(scroll, text="⚠️ Sequence is required!", text_color="red").pack()
                return
            
            # Create local assets folder
            safe_name = name.lower().replace(" ", "_")
            assets_dir = os.path.join("src", "custom_assets", safe_name)
            os.makedirs(assets_dir, exist_ok=True)
            
            final_sound_path = None
            final_video_path = None
            
            try:
                # === COPY SOUND TO LOCAL STORAGE ===
                if sound_path_var.get():
                    src_sound = sound_path_var.get()
                    ext = os.path.splitext(src_sound)[1]
                    final_sound_path = os.path.join(assets_dir, f"sound{ext}")
                    shutil.copy2(src_sound, final_sound_path)
                    print(f"[+] Saved sound to: {final_sound_path}")
                
                # === COPY VIDEO TO LOCAL STORAGE ===
                if video_path_var.get():
                    src_video = video_path_var.get()
                    ext = os.path.splitext(src_video)[1]
                    final_video_path = os.path.join(assets_dir, f"video{ext}")
                    shutil.copy2(src_video, final_video_path)
                    print(f"[+] Saved video to: {final_video_path}")
                
                # Create Data Object (local paths only)
                new_jutsu = {
                    "sequence": sequence,
                    "display_text": f"{name.upper()}!!",
                    "sound_path": final_sound_path,
                    "video_path": final_video_path,
                    "effect": "custom",
                    "tracking_target": tracking_var.get()
                }
                
                # === LOCAL STORAGE ONLY ===
                custom_path = os.path.join("src", "custom_jutsus.dat")
                current_data = {}
                if os.path.exists(custom_path):
                    with open(custom_path, "rb") as f:
                         encoded = f.read()
                         current_data = json.loads(base64.b64decode(encoded).decode('utf-8'))
                
                current_data[name] = new_jutsu
                
                json_str = json.dumps(current_data)
                encoded_str = base64.b64encode(json_str.encode('utf-8'))
                
                with open(custom_path, "wb") as f:
                    f.write(encoded_str)
                    
                print(f"[+] Local Cache Updated: {name}")
                print(f"    Tracking: {tracking_var.get()}")
                print(f"    Sound: {final_sound_path}")
                print(f"    Video: {final_video_path}")
                
                dialog.destroy()
                
                # Show success message
                success = ctk.CTkToplevel(self)
                success.title("Success")
                success.geometry("320x150")
                success.attributes("-topmost", True)
                ctk.CTkLabel(success, text="✅ Jutsu Created!", font=("Impact", 24), text_color="#22c55e").pack(pady=15)
                ctk.CTkLabel(success, text=f"{name} is now available!", font=("Arial", 14)).pack()
                ctk.CTkButton(success, text="OK", width=100, command=success.destroy).pack(pady=10)
                
            except Exception as e:
                print(f"[!] Failed to save: {e}")
                import traceback
                traceback.print_exc()
                ctk.CTkLabel(scroll, text=f"⚠️ Error: {str(e)[:50]}", text_color="red").pack()
        
        # Save Button
        ctk.CTkLabel(scroll, text="━" * 50, text_color="#333").pack(pady=10)
        ctk.CTkButton(scroll, text="💾 SAVE JUTSU", fg_color="#22c55e", hover_color="#16a34a", height=50, font=("Arial", 16, "bold"), command=save_jutsu).pack(pady=15)


if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()
