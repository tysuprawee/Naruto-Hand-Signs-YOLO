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
    env_path = Path(__file__).parent.parent.parent / "web" / ".env.local"
    try:
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    env[k] = v.strip('"')
    except:
        pass
    return env

class NetworkManager:
    def __init__(self):
        env = get_env()
        self.url = env.get("NEXT_PUBLIC_SUPABASE_URL", "")
        self.key = env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
        
        if not self.url or not self.key:
            print("[!] Supabase credentials missing in .env.local")
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

    def get_leaderboard(self, limit=50, mode="Fireball"):
        """Fetch top scores filtered by Jutsu (mode)"""
        if not self.client: return []
        try:
            # We filter by 'mode' column which now holds the Jutsu Name
            response = self.client.table('leaderboard')\
                .select('*')\
                .eq('mode', mode)\
                .order('score_time', desc=False)\
                .limit(limit)\
                .execute()
            return response.data
        except Exception as e:
            print(f"[!] Leaderboard fetch failed: {e}")
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
