import json
import os
import time
import multiprocessing
from truthbrush.api import Api, LoginErrorException # Assuming your api.py is in truthbrush/api.py

# --- Configuration ---
TOPIC = "Europe"
TARGET_POST_COUNT = 10000
MAX_POSTS_TO_CHECK_PER_USER = 500
OUTPUT_FILE = f"{TOPIC}_snowball_posts.jsonl"

# --- KEY CHANGE: Number of parallel browser instances ---
# Start with 2 or 3 and increase based on your PC's performance.
NUM_WORKERS = 3

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

# --- KEY CHANGE: The Worker Function ---
# This function runs in its own process. It initializes its own API/browser instance.
def scrape_worker(username):
    """
    A self-contained worker that scrapes one user and returns the results.
    """
    print(f"[Worker {os.getpid()}] Starting to scrape @{username}")
    api = None
    found_posts = []
    found_users = []
    
    try:
        # Each worker creates its own browser session.
        api = Api() 
        
        # 1. Scrape user for posts with the topic
        user_posts_generator = api.pull_statuses(username=username, replies=True)
        posts_checked = 0
        for post in user_posts_generator:
            if posts_checked >= MAX_POSTS_TO_CHECK_PER_USER:
                break
            posts_checked += 1

            post_content = post.get('content', '').lower()
            if TOPIC.lower() in post_content:
                found_posts.append(post)

                # 2. Find new users from the likes of relevant posts
                try:
                    likers = api.user_likes(post_id=post.get('id'), limit=10)
                    for liker in likers:
                        liker_username = liker.get('acct')
                        if liker_username:
                            found_users.append(liker_username)
                except Exception:
                    pass # Ignore errors on finding likers
                    
    except Exception as e:
        print(f"⚠️ [Worker {os.getpid()}] Error scraping @{username}: {e}")
    finally:
        # 3. CRITICAL: Close the browser to free up resources
        if api:
            api.quit()
            
    print(f"[Worker {os.getpid()}] Finished with @{username}. Found {len(found_posts)} posts and {len(found_users)} new users.")
    # 4. Return all collected data from this user
    return {
        "scraped_user": username,
        "found_posts": found_posts,
        "newly_found_users": found_users
    }

# --- KEY CHANGE: The Main Orchestrator ---
def run_parallel_scraper():
    initialize_state()
    
    users_to_scrape = load_state_list(USERS_TO_SCRAPE_FILE)
    scraped_users = load_state_set(SCRAPED_USERS_FILE)
    collected_post_ids = load_state_set(COLLECTED_POST_IDS_FILE)
    
    # Initial seeding if the scraper is brand new
    if not users_to_scrape and not scraped_users:
        print("\n[Phase 1: No existing state found. Discovering seed users with a temporary session...]")
        temp_api = None
        try:
            temp_api = Api()
            seed_posts = temp_api.search(searchtype="statuses", query=TOPIC, limit=100)
            for post in seed_posts:
                username = post.get('account', {}).get('acct')
                if username and username not in scraped_users and username not in users_to_scrape:
                    users_to_scrape.append(username)
            print(f"🌱 Discovered {len(users_to_scrape)} initial seed users.")
            save_state(users_to_scrape, USERS_TO_SCRAPE_FILE)
        except Exception as e:
            print(f"⚠️ Warning: Could not fetch seed users. Error: {e}")
        finally:
            if temp_api:
                temp_api.quit()

    if not users_to_scrape:
        print("❌ No users to scrape. The initial seed search may have failed. Exiting.")
        return

    print(f"\n[Phase 2: Starting main scraping loop with {NUM_WORKERS} parallel workers]")
    
    # The main loop continues as long as we have users and haven't met the target
    while users_to_scrape and len(collected_post_ids) < TARGET_POST_COUNT:
        # Take a batch of users to process in parallel
        batch_size = NUM_WORKERS * 2 # Give the pool a bit of work to chew on
        users_batch = []
        
        # De-duplicate the users_to_scrape list while creating the batch
        temp_users_set = set()
        new_users_to_scrape = []
        for user in users_to_scrape:
            if user not in scraped_users and user not in temp_users_set:
                temp_users_set.add(user)
                if len(users_batch) < batch_size:
                    users_batch.append(user)
                else:
                    new_users_to_scrape.append(user)
        
        users_to_scrape = new_users_to_scrape + list(temp_users_set - set(users_batch))

        if not users_batch:
            print("No new users left to scrape in the queue. Exiting.")
            break

        print(f"\n--- Processing a batch of {len(users_batch)} users ---")
        
        # Use a multiprocessing Pool to run scrape_worker on the batch
        with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
            results = pool.map(scrape_worker, users_batch)

        # Process the results from the batch
        for result in results:
            scraped_users.add(result['scraped_user'])
            
            # Save new posts
            for post in result['found_posts']:
                post_id = post.get('id')
                if post_id and post_id not in collected_post_ids:
                    with open(OUTPUT_FILE, 'a') as f:
                        f.write(json.dumps(post) + '\n')
                    collected_post_ids.add(post_id)
            
            # Add newly found users to the main queue
            for new_user in result['newly_found_users']:
                if new_user not in scraped_users and new_user not in users_to_scrape:
                    users_to_scrape.append(new_user)
        
        # Save state after each batch is processed
        print("💾 Saving progress...")
        save_state(users_to_scrape, USERS_TO_SCRAPE_FILE)
        save_state(scraped_users, SCRAPED_USERS_FILE)
        save_state(collected_post_ids, COLLECTED_POST_IDS_FILE)
        print(f"--- Progress: {len(collected_post_ids)}/{TARGET_POST_COUNT} posts --- ({len(users_to_scrape)} users in queue) ---")

    print("\n✨ Target post count reached or no users left. Done.")

if __name__ == "__main__":
    # This is essential for multiprocessing to work correctly on all platforms
    multiprocessing.freeze_support() 
    run_parallel_scraper()