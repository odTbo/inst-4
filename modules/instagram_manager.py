from modules.utils import *
from modules.logs_manager import LogsManager as Logs
from modules.constants import *
from pathlib import Path
import datetime
from os import path, getenv
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


class Instagram(Logs):
    def __init__(self):
        self.username = getenv("IG_USERNAME")
        self.password = getenv("IG_PASSWORD")
        self.target_account = getenv("TARGET_ACCOUNT")
        self.settings_filename = "ig_credentials.json"
        try:
            self.to_ignore = set(self.fetch_users_from_file("to_ignore.txt"))
        except TypeError:
            self.to_ignore = set()
        self.users = []
        self.my_followers = set()
        self.__login()

    def __login(self):
        """Establishes connection to Instagram API."""
        print('Client version: {0!s}'.format(client_version))

        device_id = None
        try:
            sett_path = Path.cwd() / self.settings_filename
            settings_file = str(sett_path.absolute())
            if not path.isfile(settings_file):
                # settings file does not exist
                print('Unable to find file: {0!s}'.format(settings_file))

                # login new
                self.api = Client(
                    self.username, self.password,
                    on_login=lambda x: onlogin_callback(x, settings_file), auto_patch=True)
            else:
                with open(settings_file) as file_data:
                    cached_settings = json.load(file_data, object_hook=from_json)
                print('Reusing settings: {0!s}'.format(settings_file))

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
                on_login=lambda x: onlogin_callback(x, settings_file), auto_patch=True)

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
        cookie_expiry = self.api.cookie_jar.auth_expires
        print('Cookie Expiry: {0!s}'.format(
            datetime.datetime.fromtimestamp(cookie_expiry).strftime('%Y-%m-%dT%H:%M:%SZ')))

    def fetch_following(self, target_account, all_=False):
        """Grabs target account's following."""
        # Get user_id and rank token
        result = self.api.username_info(target_account)
        user_id = result["user"]["pk"]
        rank_token = self.api.generate_uuid()

        users = []
        if all_:
            results = self.api.user_following(user_id, rank_token)

            users.extend(results.get('users', []))

            next_max_id = results.get('next_max_id')

            while next_max_id:
                timeout()
                results = self.api.user_following(user_id, rank_token=rank_token, max_id=next_max_id)

                users.extend(results.get('users', []))

                next_max_id = results.get('next_max_id')

            return users

    def get_user_id(self, username):
        try:
            result = self.api.username_info(username)
            user_id = result["user"]["pk"]
        except ClientError as e:
            print(e)
        except KeyError:
            pass
        else:
            return user_id

    def fetch_followers(self, target_account, all_=False):
        """Grabs followers from target account."""
        # Get user_id and rank token
        user_id = self.get_user_id(target_account)
        rank_token = self.api.generate_uuid()

        users = []

        if all_:
            results = self.api.user_followers(user_id, rank_token=rank_token)

            for user in results.get('users', []):
                users.append(user)

            next_max_id = results.get('next_max_id')

            while next_max_id:
                timeout()
                results = self.api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)

                for user in results.get('users', []):
                    if user not in users:
                        users.append(user)

                next_max_id = results.get('next_max_id')

            return users

        else:
            results = self.api.user_followers(user_id, rank_token=rank_token)

            for user in results.get('users', []):
                if self.follow_conditions(user):
                    users.append(user)

            next_max_id = results.get('next_max_id')

            while next_max_id and len(users) < ACTIONS_LIMIT:
                timeout()
                results = self.api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)

                for user in results.get('users', []):
                    if self.follow_conditions(user) and user not in users:
                        users.append(user)

                next_max_id = results.get('next_max_id')

            return users[:ACTIONS_LIMIT]

    def follow_user(self, username):
        """Follow IG User by username."""
        if type(username) == int:
            user_id = username
        else:
            # Get user_id
            user_id = self.get_user_id(username)

        # Follow by user_id
        r = self.api.friendships_create(user_id)
        if r["status"] == "ok":
            # print(f"[IG] Followed {username}.")
            return True
        else:
            print(r)
            return False

    def unfollow_user(self, username):
        """Unfollow IG User by username."""
        if type(username) == int:
            user_id = username
        else:
            # Get user_id
            user_id = self.get_user_id(username)

        # Unfollow by user_id
        r = self.api.friendships_destroy(user_id)
        if r["status"] == "ok":
            print(f"[IG] Unfollowed {username}.")
            return True
        else:
            print(r)
            return False

    def fetch_posts(self, username, max_posts=12, step=1):
        """Fetch User's posts."""
        if type(username) == int:
            user_id = username
        else:
            # Get user_id
            user_id = self.get_user_id(username)

        # Fetch Posts
        posts = []
        if not len(posts) > max_posts:

            results = self.api.user_feed(user_id)
            posts.extend(results.get('items', []))
            next_max_id = results.get('next_max_id')
            while next_max_id:
                timeout()

                results = self.api.user_feed(user_id, max_id=next_max_id)
                posts.extend(results.get('items', []))

                if len(posts) > max_posts:  # get only first 12 or so
                    break
                next_max_id = results.get('next_max_id')

        return posts[:max_posts:step]

    # TODO not fully functional yet
    def fetch_user_saved(self, max_posts=12, _all=False):
        """Fetch self.user's saved feed."""
        # Fetch Posts
        posts = []

        results = self.api.saved_feed()
        posts.extend([item["media"] for item in results.get("items", [])])
        next_max_id = results.get('next_max_id')

        if _all:
            while next_max_id:
                timeout()
                results = self.api.saved_feed(max_id=next_max_id)
                posts.extend([item["media"] for item in results.get("items", [])])
                next_max_id = results.get('next_max_id')

            return posts

        else:
            if len(posts) < max_posts:
                while next_max_id:
                    timeout()
                    results = self.api.saved_feed(max_id=next_max_id)
                    posts.extend([item["media"] for item in results.get("items", [])])

                    if len(posts) > max_posts:
                        break
                    next_max_id = results.get('next_max_id')

            return posts[:max_posts]

    def follow_conditions(self, account):
        """Checks against conditions in order to follow the account."""

        # Account can't be private
        if account["is_private"]:
            return False
        # Account can't have anonymous profile picture
        elif account["has_anonymous_profile_picture"]:
            return False
        # Account was interacted with in the past already
        elif account["username"] in self.to_ignore:
            return False
        else:
            return True


if __name__ == "__main__":
    ig = Instagram()
