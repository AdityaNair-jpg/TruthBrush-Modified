import json
import os
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from truthbrush.api import Api, LoginErrorException

# --- Configuration ---
TOPIC = "Ukraine"
TARGET_POST_COUNT = 10000
MAX_POSTS_TO_CHECK_PER_USER = 500 
OUTPUT_FILE = f"{TOPIC}_snowball_posts.jsonl"

# --- Unbiased Performance Optimizations ---
MAX_CONCURRENT_SESSIONS = 3  # Parallel sessions for speed
BATCH_SIZE = 30  # Users per batch (smaller to maintain randomness)
USER_SHUFFLE_FREQUENCY = 100  # Reshuffle user queue every N users
RANDOM_SEED_EXPANSION = True  # Continuously discover new seed users
DIVERSE_SEARCH_TERMS = [TOPIC, f"#{TOPIC}", f"{TOPIC.lower()}", f"@{TOPIC}"]  # Multiple search variations

# --- State Files ---
STATE_DIR = "scraper_state"
USERS_TO_SCRAPE_FILE = os.path.join(STATE_DIR, f"{TOPIC}_users_to_scrape.json")
SCRAPED_USERS_FILE = os.path.join(STATE_DIR, f"{TOPIC}_scraped_users.json")
COLLECTED_POST_IDS_FILE = os.path.join(STATE_DIR, f"{TOPIC}_collected_post_ids.json")
SEED_SEARCH_OFFSET_FILE = os.path.join(STATE_DIR, f"{TOPIC}_search_offset.json")

class UnbiasedSnowballScraper:
    def __init__(self):
        self.users_to_scrape = deque()
        self.scraped_users = set()
        self.collected_post_ids = set()
        self.search_offset = 0  # Track search pagination for diverse seeds
        self.lock = threading.Lock()
        self.session_pool = []
        
    def initialize_state(self):
        if not os.path.exists(STATE_DIR): 
            os.makedirs(STATE_DIR)
        print(f"✅ State directory: '{STATE_DIR}'")
        
        # Load existing state
        self.users_to_scrape = deque(self.load_state_list(USERS_TO_SCRAPE_FILE))
        self.scraped_users = self.load_state_set(SCRAPED_USERS_FILE)
        self.collected_post_ids = self.load_state_set(COLLECTED_POST_IDS_FILE)
        self.search_offset = self.load_state_dict(SEED_SEARCH_OFFSET_FILE).get('offset', 0)
        
        # Immediately randomize existing users to remove any previous bias
        if self.users_to_scrape:
            user_list = list(self.users_to_scrape)
            random.shuffle(user_list)
            self.users_to_scrape = deque(user_list)
            print(f"🎲 Randomized {len(self.users_to_scrape)} existing users")

    def save_state(self, data, filepath):
        with open(filepath, 'w') as f: 
            json.dump(list(data) if isinstance(data, (set, deque)) else data, f)

    def load_state_set(self, filepath):
        if not os.path.exists(filepath): return set()
        with open(filepath, 'r') as f: return set(json.load(f))

    def load_state_list(self, filepath):
        if not os.path.exists(filepath): return []
        with open(filepath, 'r') as f: return list(json.load(f))
    
    def load_state_dict(self, filepath):
        if not os.path.exists(filepath): return {}
        with open(filepath, 'r') as f: return json.load(f)

    def create_session_pool(self):
        """Create browser session pool for parallel processing"""
        print(f"🔄 Creating {MAX_CONCURRENT_SESSIONS} browser sessions...")
        for i in range(MAX_CONCURRENT_SESSIONS):
            try:
                api = Api()
                self.session_pool.append(api)
                print(f"  ✅ Session {i+1} ready")
                time.sleep(1)  # Stagger session creation
            except Exception as e:
                print(f"  ⚠️ Failed to create session {i+1}: {e}")

    def discover_diverse_seed_users(self, api_session):
        """Discover seed users from multiple search strategies for unbiased sampling"""
        if self.users_to_scrape and len(self.users_to_scrape) > 50:
            return  # Don't over-seed if we have plenty of users
            
        print(f"\n[Seed Discovery: Expanding user pool with diverse searches...]")
        new_users = set()
        
        try:
            # Strategy 1: Multiple search terms to capture different communities
            for search_term in DIVERSE_SEARCH_TERMS:
                try:
                    posts = api_session.search(
                        searchtype="statuses", 
                        query=search_term,
                        limit=500,
                        offset=self.search_offset  # Paginate through results
                    )
                    
                    for post in posts:
                        if 'account' in post and 'acct' in post['account']:
                            username = post['account']['acct']
                            if username not in self.scraped_users:
                                new_users.add(username)
                                
                    print(f"  🔍 '{search_term}': found {len([p for p in posts if 'account' in p])} users")
                    time.sleep(0.5)  # Respectful delay between searches
                    
                except Exception as e:
                    print(f"  ⚠️ Search failed for '{search_term}': {e}")
            
            # Strategy 2: Random time-based searches to avoid temporal bias
            random_days_back = random.randint(1, 30)
            try:
                # Note: Adjust this based on TruthSocial's API date filtering capabilities
                recent_posts = api_session.search(
                    searchtype="statuses",
                    query=TOPIC,
                    limit=300
                )
                
                for post in recent_posts:
                    if 'account' in post and 'acct' in post['account']:
                        username = post['account']['acct']
                        if username not in self.scraped_users:
                            new_users.add(username)
                            
            except Exception as e:
                print(f"  ⚠️ Recent posts search failed: {e}")
            
            # Update search offset for next round (pagination)
            self.search_offset += 500
            self.save_state({'offset': self.search_offset}, SEED_SEARCH_OFFSET_FILE)
            
            # Randomize and add new users
            new_users_list = list(new_users)
            random.shuffle(new_users_list)
            
            for user in new_users_list:
                if user not in [u for u in self.users_to_scrape]:
                    self.users_to_scrape.append(user)
            
            print(f"🌱 Added {len(new_users_list)} diverse seed users (total queue: {len(self.users_to_scrape)})")
            
        except Exception as e:
            print(f"⚠️ Seed discovery error: {e}")

    def randomize_user_queue(self):
        """Periodically randomize user queue to prevent order bias"""
        if len(self.users_to_scrape) > 10:
            user_list = list(self.users_to_scrape)
            random.shuffle(user_list)
            self.users_to_scrape = deque(user_list)
            print(f"🎲 Randomized user queue ({len(user_list)} users)")

    def scrape_user_batch_unbiased(self, api_session, users_batch, session_id):
        """Scrape users with randomized post sampling for unbiased data"""
        local_posts = []
        local_new_users = []
        
        for username in users_batch:
            if username in self.scraped_users or len(self.collected_post_ids) >= TARGET_POST_COUNT:
                continue
                
            try:
                print(f"  [Session {session_id}] 🔍 @{username}")
                
                # Get user posts
                user_posts = list(api_session.pull_statuses(username=username, replies=True))
                
                # CRITICAL: Randomize post order to avoid temporal bias
                random.shuffle(user_posts)
                
                posts_checked = 0
                for post in user_posts:
                    if posts_checked >= MAX_POSTS_TO_CHECK_PER_USER:
                        break
                    posts_checked += 1
                    
                    post_id = post.get('id')
                    if not post_id or post_id in self.collected_post_ids:
                        continue
                    
                    post_content = post.get('content', '').lower()
                    if TOPIC.lower() in post_content:
                        local_posts.append(post)
                        
                        # Unbiased user discovery: sample from ALL interactions, not just top
                        try:
                            # Get likers but randomize the limit to avoid bias toward highly-liked posts
                            random_limit = random.randint(5, 20)
                            likers = list(api_session.user_likes(post_id=post_id, limit=random_limit))
                            
                            # Randomly sample from likers instead of taking first N
                            if len(likers) > 5:
                                likers = random.sample(likers, min(5, len(likers)))
                            
                            for liker in likers:
                                liker_username = liker.get('acct')
                                if (liker_username and 
                                    liker_username not in self.scraped_users and 
                                    liker_username not in [u for u in self.users_to_scrape]):
                                    local_new_users.append(liker_username)
                                    
                        except Exception:
                            pass  # Don't let engagement discovery block main scraping
                
            except Exception as e:
                print(f"  [Session {session_id}] ⚠️ Error with @{username}: {e}")
                continue
                
        # Randomize new users before returning
        random.shuffle(local_new_users)
        return local_posts, local_new_users

    def process_users_parallel_unbiased(self):
        """Process users in parallel while maintaining randomness and diversity"""
        print(f"\n[Parallel Processing: {len(self.session_pool)} sessions, maintaining randomness]")
        
        users_processed = 0
        
        with ThreadPoolExecutor(max_workers=len(self.session_pool)) as executor:
            while self.users_to_scrape and len(self.collected_post_ids) < TARGET_POST_COUNT:
                
                # Periodically shuffle queue to prevent bias
                if users_processed % USER_SHUFFLE_FREQUENCY == 0 and users_processed > 0:
                    self.randomize_user_queue()
                
                # Periodically discover new diverse seeds
                if (users_processed % 200 == 0 and 
                    RANDOM_SEED_EXPANSION and 
                    len(self.session_pool) > 0):
                    try:
                        self.discover_diverse_seed_users(self.session_pool[0])
                    except Exception as e:
                        print(f"⚠️ Seed expansion failed: {e}")
                
                # Create randomized batches
                current_batch_size = min(BATCH_SIZE, len(self.users_to_scrape))
                if current_batch_size == 0:
                    break
                    
                user_batches = []
                sessions_to_use = min(len(self.session_pool), 
                                    (current_batch_size // (BATCH_SIZE // len(self.session_pool))) + 1)
                
                for i in range(sessions_to_use):
                    batch = []
                    batch_size = min(BATCH_SIZE // sessions_to_use, len(self.users_to_scrape))
                    
                    for _ in range(batch_size):
                        if self.users_to_scrape:
                            batch.append(self.users_to_scrape.popleft())
                    
                    if batch:
                        user_batches.append((batch, i))
                
                if not user_batches:
                    break
                
                # Submit parallel jobs
                future_to_session = {}
                for batch, session_id in user_batches:
                    if session_id < len(self.session_pool):
                        future = executor.submit(
                            self.scrape_user_batch_unbiased, 
                            self.session_pool[session_id], 
                            batch, 
                            session_id + 1
                        )
                        future_to_session[future] = session_id
                
                # Collect results as they complete
                for future in as_completed(future_to_session, timeout=300):
                    try:
                        posts, new_users = future.result()
                        session_id = future_to_session[future]
                        
                        # Thread-safe updates
                        with self.lock:
                            # Write posts immediately
                            with open(OUTPUT_FILE, 'a') as f:
                                for post in posts:
                                    if post['id'] not in self.collected_post_ids:
                                        f.write(json.dumps(post) + '\n')
                                        self.collected_post_ids.add(post['id'])
                            
                            # Add new users in random order
                            for user in new_users:
                                if user not in self.scraped_users:
                                    # Insert at random position to maintain randomness
                                    if len(self.users_to_scrape) > 0:
                                        random_pos = random.randint(0, len(self.users_to_scrape))
                                        self.users_to_scrape.insert(random_pos, user)
                                    else:
                                        self.users_to_scrape.append(user)
                        
                        users_processed += len([batch for batch, _ in user_batches if future_to_session.get(future) == _][0])
                        
                    except Exception as e:
                        print(f"⚠️ Batch processing error: {e}")
                
                # Mark all users in batches as scraped
                with self.lock:
                    for batch, _ in user_batches:
                        for user in batch:
                            self.scraped_users.add(user)
                
                print(f"📊 Progress: {len(self.collected_post_ids)}/{TARGET_POST_COUNT} posts | "
                      f"{len(self.users_to_scrape)} users queued | "
                      f"{users_processed} total processed")
                
                # Periodic state save
                if users_processed % 50 == 0:
                    self.save_periodic_state()

    def save_periodic_state(self):
        """Save state periodically"""
        print("💾 Saving state...")
        self.save_state(self.users_to_scrape, USERS_TO_SCRAPE_FILE)
        self.save_state(self.scraped_users, SCRAPED_USERS_FILE)
        self.save_state(self.collected_post_ids, COLLECTED_POST_IDS_FILE)

    def cleanup_sessions(self):
        """Clean up all browser sessions"""
        print("🧹 Cleaning up sessions...")
        for i, api in enumerate(self.session_pool):
            try:
                api.quit()
                print(f"  ✅ Session {i+1} closed")
            except Exception as e:
                print(f"  ⚠️ Error closing session {i+1}: {e}")

    def run(self):
        """Main execution with unbiased sampling"""
        try:
            print("🎯 Starting UNBIASED snowball scraper...")
            print(f"🎲 Random seed: {random.seed()}")
            
            self.initialize_state()
            self.create_session_pool()
            
            if not self.session_pool:
                print("❌ No browser sessions available. Exiting.")
                return
                
            # Always try to expand seed diversity
            self.discover_diverse_seed_users(self.session_pool[0])
            
            if not self.users_to_scrape:
                print("❌ No users to scrape after seed discovery. Exiting.")
                return
            
            # Start with randomized user queue
            self.randomize_user_queue()
            
            print(f"🚀 Beginning parallel processing of {len(self.users_to_scrape)} randomized users")
            self.process_users_parallel_unbiased()
            
        except Exception as e:
            print(f"\n❌ Critical error: {e}")
        finally:
            self.cleanup_sessions()
            self.save_periodic_state()
            print("✨ Unbiased scraping completed.")
            print(f"📈 Final stats: {len(self.collected_post_ids)} posts, {len(self.scraped_users)} users processed")

if __name__ == "__main__":
    scraper = UnbiasedSnowballScraper()
    scraper.run()