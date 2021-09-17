from datetime import datetime
from os import remove
import glob
import json
from pathlib import Path
from modules.constants import DATE_STR, DATETIME_TODAY

# Logs dir path
LOGS_PATH = Path().cwd() / "logs"


class LogsManager:
    """Class responsible for manipulating usernames and session logs/errors locally."""
    expired_list = ""

    def export_username(self, username,
                        unfollow=False,
                        ignore=False,
                        scrape=False):
        """Saves followed user to unfollow list and to ignore list, to prevent future interaction with the account."""

        # Save to unfollow list
        if unfollow:
            path = LOGS_PATH / f"{DATE_STR}.txt"
            with path.open(mode="a") as f:
                f.write(f"{username}\n")

        # Save to ignore list
        if ignore:
            path = LOGS_PATH / "to_ignore.txt"
            with path.open(mode="a") as f:
                f.write(f"{username}\n")

        # Save scrape list
        if scrape:
            path = Path.cwd() / "to_scrape.txt"
            with path.open(mode="a") as f:
                f.write(f"{username}\n")

    def export_to_unfollow(self, usernames, filename):
        """Saves remaining usernames (list) waiting for unfollow to the original file."""
        path = LOGS_PATH / filename
        with path.open(mode="w") as f:
            f.write('\n'.join(usernames))
            f.write('\n')

    def expired_lists(self):
        """Checks if there are lists atleast 4 days old to unfollow."""
        date_today = datetime.now()

        # Get all txt files in logs
        path = str(LOGS_PATH.absolute() / "*.txt")
        filenames = [Path(file).name[:-4] for file in glob.glob(path)]
        for date in filenames:

            try:
                fname_date = datetime.strptime(date, "%d-%m-%Y")
            except ValueError:
                pass
            else:
                # Check if the file older than 3 days
                if int((date_today - fname_date).days) >= 3:
                    self.expired_list = f'{fname_date.strftime("%d-%m-%Y")}.txt'
                    print("[IG] Expired list found")

                    return True

        return False

    def fetch_users_from_file(self, filename):
        """Grabs all usernames from a file and returns them as a list."""
        path = LOGS_PATH / filename
        if path.exists():
            with open(path, "r") as f:
                output = [line.strip() for line in f.readlines()]

                return output
        else:
            print(f"The file '{filename}' doesn't exist.")

            return None

    def remove_finished_file(self, filename):
        """Remove empty unfollow list file."""
        path = LOGS_PATH / filename
        if path.exists():
            remove(path)
        else:
            print(f"The file '{filename}' doesn't exist.")

    def log_actions(self, method, actions, **kwargs):
        """Logs the number of instagram actions made in a session.
            **kwargs:
            current_following: (int)
            target_account: (string)
            ...
        """
        date = DATETIME_TODAY.strftime("%d-%m-%YT%H:%M:00")

        logs = {
            "date": date,
            "method": method,
            "actions": {key: value for (key, value) in actions.items() if value != 0}
        }
        if kwargs:
            logs.update(kwargs)
        if len(logs["actions"]) != 0:
            logs = json.dumps(logs)

            path = LOGS_PATH / "actions_log.txt"
            with path.open(mode="a") as f:
                f.write(logs + "\n")

    def log_errors(self, errors):
        """Logs the errors encountered in a session."""
        path = LOGS_PATH / "errors_log.txt"
        formatted = json.dumps(errors)
        if len(errors) != 0:
            if path.exists():
                with path.open(mode="a") as f:
                    f.write(formatted)
                    f.write("\n")
                    # f.write('\n'.join(errors))
                    # f.write('\n')
            # TODO Make error logs file json
            # else:

    def logs_dir_create(self):
        if LOGS_PATH.exists():
            pass
        else:
            LOGS_PATH.mkdir()
            print("Logs directory created.")


if __name__ == "__main__":
    lm = LogsManager()
