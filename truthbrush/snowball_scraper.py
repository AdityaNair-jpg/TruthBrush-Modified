import json
import os
import time
from truthbrush.api import Api, LoginErrorException

# --- Configuration ---
TOPIC = "Russia"
TARGET_POST_COUNT = 10000
MAX_POSTS_TO_CHECK_PER_USER = 500 
OUTPUT_FILE = f"{TOPIC}_snowball_posts.jsonl"

# --- State Files ---
STATE_DIR = "scraper_state"
USERS_TO_SCRAPE_FILE = os.path.join(STATE_DIR, f"{TOPIC}_users_to_scrape.json")
SCRAPED_USERS_FILE = os.path.join(STATE_DIR, f"{TOPIC}_scraped_users.json")
COLLECTED_POST_IDS_FILE = os.path.join(STATE_DIR, f"{TOPIC}_collected_post_ids.json")

# --- Helper Functions (unchanged) ---
def initialize_state():
    if not os.path.exists(STATE_DIR): os.makedirs(STATE_DIR)
    print(f"✅ State will be managed in the '{STATE_DIR}' directory.")
def save_state(data, filepath):
    with open(filepath, 'w') as f: json.dump(list(data), f)
def load_state_set(filepath):
    if not os.path.exists(filepath): return set()
    with open(filepath, 'r') as f: return set(json.load(f))
def load_state_list(filepath):
    if not os.path.exists(filepath): return []
    with open(filepath, 'r') as f: return list(json.load(f))

def run_robust_snowball_scraper():
    initialize_state()
    
    users_to_scrape = load_state_list(USERS_TO_SCRAPE_FILE)
    scraped_users = load_state_set(SCRAPED_USERS_FILE)
    collected_post_ids = load_state_set(COLLECTED_POST_IDS_FILE)
    
    tb_api = None
    try:
        # --- KEY CHANGE: Initialize API client ONCE at the start ---
        print("\n[Phase 1: Establishing a persistent browser session...]")
        tb_api = Api()

        if not users_to_scrape and not scraped_users:
            print("\n[Phase 2: No existing state found. Discovering seed users.]")
            try:
                seed_posts = tb_api.search(searchtype="statuses", query=TOPIC, limit=1000)
                for post in seed_posts:
                    if 'account' in post and 'acct' in post['account']:
                        username = post['account']['acct']
                        if username not in scraped_users and username not in users_to_scrape:
                            users_to_scrape.append(username)
                print(f"🌱 Discovered {len(users_to_scrape)} initial seed users.")
                save_state(users_to_scrape, USERS_TO_SCRAPE_FILE)
            except Exception as e:
                print(f"⚠️ Warning: Could not fetch seed users. Error: {e}")

        if not users_to_scrape:
            print("❌ No users to scrape. The initial seed search may have failed. Exiting.")
            return

        print("\n[Phase 3: Starting the main scraping and discovery loop]")
        while users_to_scrape and len(collected_post_ids) < TARGET_POST_COUNT:
            current_user = users_to_scrape.pop(0)
            if current_user in scraped_users: continue

            print(f"\n--- Scraping user: @{current_user} ({len(users_to_scrape)} left) | Progress: {len(collected_post_ids)}/{TARGET_POST_COUNT} posts ---")

            try:
                user_posts_generator = tb_api.pull_statuses(username=current_user, replies=True)
                posts_checked = 0
                for post in user_posts_generator:
                    if posts_checked >= MAX_POSTS_TO_CHECK_PER_USER:
                        print(f"    -> Reached check limit for @{current_user}. Moving on.")
                        break
                    posts_checked += 1

                    post_id = post.get('id')
                    if not post_id or post_id in collected_post_ids: continue

                    post_content = post.get('content', '').lower()
                    if TOPIC.lower() in post_content:
                        print(f"    -> Found relevant post! ID: {post_id}")
                        with open(OUTPUT_FILE, 'a') as f: f.write(json.dumps(post) + '\n')
                        collected_post_ids.add(post_id)

                        try:
                            likers = tb_api.user_likes(post_id=post_id, limit=10)
                            for liker in likers:
                                username = liker.get('acct')
                                if username and username not in scraped_users and username not in users_to_scrape:
                                    users_to_scrape.append(username)
                        except Exception: pass
            
            except Exception as e:
                print(f"⚠️ Warning: An error occurred while scraping @{current_user}. Skipping. Error: {e}")

            scraped_users.add(current_user)
            if len(scraped_users) % 5 == 0:
                print("💾 Saving progress...")
                save_state(users_to_scrape, USERS_TO_SCRAPE_FILE)
                save_state(scraped_users, SCRAPED_USERS_FILE)
                save_state(collected_post_ids, COLLECTED_POST_IDS_FILE)
            
            time.sleep(0.5) # A short delay between users is still polite

    except (LoginErrorException, Exception) as e:
        print(f"\n❌ A critical error occurred: {e}")
    finally:
        # --- KEY CHANGE: Ensure the browser is always closed at the end ---
        print("\n--- Scraper session finished. ---")
        if tb_api:
            tb_api.quit()
        
        print("💾 Performing final state save...")
        save_state(users_to_scrape, USERS_TO_SCRAPE_FILE)
        save_state(scraped_users, SCRAPED_USERS_FILE)
        save_state(collected_post_ids, COLLECTED_POST_IDS_FILE)
        print("✨ Done.")

if __name__ == "__main__":
    run_robust_snowball_scraper()