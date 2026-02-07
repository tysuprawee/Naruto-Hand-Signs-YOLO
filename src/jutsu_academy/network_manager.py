from supabase import create_client, Client
from pathlib import Path
import json
import time
import os
import cv2
import threading

# Load env variables simple parser
def get_env():
    env = {}
    
    # 1. Try Loading from os.environ first (if loaded by dotenv elsewhere)
    for k, v in os.environ.items():
        env[k] = v
        
    # 2. Check for .env files in common locations
    root_dir = Path(__file__).parent.parent.parent
    possible_paths = [
        root_dir / ".env",
        root_dir / "web" / ".env.local",
        root_dir / ".env.local"
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"): continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            # Simple cleanup
                            k = k.strip() 
                            v = v.strip().strip('"').strip("'")
                            if k not in env: # Don't overwrite existing env vars
                                env[k] = v
            except:
                pass
                
    return env

class NetworkManager:
    def __init__(self):
        env = get_env()
        
        # Try different key variants
        self.url = env.get("SUPABASE_URL") or env.get("NEXT_PUBLIC_SUPABASE_URL", "")
        self.key = env.get("SUPABASE_KEY") or env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
        
        if not self.url or not self.key:
            print("[!] Supabase credentials missing (checked .env, web/.env.local)")
            self.client = None
        else:
            self.client: Client = create_client(self.url, self.key)
            
        self.room_id = None
        self.is_host = False
        self.last_state = {}
        self.msg_queue = []
        self.stop_thread = False

    def connect(self, room_id):
        if not self.client: return
        
        self.room_id = room_id if room_id else f"ROOM_{int(time.time())}"
        self.is_host = True if not room_id else False
        
        print(f"[*] Connected to Room: {self.room_id} (Role: {'HOST' if self.is_host else 'GUEST'})")
        
        # Start Polling Thread
        self.t = threading.Thread(target=self.poll_loop)
        self.t.start()

    def poll_loop(self):
        """Polls the match state file from storage every 1s"""
        while not self.stop_thread:
            try:
                # Attempt to download matches/id.json
                # Note: Using 'training_data' bucket for now as we know it exists
                # In production, create a 'matches' bucket
                try:
                    data = self.client.storage.from_("training_data").download(f"matches/{self.room_id}.json")
                    state = json.loads(data)
                    
                    # Check for updates
                    if state.get("timestamp", 0) > self.last_state.get("timestamp", 0):
                        # New update!
                        self.last_state = state
                        # Logic to see if it's a message for me
                        # If I am host, and turn is guest, and new state says turn is host -> I received pass
                        
                        if state.get("last_action") and state["last_action"] != self.last_state.get("last_action_id"):
                             self.msg_queue.append(state["payload"])
                    
                except Exception as e:
                    # File likely doesn't exist yet (new room)
                    if self.is_host and not self.last_state:
                        # Create it
                        self.send_state({"status": "waiting"})
                    pass
                    
            except Exception as e:
                print(f"[!] Network Error: {e}")
            
            time.sleep(1.0)

    def send_state(self, payload):
        """Write state to storage"""
        if not self.client: return
        
        state = {
            "room_id": self.room_id,
            "timestamp": time.time(),
            "turn": "host" if self.is_host else "guest", # Simplified
            "payload": payload,
            "last_action_id": str(time.time())
        }
        
        # Determine filename
        filename = f"matches/{self.room_id}.json"
        
        # json dump
        data = json.dumps(state).encode('utf-8')
        
        # Upload (Upsert)
        try:
            self.client.storage.from_("training_data").upload(
                filename, 
                data, 
                {"upsert": "true", "content-type": "application/json"}
            )
        except Exception as e:
            print(f"[!] Send Error: {e}")

    def send_attack(self, frame):
        # 1. Upload Image
        img_name = f"matches/{self.room_id}_{int(time.time())}.jpg"
        _, buf = cv2.imencode(".jpg", frame)
        try:
             self.client.storage.from_("training_data").upload(
                img_name,
                buf.tobytes(),
                {"content-type": "image/jpeg"}
             )
             img_url = self.client.storage.from_("training_data").get_public_url(img_name)
             
             # 2. Update State
             self.send_state({
                 "type": "attack",
                 "damage": 20,
                 "image": img_url
             })
             
        except Exception as e:
            print(f"Attack upload failed: {e}")

    def receive(self):
        if self.msg_queue:
            return self.msg_queue.pop(0)
        return None

    def close(self):
        self.stop_thread = True
        
    def join_room(self, room_id):
        # Improved connection logic
        # 1. Determine Host/Guest
        # For simple Storage-based matching:
        # If room_id is empty => Host a new random room
        # If room_id provided => Join (Guest)
        
        if not room_id:
            # HOST
            self.room_id = f"ROOM_{int(time.time())}"[-6:] # Short ID
            self.is_host = True
            role = "host"
        else:
            # GUEST
            self.room_id = room_id
            self.is_host = False
            role = "guest"
            
        print(f"[*] Connected to Room: {self.room_id} ({role})")
        # Start state polling
        self.t = threading.Thread(target=self.poll_loop)
        self.t.start()
        
        return role

    def get_leaderboard(self, limit=10, offset=0, mode="Fireball"):
        """Fetch top scores filtered by Jutsu (mode)"""
        if not self.client: return []
        try:
            # We filter by 'mode' column which now holds the Jutsu Name
            response = self.client.table('leaderboard')\
                .select('*')\
                .eq('mode', mode)\
                .order('score_time', desc=False)\
                .range(offset, offset + limit - 1)\
                .execute()
            return response.data
        except Exception as e:
            print(f"[!] Leaderboard fetch failed: {e}")
            return []

    def get_announcements(self, limit=10):
        """Fetch active announcements from app_config table"""
        if not self.client: return []
        try:
            response = self.client.table('app_config')\
                .select('*')\
                .eq('type', 'announcement')\
                .eq('is_active', True)\
                .order('priority', desc=True)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            return response.data
        except Exception as e:
            print(f"[!] Announcements fetch failed: {e}")
            return []

    def submit_score(self, username, score_time, mode="Fireball", discord_id=None, avatar_url=None):
        """Upload score to DB"""
        if not self.client: return
        try:
            data = {
                "username": username,
                "score_time": float(score_time),
                "mode": mode
            }
            if discord_id: data["discord_id"] = discord_id
            if avatar_url: data["avatar_url"] = avatar_url

            self.client.table('leaderboard').insert(data).execute()
            print(f"[+] Score submitted: {score_time}s by {username}")
        except Exception as e:
            print(f"[!] Score submission failed: {e}")

    def get_profile(self, username):
        """Fetch player profile/progression from DB"""
        if not self.client: return None
        try:
            response = self.client.table('profiles').select('*').eq('username', username).execute()
            if response.data:
                return response.data[0]
            return {} # Return empty dict for "User Not Found"
        except Exception as e:
            print(f"[!] Profile fetch failed: {e}")
        return None # Return None for "Error"

    def upsert_profile(self, data):
        """Update or Insert player progression"""
        if not self.client: return
        try:
            # We use username as the conflict target
            self.client.table('profiles').upsert(data, on_conflict='username').execute()
        except Exception as e:
            print(f"[!] Profile sync failed: {e}")

if __name__ == "__main__":
    nm = NetworkManager()
    print(f"URL: {nm.url}")
    print(f"Key Found: {'Yes' if nm.key else 'No'}")
    if nm.client:
        print("Client created successfully.")
        # Try fetch
        print("Fetching leaderboard...")
        print(nm.get_leaderboard(limit=1))
    else:
        print("Client failed.")
