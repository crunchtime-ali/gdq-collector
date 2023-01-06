import tweepy
from .credentials import twitter
import logging

logger = logging.getLogger(__name__)
MAX_TWEETS_SAVED = 10000


class HashtagStreamListener(tweepy.StreamingClient):

    def __init__(self, handler, bearer_token):
        self.handler = handler
        tweepy.StreamingClient.__init__(self, bearer_token)

    def on_tweet(self, status):
        logger.info("Received tweet: {}".format(status.text))
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

        stream = HashtagStreamListener(self,bearer_token=twitter["bearer_token"])

        # Reset rules
        ruleList = []
        rules = stream.get_rules()
 
        if rules.data != None and len(rules.data) > 0:
            for rule in rules.data:
                ruleList.append(rule.id)
            stream.delete_rules(ruleList)
        
        stream.delete_rules(ruleList)

        # Add new rules
        stream.add_rules(tweepy.StreamRule(' OR '.join(self.tags)))
        rules = stream.get_rules()
        logger.info("current rules:")
        logger.info(rules)
        thread = stream.filter(threaded=True)

    def _increment_tweet_counter(self):
        self.curr_tweets += 1

    def _save_tweet(self, tweet):
        if len(self.tweets) < MAX_TWEETS_SAVED:
            self.tweets.append(tweet)
