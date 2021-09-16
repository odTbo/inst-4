import dload
from concurrent.futures import ThreadPoolExecutor
from modules.constants import SCRAPER_OUTPUT
from pathlib import Path


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

        def download_image(link):
            filename = link.split("?")[0].split("/")[-1]
            path = Path().cwd() / SCRAPER_OUTPUT / username / filename
            dload.save(url=link,
                       path=str(path.absolute()),
                       overwrite=False)
        for url in links:
            download_image(url)
        # with ThreadPoolExecutor() as exector:
        #     exector.map(download_image, links)


if __name__ == "__main__":
    # scraper = ProfileScraperMixin()
    # links = ['https://instagram.fbts3-1.fna.fbcdn.net/v/t51.2885-19/s150x150/229154268_290380529506535_4859749332379506983_n.jpg?_nc_ht=instagram.fbts3-1.fna.fbcdn.net&_nc_ohc=07lo4w7aDhgAX_dIsvN&edm=AKralEIBAAAA&ccb=7-4&oh=302d58c3c2e0b9ba46bbad7fc7bc9954&oe=6146B67F&_nc_sid=5e3072']
    # scraper.dwnld_imgs("itxx.rm", links)
    pass