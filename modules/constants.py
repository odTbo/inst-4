from random import choice
from datetime import datetime

# Follow/Unfollow actions limit
ACTIONS_LIMIT = choice(range(10, 15))

# Profile scraper output dir
SCRAPER_OUTPUT = "Scraper Output"

# Date today
DATETIME_TODAY = datetime.now()
DATE_STR = DATETIME_TODAY.strftime("%d-%m-%Y")