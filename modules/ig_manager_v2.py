from modules.utils import *
from modules.logs_manager import LogsMixin
from dotenv import load_dotenv
from modules.constants import *
from pathlib import Path
import datetime
from os import path, getenv
from instagrapi import Client

try:
    from modules.device_info import my_settings
except ImportError:
    my_settings = {}

load_dotenv()


class Instagram(LogsMixin):
    def __init__(self):
        self.username = getenv("IG_USERNAME")
        self.password = getenv("IG_PASSWORD")
        # self.target_account = getenv("TARGET_ACCOUNT")
        self.settings_filename = "ig_credentials.json"
        try:
            self.to_ignore = set(self.fetch_users_from_file("to_ignore.txt"))
        except TypeError:
            self.to_ignore = set()
        self.users = []
        self.my_followers = set()
        # self.__login()

    def login(self):
        """Establishes connection to Instagram API."""
        # get_settings()	            dict	Return settings dict
        # set_settings(settings: dict)	bool	Set session settings
        # load_settings(path: Path)	    dict	Load session settings from file
        # dump_settings(path: Path)	    bool	Serialize and save session settings to file

        custom_settings = {
            "cpu": my_settings["phone_chipset"],
            "dpi": my_settings["phone_dpi"],
            "model": my_settings["phone_model"],
            "device": my_settings["phone_device"],
            "resolution": my_settings["phone_resolution"],
            "app_version": my_settings["app_version"],
            "manufacturer": my_settings["phone_manufacturer"],
            "version_code": my_settings["version_code"],
            "android_release": my_settings["android_release"],
            "android_version": my_settings["android_version"]
        }
        settings = {}

        cached_settings = Path().cwd() / "cached_settings.json"

        # if saved settings, login with saved settings
        if cached_settings.exists():
            api = Client()
            api.load_settings(cached_settings)
            api.login(self.username, self.password)

        # else new login and save settings
        else:
            settings["device_settings"] = custom_settings
            settings["user_agent"] = my_settings["user_agent"]

            api = Client(settings)
            api.login(self.username, self.password)

            api.dump_settings(cached_settings)

    def fetch_following(self, target_account: str, all_=False) -> list:
        """Grabs target account's following."""


    def get_user_id(self, username: str) -> int:
        """Username to user_id"""


    def fetch_followers(self, target_account: str, all_=False) -> list:
        """Grabs followers from target account."""


    def follow_user(self, user_id: int) -> None:
        """Follow IG User by username."""


    def unfollow_user(self, user_id: int) -> bool:
        """Unfollow IG User by username."""


    def fetch_posts(self, username, max_posts=12, step=1):
        """Fetch User's posts."""


    # TODO not fully functional yet
    def fetch_user_saved(self, max_posts=12, all_=False) -> list:
        """Fetch self.user's saved feed."""


    def follow_conditions(self, account: dict) -> bool:
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
        elif str(account["pk"]) in self.to_ignore:
            return False
        else:
            return True


if __name__ == "__main__":
    ig = Instagram()
    ig.login()

