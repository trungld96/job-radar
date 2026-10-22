from .base import BaseScraper
from .freelancer import FreelancerScraper
from .guru import GuruScraper
from .hackernews import HackerNewsScraper
from .linkedin import LinkedInScraper
from .peopleperhour import PeoplePerHourScraper
from .reddit import RedditScraper
from .remoteok import RemoteOKScraper
from .remotive import RemotiveScraper
from .threads import ThreadsScraper
from .upwork import UpworkScraper
from .vlance import VlanceScraper
from .weworkremotely import WeWorkRemotelyScraper


ALL_SCRAPERS: dict[str, type[BaseScraper]] = {
    "hackernews": HackerNewsScraper,
    "remoteok": RemoteOKScraper,
    "remotive": RemotiveScraper,
    "weworkremotely": WeWorkRemotelyScraper,
    "reddit": RedditScraper,
    "upwork": UpworkScraper,
    "freelancer": FreelancerScraper,
    "peopleperhour": PeoplePerHourScraper,
    "guru": GuruScraper,
    "linkedin": LinkedInScraper,
    "vlance": VlanceScraper,
    "threads": ThreadsScraper,
}
