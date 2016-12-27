import credentials
import settings
import irc.client
import requests
import logging
logger = logging.getLogger(__name__)


class TwitchClient(irc.client.SimpleIRCClient):
    def __init__(self):
        self._message_count = 0
        self._emote_count = 0
        self._channel_id = None
        irc.client.SimpleIRCClient.__init__(self)

    def connect(self):
        self._emotes = self._get_emote_list()
        irc.client.SimpleIRCClient.connect(
            self, settings.twitch_host, settings.twitch_port,
            nickname=credentials.twitch['nick'],
            password=credentials.twitch['oauth'])
        self.connection.join(self._to_irc_chan(settings.twitch_channel))

    def process(self):
        """
        Needed if not using TwitchClient as the main event loop carrier.
        Allows the IRC client to process new data / events.
        Should be called regularly to allow PINGs to be responded to
        """
        self.reactor.process_once()

    def _to_irc_chan(self, chan):
        return chan if chan.startswith('#') else '#' + chan

    def _to_url_chan(self, chan):
        return chan[1:] if chan.startswith('#') else chan

    def _get_channel_id(self, chan):
        """ Gets the numeric channel id of a channel by displayname """
        if not self._channel_id:
            headers = {
                "Accept": "application/vnd.twitchtv.v5+json",
                "Client-ID": credentials.twitch['clientid'],
            }
            r = requests.get('https://api.twitch.tv/kraken/users',
                             headers=headers,
                             params={
                                "login": chan
                             })
            self._channel_id = r.json()['users'][0]['_id']
        return self._channel_id

    def _get_emote_list(self):
        r = requests.get("https://api.twitch.tv/kraken/chat/emoticon_images")
        return set(map(lambda x: x['code'], r.json()['emoticons']))

    def _num_emotes(self, s):
        return sum(1 for w in s.split(' ') if w in self._emotes)

    def on_join(self, c, e):
        logger.info("Connected to %s" % e.target)

    def get_message_count(self):
        t = self._message_count
        self._message_count = 0
        return t

    def get_emote_count(self):
        t = self._emote_count
        self._emote_count = 0
        return t

    def on_pubmsg(self, connection, event):
        msg = event.arguments[0]
        logger.debug(msg + "; {} emotes".format(self._num_emotes(msg)))
        self._message_count += 1
        self._emote_count += self._num_emotes(msg)

    def on_disconnect(self, connection, event):
        # TODO: Setup reconnection
        pass

    def get_num_viewers(self):
        """ Queries the TwitchAPI for current number of viewers of channel """
        headers = {
            "Accept": "application/vnd.twitchtv.v5+json",
            "Client-ID": credentials.twitch['clientid'],
        }
        url = "https://api.twitch.tv/kraken/streams/"
        url += self._get_channel_id(self._to_url_chan(settings.twitch_channel))
        req = requests.get(url, headers=headers)
        res = req.json()
        if 'stream' in res and res['stream']:
            return res['stream']['viewers']


if __name__ == '__main__':
    t = TwitchClient()
    print t.get_num_viewers()
