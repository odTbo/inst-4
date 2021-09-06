import dload
from concurrent.futures import ThreadPoolExecutor
import pathlib
from os import path, mkdir

CWD = str(pathlib.Path(__file__).parent.absolute())

# output = "output/"


def output_dir(directory):
    if path.exists(directory):
        pass
    else:
        mkdir(directory)


def dwnld_imgs(username, links):
    account_dir = f"{username}/"
    output_dir(account_dir)

    def download_image(link):
        filename = link.split("?")[0].split("/")[-1]

        dload.save(url=link, path=f"{CWD}/" + account_dir + filename, overwrite=False)

    with ThreadPoolExecutor() as exector:
        exector.map(download_image, links)
