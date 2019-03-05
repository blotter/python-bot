import time
import sys
import re
import locale
import os

from distutils.util import strtobool

locale.setlocale(locale.LC_TIME, "de_DE")

class trigger:
    def trigger_notice(self):
        if self.hostname == 'NickServ!NickServ@services.':
            if self.nickserv_replay:
                self.nickserv_replay = False
                self.send_message('NICKSERV: {}'.format(self.content))

    def trigger_ctcp(self):
        if self.content.find('\x01ACTION') == 0 and re.search('\x01$', self.content, re.IGNORECASE):
            self.send_notice('\x01ACTION {}\x01'.format(' '.join(str(i) for i in self.content.replace('\x01', '').split()[1:])), self.user)

        if self.content.find('\x01VERSION\x01') == 0:
            self.send_notice('\x01VERSION {}:{}:{}\x01'.format(self.nick, self.version, os.uname()[0]), self.user)

        if self.content.find('\x01TIME\x01') == 0:
            self.send_notice('\x01TIME {}\x01'.format(time.strftime("%A, %d. %B %Y %H:%M:%S %Z")), self.user)

        if self.content.find('\x01USERINFO\x01') == 0:
            self.send_notice('\x01USERINFO Ich bin ein automatisch denkendes Wesen, auch bekannt als Bot!\x01', self.user)

        if self.content.find('\x01CLIENTINFO\x01') == 0:
            self.send_notice('\x01CLIENTINFP ACTION CLIENTINFO FINGER PING SOURCE TIME URL USERINFO VERSION\x01', self.user)

        if self.content.find('\x01URL\x01') == 0:
            self.send_notice('\x01URL Frag den janus im freenode\x01', self.user)

        if self.content.find('\x01SOURCE\x01') == 0:
            self.send_notice('\x01SOURCE Frag den janus im freenode\x01', self.user)

        if self.content.find('\x01PING') == 0 and re.search('\x01$', self.content, re.IGNORECASE):
            if len(self.content.split()) > 1:
                self.send_notice('\x01PING {}\x01'.format(' '.join(str(i) for i in self.content.replace('\x01', '').split()[1:])), self.user)

        if self.content.find('\x01FINGER\x01') == 0:
            self.send_notice('\x01FINGER Du nicht nehmen Kerze! You don\'t take candle!\x01', self.user)

    def trigger_config(self):
        split_content = self.content.split()
        if self.content.find('debug') == 7:
            if len(split_content) == 2:
                self.send_message("Debug: {}".format("AN" if self.DEBUG else "AUS"))
            elif len(split_content) >= 3:
                try:
                    self.DEBUG = bool(strtobool(split_content[2]))
                    self.send_message("Debug: {}".format("AN" if self.DEBUG else "AUS"))
                except ValueError as Error:
                    self.send_message("Debug: {}".format(Error))

        if self.content.find('ping') == 7:
            if len(split_content) == 2:
                self.send_message("PING: {}".format("AN" if self.use_ping else "AUS"))
            elif len(split_content) >= 3:
                try:
                    self.use_ping = bool(strtobool(split_content[2]))
                    self.send_message("PING: {}".format("AN" if self.use_ping else "AUS"))
                except ValueError as Error:
                    self.send_message("PING: {}".format(Error))

        if self.content.find('join') == 7:
            if len(split_content) == 3 and split_content[2].startswith('#'):
                self.post_string('JOIN {}\n'.format(split_content[2]))
                self.channels.append(split_content[2])

        if self.content.find('part') == 7:
            if len(split_content) == 3 and split_content[2].startswith('#'):
                self.post_string('PART {}\n'.format(split_content[2]))
                self.channels.remove(split_content[2])

        if self.content.find('channel') == 7:
            if len(split_content) == 2:
                if len(self.channels) > 0:
                    self.send_message('Ich bin in {}.'.format(', '.join(self.channels)), self.target)

        if self.content.find('reconnect') == 7:
            if len(split_content) == 2:
                self.stop_loop()
                self.reconnect()

    def trigger_nickserv(self):
        content = self.content.split()
        print(content[1])
        if content[1] == "register":
            self.send_message('REGISTER {} {}.freenode@jhor.de'.format(self.passwort, self.nick), 'NICKSERV')

        if content[1] == "verify":
            self.send_message('VERIFY REGISTER {} {}'.format(self.nick, content[2]), 'NICKSERV')

        if content[1] == "identify":
            self.send_message('IDENTIFY {} {}'.format(self.nick, self.passwort), 'NICKSERV')

        if content[1] == "status":
            self.nickserv_replay = True
            self.send_message('STATUS', 'NICKSERV')

    def trigger_privmsg(self):
        if self.hostname == self.admin:
            if re.search('^nickserv', self.content, re.IGNORECASE):
                print('trigger_nickserv')
                self.trigger_nickserv()
            if re.search('^config', self.content, re.IGNORECASE):
                print('trigger_config')
                print('Content: {}\nCommand: {}\nTarget: {}\n'.format(self.content, self.command, self.target))
                self.trigger_config()

        if self.content.find('{}hello'.format(self.trigger)) == 0 \
                or self.content.find('{}hallo'.format(self.trigger)) == 0 \
                or re.search('^hello', self.content, re.IGNORECASE) \
                or re.search('^hallo', self.content, re.IGNORECASE):
            self.send_message('Hallo {}'.format(self.user))

        if self.content.find('{}ping'.format(self.trigger)) == 0 \
                or re.search('^ping {}'.format(self.nick), self.content, re.IGNORECASE):
            self.send_message('pong {}'.format(self.user))

