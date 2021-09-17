from random import choice
from datetime import datetime

# Follow/Unfollow actions limit
ACTIONS_LIMIT = choice(range(14, 21))

# Approximate follows per day
FOLLOWS_PER_DAY = 80

# Profile scraper output dir
SCRAPER_OUTPUT = "Scraper Output"

# Date today
DATETIME_TODAY = datetime.now()
DATE_STR = DATETIME_TODAY.strftime("%d-%m-%Y")