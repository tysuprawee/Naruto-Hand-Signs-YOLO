import customtkinter as ctk
import sys
import os
import cv2
import threading
from PIL import Image
import numpy as np

try:
    from pygrabber.dshow_graph import FilterGraph
    import comtypes
except ImportError:
    FilterGraph = None

# Add parent directory to path to allow imports from src
# Add parent directory to path to allow imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.jutsu_academy.game_engine import GameSession, NetworkManager

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Jutsu Academy v1.01")
        self.geometry("1024x768")
        
        # State
        self.current_session = None
        self.is_game_active = False
        self.selected_camera_index = 0
        self.username = "Ninja" # Default user
        self.camera_map = {}

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
        
        # Overlay Button to Exit Game
        self.btn_exit_game = ctk.CTkButton(
            self.game_frame, 
            text="EXIT TO MENU", 
            command=self.stop_game,
            fg_color="red", 
            width=120, height=30
        )
        self.btn_exit_game.place(x=20, y=20)
        
        # In-Game Camera Dropdown
        self.ingame_camera_dropdown = ctk.CTkOptionMenu(
            self.game_frame,
            values=["Camera..."],
            width=200,
            command=self.on_ingame_camera_select,
            fg_color="#404040",
            button_color="#505050"
        )
        self.ingame_camera_dropdown.place(x=150, y=20)
        
        # --- GAME CONTROLS OVERLAY ---
        # Jutsu Name
        self.lbl_jutsu_name = ctk.CTkLabel(
            self.game_frame,
            text="",
            font=("Impact", 24),
            text_color="#00EE00",
            fg_color="#202020",
            corner_radius=10,
            width=200, height=40
        )
        self.lbl_jutsu_name.place(relx=0.5, y=40, anchor="center")

        # ... (Prev/Next Buttons remain) ...
        self.btn_prev = ctk.CTkButton(
            self.game_frame,
            text="<",
            font=("Arial", 20, "bold"),
            width=50, height=50,
            corner_radius=25,
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
            corner_radius=25,
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
        # Update Menu Dropdown
        self.camera_dropdown.configure(values=cameras)
        # Update In-Game Dropdown
        self.ingame_camera_dropdown.configure(values=cameras)
        
        if cameras:
            default = cameras[0]
            self.camera_dropdown.set(default)
            self.ingame_camera_dropdown.set(default)
            self.on_camera_select(default)
            
        self.camera_dropdown.configure(state="normal")
        self.ingame_camera_dropdown.configure(state="normal")
        
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

    def setup_menu(self):
        # Menu Layout - Center Everything
        self.menu_frame.grid_columnconfigure(0, weight=1)
        self.menu_frame.grid_rowconfigure(0, weight=1) # Spacer
        self.menu_frame.grid_rowconfigure(1, weight=0) # Content
        self.menu_frame.grid_rowconfigure(2, weight=1) # Spacer

        # Content Frame (Centered)
        content_frame = ctk.CTkFrame(self.menu_frame, fg_color="transparent")
        content_frame.grid(row=1, column=0)
        
        # Header
        lbl_title = ctk.CTkLabel(
            content_frame, 
            text="JUTSU ACADEMY", 
            font=("Impact", 64),
            text_color="#00EE00"
        )
        lbl_title.pack(pady=(0, 40))
        
        # Camera Selection
        lbl_cam = ctk.CTkLabel(content_frame, text="SELECT CAMERA:", font=("Arial", 12), text_color="gray")
        lbl_cam.pack(pady=(0, 5))
        
        self.camera_dropdown = ctk.CTkOptionMenu(
            content_frame, 
            values=["Scanning Cameras..."],
            width=300,
            command=self.on_camera_select,
            state="disabled"
        )
        self.camera_dropdown.pack(pady=(0, 20))
        
        # Buttons
        ctk.CTkButton(content_frame, text="PRACTICE MODE", font=("Arial", 20, "bold"), width=350, height=60, corner_radius=30,
                      command=self.launch_practice).pack(pady=10)
                      
        ctk.CTkButton(content_frame, text="MULTIPLAYER (COMING SOON)", font=("Arial", 20, "bold"), width=350, height=60, corner_radius=30,
                      fg_color="#333333", state="disabled").pack(pady=10)
                      
        ctk.CTkButton(content_frame, text="VIEW LEADERBOARD", font=("Arial", 20, "bold"), width=350, height=60, corner_radius=30,
                      fg_color="#3B8ED0", hover_color="#36719F",
                      command=self.show_leaderboard).pack(pady=10)
                      
        ctk.CTkButton(content_frame, text="EXIT", font=("Arial", 16), width=200, height=40, fg_color="transparent", border_width=2,
                      command=self.destroy).pack(pady=30)
                      
        # Footer Info
        footer_frame = ctk.CTkFrame(self.menu_frame, fg_color="transparent")
        footer_frame.grid(row=2, column=0, sticky="s", pady=20)
        
        ctk.CTkLabel(footer_frame, text="Developed by Ty Suprawee", font=("Arial", 12), text_color="#666").pack()
        ctk.CTkLabel(footer_frame, text="Specs: Webcam Required | GPU Recommended", font=("Arial", 10), text_color="#444").pack()
                      
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
        self.menu_frame.grid_remove()
        
        # Create Practice Menu Frame
        self.practice_frame = ctk.CTkFrame(self, fg_color="#101010")
        self.practice_frame.grid(row=0, column=0, sticky="nsew")
        self.practice_frame.grid_columnconfigure(0, weight=1)
        
        # Back Button
        ctk.CTkButton(self.practice_frame, text="< Back", width=80, command=self.back_to_main).place(x=20, y=20)
        
        # Title
        ctk.CTkLabel(self.practice_frame, text="PRACTICE MODE", font=("Impact", 48), text_color="#00EE00").pack(pady=(50, 20))
        
        # Username Input
        ctk.CTkLabel(self.practice_frame, text="NINJA NAME:", font=("Arial", 14), text_color="gray").pack(pady=(0,5))
        self.entry_username = ctk.CTkEntry(self.practice_frame, width=200, justify="center")
        self.entry_username.pack(pady=(0, 20))
        self.entry_username.insert(0, "Ninja")
        
        # Buttons
        ctk.CTkButton(self.practice_frame, text="FREE PLAY", font=("Arial", 20, "bold"), width=300, height=50,
                      fg_color="#444", hover_color="#666",
                      command=lambda: self.start_game_with_user("practice")).pack(pady=10)
                      
        ctk.CTkButton(self.practice_frame, text="TIME ATTACK (Leaderboard)", font=("Arial", 20, "bold"), width=300, height=50,
                      fg_color="#D32F2F", hover_color="#B71C1C",
                      command=lambda: self.start_game_with_user("challenge")).pack(pady=10)

    def back_to_main(self):
        if hasattr(self, 'practice_frame'):
            self.practice_frame.grid_remove()
        if hasattr(self, 'leaderboard_frame'):
            self.leaderboard_frame.grid_remove()
        self.menu_frame.grid()
        
    def start_game_with_user(self, mode):
        username = self.entry_username.get()
        if not username.strip(): username = "Ninja"
        self.username = username # Save globally if needed
        self.start_game(mode=mode, room_id=None)

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
        header.grid_columnconfigure(1, weight=2) # Name
        header.grid_columnconfigure(2, weight=1) # Time
        header.grid_columnconfigure(3, weight=1) # Title
        
        ctk.CTkLabel(header, text="RANK", font=("Arial", 14, "bold"), text_color="white").grid(row=0, column=0, pady=10)
        ctk.CTkLabel(header, text="NINJA", font=("Arial", 14, "bold"), text_color="white").grid(row=0, column=1, pady=10)
        ctk.CTkLabel(header, text="TIME", font=("Arial", 14, "bold"), text_color="white").grid(row=0, column=2, pady=10)
        ctk.CTkLabel(header, text="TITLE", font=("Arial", 14, "bold"), text_color="white").grid(row=0, column=3, pady=10)

        # Scrollable Area
        self.scroll_ranks = ctk.CTkScrollableFrame(self.leaderboard_frame, width=700, height=450, fg_color="transparent")
        self.scroll_ranks.pack(pady=5, padx=50, fill="both", expand=True)
        
        # Initial Load
        self.refresh_leaderboard_data("Fireball")

    def refresh_leaderboard_data(self, jutsu_name):
        # Clear existing
        for widget in self.scroll_ranks.winfo_children():
            widget.destroy()
            
        nm = NetworkManager()
        rows = nm.get_leaderboard(limit=50, mode=jutsu_name)
        
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
            
            r_frame.grid_columnconfigure(0, weight=1)
            r_frame.grid_columnconfigure(1, weight=2)
            r_frame.grid_columnconfigure(2, weight=1)
            r_frame.grid_columnconfigure(3, weight=1)
            
            ctk.CTkLabel(r_frame, text=f"#{rank}", font=("Impact", 18), text_color=color).grid(row=0, column=0, pady=10)
            ctk.CTkLabel(r_frame, text=row['username'], font=("Arial", 16, "bold"), text_color="white").grid(row=0, column=1, pady=10)
            ctk.CTkLabel(r_frame, text=f"{row['score_time']:.2f}s", font=("Arial", 16), text_color=color).grid(row=0, column=2, pady=10)
            ctk.CTkLabel(r_frame, text=title, font=("Arial", 12, "bold"), text_color=color).grid(row=0, column=3, pady=10)

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
            
            self.current_session = GameSession(mode=mode, room_id=room_id, camera_index=self.selected_camera_index, username=self.username)
            
            self.lbl_status_load.configure(text="Connecting to Server...")
            # Initialization Done -> Switch to Game UI on Main Thread
            self.after(0, self._finalize_start_game)
        except Exception as e:
            print(f"Failed to start game: {e}")
            self.after(0, self.stop_game)
            
    def handle_space_bar(self, event):
        if self.current_session and self.is_game_active:
            self.current_session.start_challenge()
            
    def prev_jutsu(self):
        if self.current_session and self.is_game_active:
            self.current_session.prev_jutsu()
            self.update_jutsu_label()

    def next_jutsu(self):
        if self.current_session and self.is_game_active:
            self.current_session.next_jutsu()
            self.update_jutsu_label()
            
    def update_jutsu_label(self):
        if self.current_session:
            name = self.current_session.get_current_jutsu_name()
            self.lbl_jutsu_name.configure(text=name)

    def _finalize_start_game(self):
        # Hide Loading, Show Game
        self.loading_frame.grid_remove()
        self.game_frame.grid()
        self.game_frame.tkraise() # Ensure top z-order
        
        self.is_game_active = True
        self.update_jutsu_label() # Init label
        
        # Bind Keys
        self.bind('<space>', self.handle_space_bar)
        
        # Force Layout Update (Fixes "freeze until move" bug)
        self.update_idletasks()
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
        
        # 4. Schedule next update (Target ~60 FPS = 16ms)
        self.after(16, self.update_game_loop)

if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()
