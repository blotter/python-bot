import json
import threading
import config
from irc import IrcConnection

irc = None

def worker():
    irc.loop()

irc = IrcConnection(server=config.IRC_SERV, channel=config.IRC_CHAN, \
        nick=config.IRC_NICK, port=config.IRC_PORT, passwort=config.IRC_PASS)

t = threading.Thread(target=worker)
t.start()
