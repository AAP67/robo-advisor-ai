"""
RoboAdvisor AI — Supabase Client
Thin wrapper to initialize the Supabase connection.
"""

import os
from supabase import create_client, Client


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise EnvironmentError(
            "Missing SUPABASE_URL or SUPABASE_ANON_KEY. "
            "Set them in your .env file."
        )
    
    return create_client(url, key)
