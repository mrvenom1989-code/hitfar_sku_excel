import os
import time
import httpx
from dotenv import load_dotenv
from supabase import create_client, Client

# Patch httpx.Client.send to handle transient connection resets/RemoteProtocolErrors
original_send = httpx.Client.send

def patched_send(self, request, *args, **kwargs):
    max_retries = 3
    delay = 0.5
    for attempt in range(max_retries):
        try:
            return original_send(self, request, *args, **kwargs)
        except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.ConnectTimeout) as e:
            if attempt == max_retries - 1:
                raise e
            print(f"[RETRY] httpx request to {request.url} failed: {e}. Retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(delay)
            delay *= 2
        except Exception as e:
            if "RemoteProtocolError" in type(e).__name__ or "Server disconnected" in str(e):
                if attempt == max_retries - 1:
                    raise e
                print(f"[RETRY] httpx request to {request.url} failed (RemoteProtocolError): {e}. Retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(delay)
                delay *= 2
            else:
                raise e

httpx.Client.send = patched_send

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") # Service Role Key
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-hitfar-sku-secret-key")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[CONFIG] Failed to initialize Supabase client: {e}")
