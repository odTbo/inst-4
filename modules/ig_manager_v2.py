from modules.utils import *
from modules.logs_manager import LogsMixin
from dotenv import load_dotenv
from modules.constants import *
from pathlib import Path
from instagrapi.types import UserShort
import datetime
from os import path, getenv
from instagrapi import Client

try:
    from modules.device_info import UserSettings
except ImportError:
    UserSettings = None
    pass

load_dotenv()


class Instagram(LogsMixin):
    def __init__(self):
        self.username = getenv("IG_USERNAME")
        self.password = getenv("IG_PASSWORD")
        # self.target_account = getenv("TARGET_ACCOUNT")
        self.settings_filename = "ig_credentials.json"
        self.ignored_users = self.to_ignore()
        self.users = []
        self.my_followers = set()
        # self.__login()

    def login(self):
        """Establishes connection to Instagram API."""
        # get_settings()	            dict	Return settings dict
        # set_settings(settings: dict)	bool	Set session settings
        # load_settings(path: Path)	    dict	Load session settings from file
        # dump_settings(path: Path)	    bool	Serialize and save session settings to file

        custom_settings = self.custom_settings()

        cached_settings = Path().cwd().parent / "cached_settings.json"

        # if saved settings, login with saved settings
        if cached_settings.exists():
            print("Reusing cached settings.")
            self.api = Client()
            self.api.load_settings(cached_settings)

        # else new login and save settings
        else:
            print("New login session.")
            if custom_settings:
                self.api = Client(custom_settings)
                self.api.set_country(UserSettings.COUNTRY)
                self.api.set_locale(UserSettings.LOCALE)
                self.api.set_timezone_offset(UserSettings.TIMEZONE_OFFSET)

            self.api.login(self.username, self.password)

            self.api.dump_settings(cached_settings)

    def to_ignore(self) -> set:
        output = set()
        users = self.fetch_users_from_file("to_ignore.txt")
        for u in users:
            try:
                u = int(u)
            except ValueError:
                pass
            finally:
                output.add(u)

        return output

    def custom_settings(self):
        """Creates custom device settings for client if provided."""
        if UserSettings:
            settings = {
                "user_agent": UserSettings.USER_AGENT,
                "device_settings": {
                    "cpu": UserSettings.PHONE_CHIPSET,
                    "dpi": UserSettings.PHONE_DPI,
                    "model": UserSettings.PHONE_MODEL,
                    "device": UserSettings.PHONE_DEVICE,
                    "resolution": UserSettings.PHONE_RESOLUTION,
                    "app_version": UserSettings.APP_VERSION,
                    "manufacturer": UserSettings.PHONE_MANUFACTURER,
                    "version_code": UserSettings.VERSION_CODE,
                    "android_release": UserSettings.ANDROID_RELEASE,
                    "android_version": UserSettings.ANDROID_VERSION
                }
            }
            return settings
        return None

    def fetch_following(self, target_account: str, all_=False) -> list:
        """Grabs target account's following."""

    # LEGACY
    def get_user_id(self, username: str) -> int:
        """
        OBSOLETE
        use 'api.user_id_from_username()'
        """
        # self.api.user_id_from_username()
        pass

    def fetch_followers(self, user_id: int, all_=False, amount: int = 80) -> list:
        """
        Grabs followers from target account.

        Parameters
        ------
        user_id: int
            User id of an instagram account.
        all_: bool
            True to fetch all followers.
        amount: int
            Specify the amount of followers you want to fetch.

        Returns
        ------
        List[UserShort]
            List of objects of User type
        """
        if all_:
            r = self.api.user_followers_v1_chunk(user_id)
            users = r[0]  # List of users from tuple
            print(len(users))
            return users

        # Get first batch of users
        selected_users = []
        max_id = ""
        while len(selected_users) < amount or all_:
            r = self.api.user_followers_v1_chunk(user_id, max_amount=100, max_id=max_id)
            users = r[0] # List of users from tuple
            num_users = len(users)

            max_id = r[1] # result's max_id from tuple

            # assert len(users) != 0, "Didn't find any followers"

            for u in users:
                if u not in selected_users and (self.follow_conditions(u) or all_):
                    selected_users.append(u)

                if len(selected_users) == amount and not all_:
                    return selected_users
            num_selected_users = len(selected_users)
            print(num_users, num_selected_users)

            if not max_id:
                return selected_users

    def follow_user(self, user_id: int) -> None:
        """Follow IG User by username."""

    def unfollow_user(self, user_id: int) -> bool:
        """Unfollow IG User by username."""

    def fetch_posts(self, user_id: int, max_posts=12, step=1):
        """Fetch User's posts."""
        media = self.api.user_medias(user_id=user_id, amount=max_posts)

        return media[::step]

    # TODO not fully functional yet
    def fetch_user_saved(self, max_posts=12, all_=False) -> list:
        """Fetch self.user's saved feed."""

    def follow_conditions(self, account: UserShort) -> bool:
        """Checks against conditions in order to follow the account."""

        if account.is_private:
            return False
        # elif account["has_anonymous_profile_picture"]:
        #     return False

        # Account was interacted with in the past already
        elif account.username in self.ignored_users or account.pk in self.ignored_users:
            return False
        else:
            return True


if __name__ == "__main__":
    ig = Instagram()
    ig.login()
    # user_id = ig.api.user_id_from_username("username")

    # users = ig.fetch_followers(user_id, all_=True)
    #
    # for u in users:
    #     assert not u.is_private, "PRIVATE ACCOUNT: ".format(u)
    # print("All: " + str(len(users)))
    # print(users)


    # # print("x-bloks-version-id: ", ig.api.bloks_versioning_id)
    #
    # user_id = ig.api.user_id_from_username("soulhoe")
    #
    # users = ig.fetch_followers(user_id)
    # print(users)
    # print(ig.ignored_users)
