import dload
# from concurrent.futures import ThreadPoolExecutor
from progressbar import ProgressBar, Bar, Percentage
from modules.constants import SCRAPER_OUTPUT
from pathlib import Path


def progressbar(max_val):
    bar = ProgressBar(
        maxval=max_val,
        widgets=[Bar('=', '[', ']'), ' ', Percentage()]
    )
    return bar


class ProfileScraperMixin:
    """Holds functions for scraping an IG user posts."""
    def extract_urls(self, posts):
        """Extracts URLs from instagram user's posts"""
        urls = []
        for post in posts:
            try:
                carousel = post["carousel_media"]
            except KeyError:
                # Single item post
                if post["media_type"] == 2:
                    urls.append(post["video_versions"][0]["url"])
                else:
                    urls.append(post["image_versions2"]["candidates"][0]["url"])
            else:
                # Carousel post
                for media in carousel:
                    if media["media_type"] == 2:
                        urls.append(media["video_versions"][0]["url"])
                    else:
                        urls.append(media["image_versions2"]["candidates"][0]["url"])
        return urls

    def empty_a_file(self, filename="to_scrape.txt"):
        """Truncates a file."""
        path = Path().cwd() / filename
        if path.exists():
            with open(filename, "w") as f:
                f.truncate(0)

    def users_to_scrape(self, filename="to_scrape.txt"):
        """Grabs all usernames from a scrape file and returns them as a list."""
        path = Path().cwd() / filename
        if path.exists():
            with path.open(mode="r") as f:
                users = [line.strip() for line in f.readlines()]

            self.empty_a_file()
            return users
        else:
            print(f"The file '{filename}' doesn't exist.")
            return None

    def output_dir(self, username):
        path = Path().cwd() / SCRAPER_OUTPUT
        if path.exists():
            pass
        else:
            path.mkdir()

        path = path / username
        if path.exists():
            pass
        else:
            path.mkdir()

    def dwnld_imgs(self, username, links):
        self.output_dir(username)

        pbar = progressbar(len(links))

        def download_image(link):
            filename = link.split("?")[0].split("/")[-1]
            path = Path().cwd() / SCRAPER_OUTPUT / username / filename
            dload.save(url=link,
                       path=str(path.absolute()),
                       overwrite=False)
        progress = 0
        pbar.start()
        for url in pbar(links):
            download_image(url)
            progress += 1
            pbar.update(progress)
        pbar.finish()

        # with ThreadPoolExecutor() as exector:
        #     exector.map(download_image, links)


if __name__ == "__main__":
    scraper = ProfileScraperMixin()
