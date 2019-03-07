import select
import time
import sys
import socket
import threading
import re
import locale
import ssl
import base64

from colors import colorize
from trigger import trigger
from config import config

locale.setlocale(locale.LC_TIME, "de_DE")

class IrcConnection(trigger, config):
    def __init__(self, configfile):
        self.configfile = configfile
        self.config = self.read()
        self.widelands = self.config._sections
        self.widelands['server']['ssl'] = self.config.getboolean('server', 'ssl')
        self.widelands['server']['sasl'] = self.config.getboolean('server', 'sasl')
        self.widelands['server']['port'] = self.config.getint('server', 'port')
        self.widelands['server']['retry'] = self.config.getint('server', 'retry')
        self.widelands['nickserv']['replay'] = self.config.getboolean('nickserv', 'replay')
        self.widelands['admin']['debug'] = self.config.getboolean('admin', 'debug')
        self.widelands['ping']['interval'] = self.config.getint('ping', 'interval')
        self.widelands['ping']['timeout'] = self.config.getint('ping', 'timeout')
        self.widelands['ping']['pending'] = self.config.getboolean('ping', 'pending')
        self.widelands['ping']['use'] = self.config.getboolean('ping', 'use')
        if ',' in self.widelands['channel']['liste']:
            self.channels = self.widelands['channel']['liste'].split(', ')

        self.command_list = '001 002 003 004 005 250 251 252 253 254 255 265 266 372 375 376 404'
        self.version = "v0.3.3"
        self.connection = None
        self.buffer = ""
        self.last_ping = 0
        self.last_pong = 0
        self.start_time = 0
        self.queue = []
        self.lock = threading.Lock()
        self.quit_loop = False
        self.trigger = "{}, ".format(self.widelands['nickserv']['username'])
        self.time_format = "%d.%m.%Y %H:%M:%S"

    def connect_server(self):
        print(colorize("Connecting to {}:{}".format(self.widelands['server']['server'],
            self.widelands['server']['port']), 'brown', 'shell'))

        while not self.connection:
            try:
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if self.widelands['server']['ssl']:
                    self.connection = ssl.wrap_socket(self.connection,
                            do_handshake_on_connect=True,
                            suppress_ragged_eofs=True)
                self.connection.connect((self.widelands['server']['server'], 
                    self.widelands['server']['port']))
            except socket.gaierror:
                print(colorize("Couldn't resolve server, check your internet connection." \
                       " Re-attempting in 60 seconds.", 'red', 'shell'))
                self.connection = None
                time.sleep(self.widelands['server']['retry'])

        self.last_ping = time.time()
        self.start_time = time.time()
        self.process_input()

        if self.widelands['server']['sasl'] and self.widelands['server']['ssl']:
            self.post_string('CAP LS 302\n')

        if not self.widelands['server']['sasl'] and self.widelands['server']['ssl']:
            self.post_string('PASS {}:{}\n'.format(self.widelands['nickserv']['username'],
                self.widelands['nickserv']['password']))

        self.post_string('NICK {}\n'.format(self.widelands['nickserv']['username']))
        self.post_string('USER {} {} {} :{}\n'.format(self.widelands['nickserv']['username'], 
            '0', '*', self.widelands['server']['realname']))

        if self.widelands['server']['sasl'] and self.widelands['server']['ssl']:
            self.post_string('CAP REQ :sasl\n')

    def reconnect(self):
        self.connection.shutdown(2)
        self.connection.close()
        self.connection = None
        self.connect_server()

    def try_ping(self):
        if self.widelands['admin']['debug']:
            print('try_ping: {}'.format(time.time()))
        if self.widelands['ping']['use']:
            self.post_string('PING {}\n'.format(self.widelands['server']['server']))
            self.update('ping', 'pending', True)
        else:
            self.last_pong = time.time()
            self.update('ping', 'pending', False)

    def schedule_message(self, message):
        self.lock.acquire()
        try:
            self.queue.append(message)
        finally:
            self.lock.release()

    def format_content(self, line):
        if self.widelands['admin']['debug']:
            print("format_content_1: {}".format(line))
        if line.startswith(':'):
            source, line = line[1:].split(' ', 1)
        else:
            source = None
        search = re.compile(r'([^!]*)!?([^@]*)@?(.*)')
        match = search.match(source or '')
        self.hostname = source
        self.name, self.user, self.host = match.groups()
        if not self.host and not self.user:
            if self.name.find('.') >= 0:
                self.host = self.name
                self.name = ''

        if ' :' in line:
            arguments, text = line.split(' :', 1)
        else:
            arguments, text = line, ''
        arguments = arguments.split()

        if len(arguments) == 0:
            self.command = None
            self.target = None
        elif len(arguments) == 1:
            self.command = arguments[0]
            self.target = None
        elif len(arguments) == 2:
            self.command = arguments[0]
            self.target = arguments[1]
        else:
            try:
                self.command = arguments[0]
                self.target = ' '.join(str(i) for i in arguments[1:])
            except:
                print("format_content_3: {}:{}".format(len(arguments), arguments))

        self.content = text
        if self.widelands['admin']['debug'] and not self.command in self.command_list:
            print("""format_content_2: hostname: {}
                  name:     {}
                  user:     {}
                  host:     {}
                  command:  {}
                  target:   {}
                  content:  {}""".format(self.hostname
                            , self.name
                            , self.user
                            , self.host
                            , self.command
                            , self.target
                            , self.content))

    def process_line(self, line):
        if len(line) > 0:
            line = line.replace('\n', '')
            line = line.replace('\r', '')
            self.format_content(line)
            if self.widelands['server']['sasl'] and self.widelands['server']['ssl']:
                if self.command == 'CAP' and self.target == '{} ACK'.format(self.widelands['nickserv']['username']):
                    self.post_string('AUTHENTICATE PLAIN\n')

                if self.command == 'AUTHENTICATE' and self.target == '+':
                    auth = '{benutzer}\0{benutzer}\0{passwort}'.format(
                                    benutzer=self.widelands['nickserv']['username'],
                                    passwort=self.widelands['nickserv']['password'])
                    self.post_string('AUTHENTICATE {}\n'.format(
                                    base64.b64encode(auth.encode('utf8')).decode('utf8')))

                if self.command == '903' and self.target == self.widelands['nickserv']['username']:
                    self.post_string('CAP END\n')

                if self.command == '908':
                    self.update('server', 'sasl', False)
                    self.reconnect()

            if self.command == '376':
                if len(self.channels) > 0:
                    for channel in self.channels:
                        self.post_string('JOIN {}\n'.format(channel))
                self.post_string('MODE {} +iw\n'.format(self.widelands['nickserv']['username']))
                self.send_notice(colorize('IRC bot initialized successfully', 'green', 'irc'))

            if self.command == 'PING':
                self.post_string('PONG {}\n'.format(self.content))
                self.last_ping = time.time()

            if self.command == 'PONG':
                self.last_ping = time.time()
                self.last_pong = time.time()
                self.update('ping', 'pending', False)

            if self.command == 'KICK' and self.target.split()[1] == self.nick:
                self.post_string('JOIN {}\n'.format(self.target.split()[0]))

            if re.search('^\x01', self.content) and re.search('\x01$', self.content):
                self.trigger_ctcp()

            if self.command == 'PRIVMSG' and not re.search('\x01$', self.content):
                self.trigger_privmsg()

            if self.command == 'NOTICE' and not re.search('\x01$', self.content):
                self.trigger_notice()

            if self.start_time + 2 < time.time():
                if self.command != "PONG":
                    if not self.widelands['admin']['debug'] and self.command not in self.command_list :
                        print("Hostname: {}\nCommand: {}\nTarget: {}\nMessage: {}".format(self.hostname, self.command, self.target, self.content))

                if self.widelands['admin']['debug'] and self.command not in self.command_list:
                    self.send_message(line)

            print('{}: {}'.format(colorize("{} {}".format(time.strftime(self.time_format), self.widelands['server']['server']), 'green', 'shell'), line))


    def process_input(self):
        data = self.connection.recv(4096)
        if not data or data == b'':
            return

        self.buffer += data.decode('utf-8')

        last_line_complete = (self.buffer[-1] == '\n')
        lines = self.buffer.split('\n')
        if last_line_complete: 
            lines += ['']

        for line in lines[:-1]:
            self.process_line(line)

        self.buffer = self.buffer[-1]

    def post_string(self, message):
        print(colorize('{} {}> {}'.format(time.strftime(self.time_format), self.widelands['nickserv']['username'], message[:-1]), 'blue', 'shell'))
        self.last_ping = time.time()
        self.connection.send(bytes(message, 'utf-8'))

    def send_notice(self, message, target=None):
        if target:
            self.post_string('NOTICE ' + target + ' :' + message + '\n')
        else:
            self.post_string('NOTICE ' + self.widelands['channel']['admin'] + ' :' + message + '\n')

    def send_message(self, message, target=None):
        if target:
            self.post_string('PRIVMSG ' + target + ' :' + message + '\n')
        else:
            self.post_string('PRIVMSG ' + self.widelands['channel']['admin'] + ' :' + message + '\n')

    def stop_loop(self):
        self.quit_loop = True

    def loop(self):
        self.connect_server()
        k = 0
        while not self.quit_loop:
            try:
                to_read, _, _ = select.select([self.connection], [], [], 1)
            except select.error:
                self.reconnect()
                continue

            if self.last_pong + self.widelands['ping']['interval'] < time.time() and not self.widelands['ping']['pending']:
                self.try_ping()

            if self.last_ping + self.widelands['ping']['timeout'] < time.time():
                self.reconnect()
                continue

            if to_read:
                r = self.process_input()

            with self.lock:
                while len(self.queue) > 0:
                    print('loop_try_while: {}'.format(self.queue))
                    self.send_notice(self.queue[0])
                    self.queue = self.queue[1:]

    def __del__(self):
        self.connection.close()
