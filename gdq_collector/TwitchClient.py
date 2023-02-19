from . import settings, credentials
import irc.client
import requests
import logging
from time import sleep
from datetime import datetime

logger = logging.getLogger(__name__)
MAX_CHATS_SAVED = 100000


class TwitchClient(irc.client.SimpleIRCClient):

    def __init__(self, twitch_channel):
        self._message_count = 0
        self._channel_id = None
        self._chats = []
        self._exponential_backoff = 0
        irc.client.SimpleIRCClient.__init__(self)
        self.twitch_channel = twitch_channel

    def connect(self):
        if self._exponential_backoff > 0:
            logger.info(
                "Backing off on IRC join for {} sec".format(
                    self._exponential_backoff
                )
            )
            sleep(self._exponential_backoff)
            self._exponential_backoff *= 2
        else:
            self._exponential_backoff = 1

        logger.info("Attempting to connect to IRC server.")
        irc.client.SimpleIRCClient.connect(
            self,
            settings.TWITCH_HOST,
            settings.TWITCH_PORT,
            nickname=credentials.twitch["nick"],
            password=credentials.twitch["oauth"],
        )
        logger.info("Connected to IRC server: %s" % settings.TWITCH_HOST)
        self.connection.join(self._to_irc_chan(self.twitch_channel))

    def process(self):
        """
        Needed if not using TwitchClient as the main event loop carrier.
        Allows the IRC client to process new data / events.
        Should be called regularly to allow PINGs to be responded to
        """
        self.reactor.process_once()

    def _to_irc_chan(self, chan):
        return chan if chan.startswith("#") else "#" + chan

    def _to_url_chan(self, chan):
        return chan[1:] if chan.startswith("#") else chan

    def on_join(self, c, e):
        logger.info("Joined channel: %s" % e.target)

        # Reset exponential backoff on successful join
        self._exponential_backoff = 0

    def get_message_count(self):
        """
        Returns the current number of counted chat messages
        """
        t = self._message_count
        self._message_count = 0
        return t

    def get_chats(self):
        c = self._chats
        self._chats = []
        return c

    def on_pubmsg(self, connection, event):
        msg = event.arguments[0]
        self._message_count += 1

        if len(self._chats) < MAX_CHATS_SAVED:
            try:
                self._chats.append(
                    {
                        "user": event.source.split("!")[0],
                        "content": msg,
                        "created_at": datetime.utcnow(),
                    }
                )
            except Exception as e:
                logger.error("Error appending message: {}".format(e))

    def on_disconnect(self, connection, event):
        logger.error("Disconnected from twitch chat. Attempting reconnection")
        self.connect()

    def get_num_viewers(self):
        """ Queries the TwitchAPI for current number of viewers of channel """
        headers = {
            "Authorization": "Bearer " + credentials.twitch["app_access_token"],
            "Client-ID": credentials.twitch["clientid"],
        }

        req = requests.get(
            "https://api.twitch.tv/helix/streams",
            headers=headers,
            params={"user_login": self._to_url_chan(self.twitch_channel)},
        )

        data = req.json()
        if "data" in data and len(data["data"]) == 1:
            viewers = data["data"][0]["viewer_count"]

            logger.info(
                "Downloaded viewer info. " "Number of current viewers: %s" % viewers
            )
        
            return viewers

        else:
            logger.warn(
                "Unable to get number of viewers. "
                "Possible that stream is offline. "
                "Status code: {}".format(req.status_code)
            )


if __name__ == "__main__":
    t = TwitchClient()
    print(t.get_num_viewers())
