import json
import secrets
import threading
import time
import urllib.request
import urllib.error
from collections import deque
from typing import Optional

class TrueRNGProvider:
    """
    Provides True Random Numbers (Quantum Entropy) from the ANU API.
    Maintains a local buffer via a background thread to avoid blocking.
    Gracefully degrades to pseudo-random numbers if offline or rate-limited.
    """
    
    API_URL = "https://qrng.anu.edu.au/API/jsonI.php?length={}&type=uint16"
    MAX_BUFFER_SIZE = 2048
    FETCH_CHUNK_SIZE = 1024
    MIN_BUFFER_THRESHOLD = 256

    def __init__(self):
        self._buffer: deque[float] = deque()
        self._lock = threading.Lock()
        self._is_fetching = False
        self._fetch_thread: Optional[threading.Thread] = None
        self._consecutive_failures = 0
        
        # Initial seed
        self._trigger_fetch_if_needed()

    def get_float(self) -> float:
        """
        Returns a float between 0.0 and 1.0 from true quantum entropy if available,
        falling back to cryptographic pseudorandomness if the buffer is empty.
        """
        self._trigger_fetch_if_needed()
        
        with self._lock:
            if self._buffer:
                return self._buffer.popleft()
                
        # Graceful fallback: Buffer is empty (e.g. offline, rate-limited)
        return self._generate_fallback()

    def _generate_fallback(self) -> float:
        """Generates a cryptographically secure pseudo-random float."""
        return secrets.randbelow(2**32) / (2**32)

    def _trigger_fetch_if_needed(self):
        """Spawns a background thread to fetch more entropy if below threshold."""
        with self._lock:
            if len(self._buffer) >= self.MIN_BUFFER_THRESHOLD:
                return
            if self._is_fetching:
                return
                
            # If we failed multiple times recently, implement exponential backoff
            if self._consecutive_failures > 0:
                # E.g., if we failed, wait a bit before trying again. 
                # For simplicity, let the background thread handle delays, but don't spawn if already fetching
                pass
                
            self._is_fetching = True

        self._fetch_thread = threading.Thread(target=self._fetch_entropy_worker, daemon=True)
        self._fetch_thread.start()

    def _fetch_entropy_worker(self):
        """Background worker to fetch entropy from the API."""
        try:
            url = self.API_URL.format(self.FETCH_CHUNK_SIZE)
            
            # Simple backoff if we've failed recently
            if self._consecutive_failures > 0:
                time.sleep(min(self._consecutive_failures * 2, 60))
                
            req = urllib.request.Request(url, headers={'User-Agent': 'VajraStream/1.0'})
            
            with urllib.request.urlopen(req, timeout=10.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    
                    if data.get("success") and "data" in data:
                        uint16_data = data["data"]
                        # Convert uint16 (0 to 65535) to float (0.0 to 1.0)
                        float_data = [x / 65535.0 for x in uint16_data]
                        
                        with self._lock:
                            # Append new entropy, respecting max size
                            for val in float_data:
                                if len(self._buffer) < self.MAX_BUFFER_SIZE:
                                    self._buffer.append(val)
                                    
                        self._consecutive_failures = 0
                        
        except Exception as e:
            # Silent fallback; the get_float() method will use secrets.
            self._consecutive_failures += 1
        finally:
            with self._lock:
                self._is_fetching = False

# Singleton instance
true_rng_provider = TrueRNGProvider()

def get_true_rng() -> TrueRNGProvider:
    return true_rng_provider
