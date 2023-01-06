import tweepy
from .credentials import twitter
import logging

logger = logging.getLogger(__name__)
MAX_TWEETS_SAVED = 10000


class HashtagStreamListener(tweepy.StreamingClient):

    #def __init__(self, handler):
    #    self.handler = handler
    #    tweepy.Stream.__init__(self)

    def on_tweet(self, status):
        logger.debug("Received tweet: {}".format(status.text))
        self.handler._increment_tweet_counter()
        self.handler._save_tweet(status)

    def on_error(self, status_code):
        logger.warn("Error with status code: {}".format(status_code))

    def on_connect(self):
        logger.info("Connected to stream.")

    def on_exception(self, e):
        logger.error("Unhandled exception: {}".format(e))


class TwitterClient:

    def __init__(self, tags=[]):
        self.tags = tags
        self.curr_tweets = 0
        self.tweets = []

    def num_tweets(self):
        """
        Returns current number of tweets on the counter and resets internal
        counter
        """
        t = self.curr_tweets
        logger.info("Reporting received {} tweets.".format(t))
        self.curr_tweets = 0
        return t

    def get_tweets(self):
        """
        Returns list of buffered tweets
        Resets buffer after returning result
        """
        t = self.tweets
        self.tweets = []
        return t

    def start(self):
        self._setup_stream()

    def _setup_stream(self):
        logger.info("Starting twitter steam")

        s_listener = HashtagStreamListener(self)
        stream = tweepy.StreamingClient(bearer_token=twitter["bearer_token"], listener=s_listener)
        stream.filter(track=self.tags, is_async=True)

    def _increment_tweet_counter(self):
        self.curr_tweets += 1

    def _save_tweet(self, tweet):
        if len(self.tweets) < MAX_TWEETS_SAVED:
            self.tweets.append(tweet)
