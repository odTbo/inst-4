from modules.profile_scraper import ProfileScraperMixin as ScraperMixin
from modules.instagram_manager import Instagram as IgMixin
from modules.constants import DATE_STR, ACTIONS_LIMIT, FOLLOWS_PER_DAY
from modules.utils import timeout
from dotenv import load_dotenv
import time
from os import path
try:
    from instagram_private_api import ClientError
except ImportError:
    import sys
    sys.path.append(path.join(path.dirname(__file__), '..'))
    from instagram_private_api import ClientError

load_dotenv()


class Inst4(IgMixin, ScraperMixin):
    def __init__(self):
        super().__init__()
        self.method = ""
        self.actions = {
            "follow": 0,
            "unfollow": 0,
            "post_like": 0,
            "comment": 0
        }
        self.errors = []

    def session(self):
        self.logs_dir_create()

        # Bonus image scraper
        to_scrape = self.users_to_scrape()
        if to_scrape:
            print("[IG] Scraper method")
            self.method = "Scraper"
            for user in to_scrape:
                try:
                    self.scraper_method(user)
                except ClientError as e:
                    error = str(e)
                    print(error, user)
                    if "Not authorized to view user" in error:
                        self.follow_user(user)
                        self.export_username(user, scrape=True)
                        # TODO Request a follow, save username

        else:
            self.my_followers = set(user["username"] for user in self.fetch_followers(self.username, all_=True))

            # Unfollow list ready
            if self.expired_lists():
                print("[IG] Unfollow Method")
                self.method = "Unfollow"
                self.unfollow_method()

            # Follow more people
            else:
                print("[IG] Follow Method")
                self.method = "Follow"

                follows_today = self.fetch_users_from_file(f"{DATE_STR}.txt")
                if follows_today:

                    # To get FOLLOWS_PER_DAY followers a day
                    if FOLLOWS_PER_DAY <= len(follows_today):
                        print("Enough follows for today")
                    else:
                        print(f"Follows made today: {len(follows_today)}")

                        self.follow_method()
                else:
                    print("No follows yet today.")

                    self.follow_method()

            print(f"Actions made in this session: {self.actions}")

            logs = {
                "method": self.method,
                "actions": self.actions,
                "current_following": len(self.my_followers)
            }
            if self.method == "Follow":
                logs.update({"target_account": self.target_account})

            self.log_actions(**logs)
            self.log_errors(self.errors)

    # BONUS IMAGE DOWNLOADER
    def scraper_method(self, username, download_posts=9999):
        """User's feed scraper script."""
        # print(datetime.fromtimestamp(taken_at).strftime('%d-%m-%Y')) # Taken_at post timestamp to date
        print(f"Scraping profile: {username}")

        # Fetch posts
        posts = self.fetch_posts(username=username, max_posts=download_posts)
        print(f"Posts to scrape: {len(posts)}")

        # Extract URLs from all posts
        urls = self.extract_urls(posts)
        print(f"Media to download: {len(urls)}")

        # Download posts
        print("Downloading media...")
        self.dwnld_imgs(username, urls)

    def unfollow_method(self):
        """Unfollow ACTIONS_LIMIT number of users from the expired unfollow list."""
        to_unfollow_list = self.fetch_users_from_file(self.expired_list)

        # While there are users to unfollow
        while len(to_unfollow_list) != 0:

            # Get the first user from the list
            user = to_unfollow_list[0]
            # try:
            #     user = int(user)
            # except ValueError:
            #     pass

            # Reached set actions limit
            if self.actions["unfollow"] == ACTIONS_LIMIT:
                print(f"Reached session actions limit.")
                # Save the rest of users to original file
                self.export_to_unfollow(to_unfollow_list, filename=self.expired_list)
                break

            # User is not a follower
            elif user not in self.my_followers:
                try:
                    # Unfollow
                    # assert type(user) == int
                    if self.unfollow_user(user):
                        self.actions["unfollow"] += 1
                        timeout()
                        # Successful unfollow
                        to_unfollow_list.remove(user)
                    # Actions limited by instagram
                    else:
                        # Save the rest of users to original file
                        self.export_to_unfollow(to_unfollow_list, filename=self.expired_list)
                        print("Error unfollowing, exiting.")
                        break

                # Internal API errors
                except ClientError as e:
                    # error_msg = f"UNFOLLOW ERROR {e} {user}"
                    error_msg = {
                        "method": self.method,
                        "user": user,
                        "error": str(e)
                    }
                    print(error_msg)
                    self.errors.append(error_msg)
                    to_unfollow_list.remove(user)

            # User follows back
            else:
                to_unfollow_list.remove(user)

        # Remove the source file if it's empty
        if len(to_unfollow_list) == 0:
            self.remove_finished_file(filename=self.expired_list)

    def follow_method(self):
        """Follow and like post's of followers from TARGET_ACCOUNT."""
        self.to_ignore = set(self.fetch_users_from_file("to_ignore.txt"))
        # Fetch accounts to follow
        to_follow = self.fetch_followers(self.target_account)

        print(f"Num of users to follow: {len(to_follow)}")

        for user in to_follow:
            try:
                if self.follow_user(user["pk"]):
                    print(f"Followed user: {user['username']}")
                    timeout()
                    self.export_username(user["pk"], unfollow=True, ignore=True)
                    self.actions["follow"] += 1
                    # Like users posts
                    posts = self.fetch_posts(user["pk"], step=2)
                    if posts:
                        print(f"Liking posts for {user['username']}.")
                        for post in posts:
                            try:
                                self.api.post_like(post["pk"])
                            except ClientError as e:
                                error_msg = {
                                    "method": self.method,
                                    "action": "post_like",
                                    "post": post["pk"],
                                    "error": str(e)
                                }
                                print(error_msg)
                                self.errors.append(error_msg)
                            else:
                                self.actions["post_like"] += 1
                                timeout()
                    else:
                        print(f"{user['username']} has no posts.")
                    # self.like_posts(user["username"], step=2)
                    print("\n")
                else:
                    print(f"Actions limited! Reached {self.actions} actions.")
                    # Actions limited
                    break
            except ClientError as e:
                # error_msg = f"FOLLOW ERROR {e} {user['username']}"
                error_msg = {
                    "method": self.method,
                    "action": "follow",
                    "user": {
                        "username": user["username"],
                        "user_id": user["pk"]
                    },
                    "error": str(e)
                }
                print(error_msg)
                self.errors.append(error_msg)
                self.export_username(user["username"], ignore=True)


if __name__ == "__main__":
    ig = Inst4()
    ig.session()

    # # Download saved feed (wip)
    # posts = ig.fetch_user_saved(max_posts=10)
    # urls = ig.extract_urls(posts)
    # ig.dwnld_imgs(ig.username, urls)
    # posts = ig.fetch_user_saved(all_=True)
    # posts = [post['id'] for post in posts]
    # print(len(posts))
    # print(posts)
