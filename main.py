import json
import codecs
import datetime
import time
from os import path, getenv, remove, mkdir
from datetime import datetime
from random import choice
import glob
import logging
import argparse
from dotenv import load_dotenv
# https://github.com/ping/instagram_private_api
# pip install git+https://git@github.com/ping/instagram_private_api.git@1.6.0
# pip install git+https://git@github.com/ping/instagram_private_api.git@1.6.0 --upgrade
try:
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError,
        __version__ as client_version)
except ImportError:
    import sys
    sys.path.append(path.join(path.dirname(__file__), '..'))
    from instagram_private_api import (
        Client, ClientError, ClientLoginError,
        ClientCookieExpiredError, ClientLoginRequiredError,
        __version__ as client_version)

# Follow/Unfollow actions limit
ACTIONS_LIMIT = choice(range(20, 31))
# Log files location
LOGS_PATH = "logs/"
# Account with target audience
TARGET_ACCOUNT = "soulhoe"


load_dotenv()


class Instagram:
    def __init__(self):
        self.username = getenv("IG_USERNAME")
        self.password = getenv("IG_PASSWORD")
        self.settings_file_path = "ig_credentials.json"
        self.to_ignore = set()
        self.my_followers = set()
        self.expired_follows_file = ""
        self.users = []
        self.actions = {
            "Follow": 0,
            "Unfollow": 0,
            "Post Like": 0
        }
        self.errors = []

    def run(self):
        self.logs_dir()
        self.login()
        self.my_followers = set(user["username"] for user in self.fetch_followers(self.username, my_account=True))
        if self.expired_lists():
            print("[IG] Unfollow Method")
            self.unfollow_method()
        else:
            print("[IG] Follow Method")
            self.follow_method()

        print(f"Actions made in this session: {self.actions}")

    def unfollow_method(self):
        to_unfollow_list = self.fetch_users_from_file(self.expired_follows_file)

        # While there are user to unfollow
        while len(to_unfollow_list) != 0:

            # Get the first user from the list
            user = to_unfollow_list[0]

            # Reached set actions limit
            if self.actions["Unfollow"] == ACTIONS_LIMIT:
                print(f"Reached {ACTIONS_LIMIT} unfollows limit.")
                # Save the rest of users to original file
                self.export_to_unfollow(to_unfollow_list, filename=self.expired_follows_file)
                break

            elif user not in self.my_followers:
                try:
                    # Unfollow
                    if self.unfollow_user(user):
                        self.actions["Unfollow"] += 1
                        time.sleep(1)
                        # Successful unfollow
                        to_unfollow_list.remove(user)
                    # Actions limited by instagram
                    else:
                        # Save the rest of users to original file
                        self.export_to_unfollow(to_unfollow_list, filename=self.expired_follows_file)
                        print("Error unfollowing, exiting.")
                        break
                # Internal API errors
                except ClientError as e:
                    error_msg = f"UNFOLLOW {e} {user}"
                    self.errors.append(error_msg)
                    to_unfollow_list.remove(user)

            # Users follows back
            else:
                to_unfollow_list.remove(user)

        # Remove the empty source file if it's empty
        if len(to_unfollow_list) == 0:
            self.remove_finished_file(filename=self.expired_follows_file)

        self.log_actions(method="Unfollow")

    def follow_method(self):
        self.to_ignore = set(self.fetch_users_from_file("to_ignore.txt"))
        # Fetch accounts to follow
        to_follow = self.fetch_followers(TARGET_ACCOUNT)

        print(f"Num of users to follow: {len(to_follow)}")

        for user in to_follow:
            try:
                if self.follow_user(user["username"]):
                    time.sleep(1)
                    self.export_username(user["username"])
                    self.actions["Follow"] += 1
                    # Like users posts
                    self.like_posts(user["username"])
                    print("\n")
                else:
                    print(f"Actions limited! Reached {self.actions} actions.")
                    # Actions limited
                    break
            except ClientError as e:
                error_msg = f"FOLLOW {e} {user['username']}"
                self.errors.append(error_msg)
                self.export_username(user["username"], unfollow=False)

        self.log_actions(method="Follow")

    def login(self):
        """Establishes connection to Instagram API."""
        # print('Client version: {0!s}'.format(client_version))

        device_id = None
        try:
            settings_file = self.settings_file_path
            if not path.isfile(settings_file):
                # settings file does not exist
                print('Unable to find file: {0!s}'.format(settings_file))

                # login new
                self.api = Client(
                    self.username, self.password,
                    on_login=lambda x: self.onlogin_callback(x, self.settings_file_path), auto_patch=True)
            else:
                with open(settings_file) as file_data:
                    cached_settings = json.load(file_data, object_hook=self.from_json)
                # print('Reusing settings: {0!s}'.format(settings_file))

                device_id = cached_settings.get('device_id')
                # reuse auth settings
                self.api = Client(
                    self.username, self.password,
                    settings=cached_settings, auto_patch=True)

        except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
            print('ClientCookieExpiredError/ClientLoginRequiredError: {0!s}'.format(e))

            # Login expired
            # Do relogin but use default ua, keys and such
            self.api = Client(
                self.username, self.password,
                device_id=device_id,
                on_login=lambda x: self.onlogin_callback(x, self.settings_file_path), auto_patch=True)

        except ClientLoginError as e:
            print('ClientLoginError {0!s}'.format(e))
            exit(9)
        except ClientError as e:
            print('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response))
            exit(9)
        except Exception as e:
            print('Unexpected Exception: {0!s}'.format(e))
            exit(99)

        # Show when login expires
        # cookie_expiry = self.api.cookie_jar.auth_expires
        # print('Cookie Expiry: {0!s}'.format(
        #     datetime.datetime.fromtimestamp(cookie_expiry).strftime('%Y-%m-%dT%H:%M:%SZ')))

    def fetch_followers(self, target_account, my_account=False):
        """Grabs followers from target account."""
        # Get user_id
        result = self.api.username_info(target_account)
        user_id = result["user"]["pk"]
        rank_token = self.api.generate_uuid()

        # r = self.api.user_following(user_id=user_id, rank_token=rank_token)
        users = []
        results = self.api.user_followers(user_id, rank_token=rank_token)
        users.extend(results.get('users', []))

        next_max_id = results.get('next_max_id')
        # print(f"Num of users from result: {len(users)}")
        if my_account:
            while next_max_id:
                time.sleep(1)
                results = self.api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
                users.extend(results.get('users', []))

                next_max_id = results.get('next_max_id')
        else:
            output = []
            satisfied = False
            while not satisfied:
                # Check users
                for user in users:
                    # If account meets conditions, add it to the output
                    if self.follow_conditions(user) and user not in output:
                        output.append(user)
                if len(output) >= ACTIONS_LIMIT or not next_max_id:  # If list has still more than 30 users we can move on
                    satisfied = True
                else:
                    results = self.api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
                    users.extend(results.get('users', []))
                    next_max_id = results.get('next_max_id')

            if len(output) > ACTIONS_LIMIT:
                users = output[:ACTIONS_LIMIT]

        return users

    def follow_user(self, username):
        """Follow IG User by username."""
        # Get user_id
        result = self.api.username_info(username)
        user_id = result["user"]["pk"]

        # Follow by user_id
        r = self.api.friendships_create(user_id)
        if r["status"] == "ok":
            print(f"[IG] Followed {username}.")
            return True
        else:
            print(r)
            return False

    def unfollow_user(self, username):
        """Unfollow IG User by username."""
        # Get user_id
        result = self.api.username_info(username)
        user_id = result["user"]["pk"]

        # Unfollow by user_id
        r = self.api.friendships_destroy(user_id)
        if r["status"] == "ok":
            print(f"[IG] Unfollowed {username}.")
            return True
        else:
            print(r)
            return False

    def like_posts(self, username):
        """Like User's posts."""
        # Get user id
        result = self.api.username_info(username)
        user_id = result["user"]["pk"]

        updates = []
        results = self.api.user_feed(user_id)
        updates.extend(results.get('items', []))

        next_max_id = results.get('next_max_id')
        while next_max_id:
            results = self.api.user_feed(user_id, max_id=next_max_id)
            updates.extend(results.get('items', []))
            if len(updates) >= 10:  # get only first 10 or so
                break
            next_max_id = results.get('next_max_id')
        if len(updates) != 0:
            print(f"[IG] Liking posts for {username}...")
            posts = updates[::3]
            for post in posts:
                # Like post
                self.api.post_like(post["id"])
                self.actions["Post Like"] += 1
                time.sleep(1)
            print(f"[IG] Liked {username}'s {len(posts)} posts.")
        else:
            print(f"[IG] No posts for user {username}.")

    def follow_conditions(self, account):
        """Checks against conditions in order to follow the account."""
        # print(account["username"], account["is_private"], account["has_anonymous_profile_picture"])

        # Account can't be private
        if account["is_private"]:
            # print(f"Private account: {account['username']}")
            return False
        # Account can't have anonymous profile picture
        elif account["has_anonymous_profile_picture"]:
            # print(f"Has anonymous pfp: {account['username']}")
            return False
        # Account was interacted with in the past already
        elif account["username"] in self.to_ignore:
            # print(f"Account to ignore: {account['username']}")
            return False
        else:
            return True

    def export_username(self, username, unfollow=True, ignore=True):
        """Saves followed user to unfollow list and to ignore list, to prevent future interaction with the account."""
        today = datetime.now()
        date = today.strftime("%d-%m-%Y")

        # Save to unfollow list
        if unfollow:
            with open(LOGS_PATH + f"{date}.txt", mode="a") as f:
                f.write(f"{username}\n")

        # Save to ignore list
        if ignore:
            with open(LOGS_PATH + "to_ignore.txt", mode="a") as f:
                f.write(f"{username}\n")

    def export_to_unfollow(self, usernames, filename):
        """Saves remaining usernames waiting for unfollow to the original file."""
        filename = LOGS_PATH + filename
        with open(filename, mode="w") as f:
            f.write('\n'.join(usernames))
            f.write('\n')

    def expired_lists(self):
        """Checks if there are lists atleast 4 days old to unfollow."""
        date_today = datetime.now()
        filenames = [file[5:-4] for file in glob.glob(LOGS_PATH + "*.txt")]

        for date in filenames:

            # Convert filename to datetime object
            try:
                fname_date = datetime.strptime(date, "%d-%m-%Y")
            except ValueError:
                pass
            else:
                # Check if the file older than 4 days
                if int((date_today - fname_date).days) >= 4:
                    self.expired_follows_file = f'{fname_date.strftime("%d-%m-%Y")}.txt'
                    print("[IG] Expired list found")
                    return True

        return False

    def fetch_users_from_file(self, filename):
        """Grabs all usernames from a file and returns them as a list."""
        filename = LOGS_PATH + filename
        if path.exists(filename):
            with open(filename, "r") as f:
                output = [line.strip() for line in f.readlines()]
        else:
            print(f"The file '{filename}' doesn't exist.")
            return

        return output

    def remove_finished_file(self, filename):
        """Remove list."""
        filename = LOGS_PATH + filename
        if path.exists(filename):
            remove(filename)
        else:
            print(f"The file '{filename}' doesn't exist.")

    def log_actions(self, method):
        """Logs the number of instagram actions made in a session."""
        today = datetime.now()
        date = today.strftime("%d-%m-%YT%H:%M:00")

        actions = ", ".join([f"{key}: {value}" for (key, value) in self.actions.items() if value != 0])

        with open(LOGS_PATH + "actions_log.txt", "a") as f:
            f.write(f"DATE: {date}, "
                    f"METHOD: {method}, "
                    f"CURRENT FOLLOWING: {len(self.my_followers)}, "
                    f"ACTIONS: {actions}\n")

    def log_errors(self):
        """Logs the errors encountered in a session."""
        with open(LOGS_PATH + "errors_log.txt", "a") as f:
            f.write('\n'.join(self.errors))
            f.write('\n')

    def logs_dir(self):
        if path.exists(LOGS_PATH):
            pass
        else:
            mkdir(LOGS_PATH)
            print("Logs directory created.")

    def to_json(self, python_object):
        if isinstance(python_object, bytes):
            return {'__class__': 'bytes',
                    '__value__': codecs.encode(python_object, 'base64').decode()}
        raise TypeError(repr(python_object) + ' is not JSON serializable')

    def from_json(self, json_object):
        if '__class__' in json_object and json_object['__class__'] == 'bytes':
            return codecs.decode(json_object['__value__'].encode(), 'base64')
        return json_object

    def onlogin_callback(self, api, new_settings_file):
        cache_settings = api.settings
        with open(new_settings_file, 'w') as outfile:
            json.dump(cache_settings, outfile, default=self.to_json)
            print('SAVED: {0!s}'.format(new_settings_file))


if __name__ == "__main__":
    ig = Instagram()
    ig.run()
