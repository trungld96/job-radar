from .base import BaseTrendSource
from .producthunt import ProductHuntSource
from .hackernews import HackerNewsFrontSource
from .github_trending import GitHubTrendingSource
from .exploding_topics import ExplodingTopicsSource


ALL_SOURCES: dict[str, type[BaseTrendSource]] = {
    "producthunt": ProductHuntSource,
    "hackernews": HackerNewsFrontSource,
    "github_trending": GitHubTrendingSource,
    "exploding_topics": ExplodingTopicsSource,
}
