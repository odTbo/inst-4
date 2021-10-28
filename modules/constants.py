from random import choice
from datetime import datetime

# Follow/Unfollow actions limit
<<<<<<< HEAD
ACTIONS_LIMIT = choice(range(2,4))
=======
ACTIONS_LIMIT = choice(range(12, 20))
>>>>>>> d283186aed59ee01335ba1c9ec634e5ec06163d6

# Approximate follows per day
FOLLOWS_PER_DAY = 70

# Profile scraper output dir
SCRAPER_OUTPUT = "Scraper Output"

# Date today
DATETIME_TODAY = datetime.now()
DATE_STR = DATETIME_TODAY.strftime("%d-%m-%Y")