import json
from truthbrush.api import Api
import logging
from datetime import datetime, timezone  # <-- Import timezone

# --- CONFIGURATION ---
USERS_FILE = "users.txt"
OUTPUT_FILE = "all_users_data.jsonl"
# *** THIS IS THE FIX ***
# Add timezone information to the datetime objects
CREATED_AFTER_DATE = datetime(2025, 8, 1, tzinfo=timezone.utc)
CREATED_BEFORE_DATE = datetime(2025, 8, 10, tzinfo=timezone.utc)
# --- END CONFIGURATION ---

def main():
    """
    Logs in to Truth Social once, then scrapes all users from users.txt
    sequentially using the same authenticated session.
    """
    # Set up logging to be less noisy
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger("truthbrush.api")
    logger.setLevel(logging.WARNING)

    print("Logging in to Truth Social... (this may take a moment)")
    
    # 1. Create a single API object and log in ONCE
    try:
        api = Api()
        api._browser_login()
        print("Login successful!")
    except Exception as e:
        print(f"Failed to log in. Error: {e}")
        return

    # 2. Read the list of users
    try:
        with open(USERS_FILE, "r") as f:
            users_to_scrape = [line.strip() for line in f if line.strip()]
        print(f"Found {len(users_to_scrape)} users to scrape.")
    except FileNotFoundError:
        print(f"Error: Could not find '{USERS_FILE}'. Please make sure it exists.")
        return

    # 3. Scrape all users and save the data
    print("Starting to scrape posts for all users...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        total_posts = 0
        for i, username in enumerate(users_to_scrape, 1):
            print(f"({i}/{len(users_to_scrape)}) Scraping posts for: {username}...")
            try:
                for post in api.pull_statuses(
                    username, 
                    replies=False, 
                    pinned=False, 
                    created_after=CREATED_AFTER_DATE, 
                    created_before=CREATED_BEFORE_DATE
                ):
                    f.write(json.dumps(post) + "\n")
                    total_posts += 1
            except Exception as e:
                # This will now only catch genuine errors, not the datetime issue
                print(f"  Could not scrape user '{username}'. Error: {e}")
    
    print("\n--------------------------------------------------")
    print(f"DONE! Scraped a total of {total_posts} posts.")
    print(f"All data saved to '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()