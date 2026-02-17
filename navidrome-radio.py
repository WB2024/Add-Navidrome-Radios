#!/usr/bin/env python3
"""
Navidrome Radio Station Manager
A CLI tool to search, browse, and add radio stations from Radio-Browser API
"""

import sqlite3
import requests
import json
import sys
from datetime import datetime
import hashlib
import base64
from typing import List, Dict, Optional

# ============================================================================
# CONFIGURATION - Hard-coded paths (can be overridden via command line)
# ============================================================================
DEFAULT_DB_PATH = "/srv/dev-disk-by-uuid-dc4918d5-6597-465b-9567-ce442fbd8e2a/DockerAppData/navidromeclean/navidrome.db"
RADIO_BROWSER_API = "https://de1.api.radio-browser.info/json"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_id(name: str) -> str:
    """Generate a unique ID similar to Navidrome's format"""
    unique_string = f"{name}{datetime.utcnow().isoformat()}"
    hash_obj = hashlib.md5(unique_string.encode())
    return base64.b64encode(hash_obj.digest()).decode('utf-8').rstrip('=').replace('+', '-').replace('/', '_')[:22]

def get_timestamp() -> str:
    """Get current UTC timestamp in Navidrome format"""
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + '+00:00'

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def check_station_exists(cursor, name: str, url: str) -> bool:
    """Check if a station already exists in the database"""
    cursor.execute("SELECT id FROM radio WHERE name = ? OR stream_url = ?", (name, url))
    return cursor.fetchone() is not None

def add_station_to_db(db_path: str, station: Dict) -> bool:
    """Add a single station to the database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        name = station['name']
        stream_url = station['url']
        home_page_url = station.get('homepage', '')
        
        if check_station_exists(cursor, name, stream_url):
            conn.close()
            return False
        
        station_id = generate_id(name)
        timestamp = get_timestamp()
        
        cursor.execute("""
            INSERT INTO radio (id, name, stream_url, home_page_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (station_id, name, stream_url, home_page_url, timestamp, timestamp))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error adding station: {e}")
        return False

def list_existing_stations(db_path: str):
    """List all existing stations in the database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, stream_url FROM radio ORDER BY name")
        stations = cursor.fetchall()
        conn.close()
        
        if not stations:
            print("\n📻 No radio stations found in database.\n")
            return
        
        print("\n" + "="*80)
        print("📻 CURRENT RADIO STATIONS IN NAVIDROME")
        print("="*80)
        for idx, (name, url) in enumerate(stations, 1):
            print(f"{idx:3d}. {name}")
            print(f"     URL: {url[:70]}{'...' if len(url) > 70 else ''}")
        print("="*80 + "\n")
    except Exception as e:
        print(f"❌ Error reading database: {e}")

# ============================================================================
# RADIO BROWSER API FUNCTIONS
# ============================================================================

def search_stations(query: str, search_type: str = "byname") -> List[Dict]:
    """
    Search for stations on Radio-Browser
    search_type: byname, bytag, bycountry, bylanguage, bystate
    """
    try:
        url = f"{RADIO_BROWSER_API}/stations/{search_type}/{query}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error searching Radio-Browser: {e}")
        return []

def get_top_stations(limit: int = 50) -> List[Dict]:
    """Get top voted stations"""
    try:
        url = f"{RADIO_BROWSER_API}/stations/topvote/{limit}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching top stations: {e}")
        return []

def get_stations_by_tag(tag: str) -> List[Dict]:
    """Get stations by tag/genre"""
    return search_stations(tag, "bytag")

def get_stations_by_country(country: str) -> List[Dict]:
    """Get stations by country"""
    return search_stations(country, "bycountry")

# ============================================================================
# UI FUNCTIONS
# ============================================================================

def clear_screen():
    """Clear the terminal screen"""
    import os
    os.system('clear' if os.name != 'nt' else 'cls')

def print_header():
    """Print application header"""
    clear_screen()
    print("\n" + "="*80)
    print("🎵  NAVIDROME RADIO STATION MANAGER  🎵")
    print("="*80 + "\n")

def display_stations(stations: List[Dict], selected: set = None):
    """Display a list of stations with optional selection markers"""
    if not stations:
        print("No stations found.")
        return
    
    selected = selected or set()
    
    print("\n" + "-"*80)
    for idx, station in enumerate(stations, 1):
        marker = "✓" if idx in selected else " "
        name = station.get('name', 'Unknown')
        country = station.get('country', 'Unknown')
        tags = station.get('tags', '')
        bitrate = station.get('bitrate', 'N/A')
        votes = station.get('votes', 0)
        
        print(f"[{marker}] {idx:3d}. {name[:50]:<50}")
        print(f"         Country: {country:<15} Tags: {tags[:30]}")
        print(f"         Bitrate: {bitrate} kbps | Votes: {votes}")
        print(f"         URL: {station.get('url', '')[:70]}")
        print("-"*80)

def display_page_stations(stations: List[Dict], start_idx: int, selected: set = None):
    """Display a page of stations with global indexing"""
    if not stations:
        print("No stations found.")
        return
    
    selected = selected or set()
    
    print("\n" + "-"*80)
    for page_idx, station in enumerate(stations, 1):
        global_idx = start_idx + page_idx  # Global index
        marker = "✓" if global_idx in selected else " "
        name = station.get('name', 'Unknown')
        country = station.get('country', 'Unknown')
        tags = station.get('tags', '')
        bitrate = station.get('bitrate', 'N/A')
        votes = station.get('votes', 0)
        
        print(f"[{marker}] {global_idx:3d}. {name[:50]:<50} (Page #{page_idx})")
        print(f"         Country: {country:<15} Tags: {tags[:30]}")
        print(f"         Bitrate: {bitrate} kbps | Votes: {votes}")
        print(f"         URL: {station.get('url', '')[:70]}")
        print("-"*80)

def get_user_choice(prompt: str, valid_range: Optional[range] = None) -> str:
    """Get user input with optional validation"""
    while True:
        choice = input(f"\n{prompt}: ").strip()
        if not valid_range:
            return choice
        
        if choice.isdigit() and int(choice) in valid_range:
            return choice
        
        print(f"❌ Please enter a number between {valid_range.start} and {valid_range.stop - 1}")

# ============================================================================
# MAIN MENU FUNCTIONS
# ============================================================================

def search_menu(db_path: str):
    """Search and select stations"""
    print_header()
    print("🔍 SEARCH RADIO STATIONS\n")
    print("1. Search by name")
    print("2. Search by genre/tag")
    print("3. Search by country")
    print("4. Browse top voted stations")
    print("5. Back to main menu")
    
    choice = get_user_choice("Select option", range(1, 6))
    
    stations = []
    
    if choice == "1":
        query = input("\nEnter station name: ").strip()
        if query:
            print(f"\n🔍 Searching for '{query}'...")
            stations = search_stations(query, "byname")
    
    elif choice == "2":
        query = input("\nEnter genre/tag (e.g., jazz, rock, classical): ").strip()
        if query:
            print(f"\n🔍 Searching for genre '{query}'...")
            stations = get_stations_by_tag(query)
    
    elif choice == "3":
        query = input("\nEnter country (e.g., USA, UK, Germany): ").strip()
        if query:
            print(f"\n🔍 Searching for country '{query}'...")
            stations = get_stations_by_country(query)
    
    elif choice == "4":
        print("\n🔍 Fetching top voted stations...")
        stations = get_top_stations(50)
    
    elif choice == "5":
        return
    
    if not stations:
        print("\n❌ No stations found!")
        input("\nPress Enter to continue...")
        return
    
    print(f"\n✅ Found {len(stations)} stations!")
    input("\nPress Enter to browse results...")
    select_and_add_stations(stations, db_path)

def select_and_add_stations(stations: List[Dict], db_path: str):
    """Allow user to select multiple stations and add them with pagination"""
    selected = set()
    page = 0
    items_per_page = 10
    total_pages = (len(stations) - 1) // items_per_page + 1
    
    while True:
        print_header()
        
        # Calculate pagination
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(stations))
        page_stations = stations[start_idx:end_idx]
        
        print(f"📻 FOUND {len(stations)} STATIONS - SELECT TO ADD")
        print(f"Page {page + 1} of {total_pages} (Showing {start_idx + 1}-{end_idx} of {len(stations)})")
        print(f"Selected: {len(selected)} station(s)\n")
        
        # Display current page with global indexing
        display_page_stations(page_stations, start_idx, selected)
        
        print("\nCommands:")
        print("  [number]     - Toggle selection (global number)")
        print("  [n1-n2]      - Select range on current page")
        print("  n/next       - Next page")
        print("  p/prev       - Previous page")
        print("  page [n]     - Go to specific page")
        print("  all          - Select all on current page")
        print("  none         - Deselect all")
        print("  add          - Add selected stations to Navidrome")
        print("  back         - Back to search menu")
        
        choice = input("\nEnter command: ").strip().lower()
        
        if choice == "back":
            return
        
        elif choice in ["n", "next"]:
            if page < total_pages - 1:
                page += 1
            else:
                print("❌ Already on last page!")
                input("Press Enter to continue...")
        
        elif choice in ["p", "prev"]:
            if page > 0:
                page -= 1
            else:
                print("❌ Already on first page!")
                input("Press Enter to continue...")
        
        elif choice.startswith("page "):
            try:
                target_page = int(choice.split()[1]) - 1
                if 0 <= target_page < total_pages:
                    page = target_page
                else:
                    print(f"❌ Page must be between 1 and {total_pages}")
                    input("Press Enter to continue...")
            except:
                print("❌ Invalid page number!")
                input("Press Enter to continue...")
        
        elif choice == "all":
            # Select all on current page
            for i in range(start_idx + 1, end_idx + 1):
                selected.add(i)
        
        elif choice == "none":
            selected.clear()
        
        elif choice == "add":
            if not selected:
                print("\n❌ No stations selected!")
                input("\nPress Enter to continue...")
                continue
            
            add_selected_stations(stations, selected, db_path)
            return
        
        elif "-" in choice:
            try:
                start, end = choice.split("-")
                start, end = int(start.strip()), int(end.strip())
                # Adjust to current page
                if 1 <= start <= items_per_page and 1 <= end <= items_per_page:
                    global_start = start_idx + start
                    global_end = start_idx + end
                    if global_end <= end_idx:
                        selected.update(range(global_start, global_end + 1))
                    else:
                        print("❌ Range exceeds current page!")
                        input("Press Enter to continue...")
                else:
                    print(f"❌ Range must be between 1 and {min(items_per_page, len(page_stations))} for current page")
                    input("Press Enter to continue...")
            except:
                print("❌ Invalid range format! Use: 1-5")
                input("Press Enter to continue...")
        
        elif choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(stations):
                if num in selected:
                    selected.remove(num)
                else:
                    selected.add(num)
            else:
                print(f"❌ Please enter a number between 1 and {len(stations)}")
                input("Press Enter to continue...")

def add_selected_stations(stations: List[Dict], selected: set, db_path: str):
    """Add the selected stations to the database"""
    print_header()
    print(f"💾 ADDING {len(selected)} STATIONS TO NAVIDROME\n")
    
    added = 0
    skipped = 0
    
    for idx in sorted(selected):
        station = stations[idx - 1]
        name = station.get('name', 'Unknown')
        
        if add_station_to_db(db_path, station):
            print(f"✅ Added: {name}")
            added += 1
        else:
            print(f"⏭️  Skipped (already exists): {name}")
            skipped += 1
    
    print(f"\n{'='*80}")
    print(f"📊 SUMMARY: {added} added, {skipped} skipped")
    print(f"{'='*80}")
    print("\n💡 Refresh your Navidrome web interface to see the new stations!")
    input("\nPress Enter to continue...")

def main_menu(db_path: str):
    """Main application menu"""
    while True:
        print_header()
        print("MAIN MENU\n")
        print("1. Search and add radio stations")
        print("2. View existing stations in database")
        print("3. Exit")
        
        choice = get_user_choice("Select option", range(1, 4))
        
        if choice == "1":
            search_menu(db_path)
        
        elif choice == "2":
            print_header()
            list_existing_stations(db_path)
            input("\nPress Enter to continue...")
        
        elif choice == "3":
            print("\n👋 Thanks for using Navidrome Radio Station Manager!\n")
            sys.exit(0)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main application entry point"""
    db_path = DEFAULT_DB_PATH
    
    # Check for command line override
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("\nNavidrome Radio Station Manager")
            print("="*50)
            print("\nUsage:")
            print("  navidrome-radio               - Use default database path")
            print("  navidrome-radio <db_path>     - Use custom database path")
            print(f"\nDefault database path:")
            print(f"  {DEFAULT_DB_PATH}")
            print()
            sys.exit(0)
        else:
            db_path = sys.argv[1]
    
    # Verify database exists
    import os
    if not os.path.exists(db_path):
        print(f"\n❌ Error: Database not found at: {db_path}")
        print("\nPlease check the path or provide a custom path:")
        print(f"  {sys.argv[0]} /path/to/navidrome.db\n")
        sys.exit(1)
    
    # Start the application
    try:
        main_menu(db_path)
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
