import select
import time
import sys
import irccolors
import socket
import threading
import re
import locale
import ssl

from distutils.util import strtobool

PING_INTERVAL = 30
PING_TIMEOUT = PING_INTERVAL + 30 # Must be PING_INTERVAL + actual ping timeout
RETRY_INTERVAL = 60

ansi_colors = {
        'green' : '1;32m',
        'blue'  : '1;34m',
        'red'   : '1;31m',
        'brown' : '0;33m',
        };

locale.setlocale(locale.LC_TIME, "de_DE")

def colorize(line, color):
    if not sys.stdout.isatty():
        return line

    return '\033[' + ansi_colors[color] + line + '\033[0m'

class IrcConnection:
    def __init__(self, server, channel, nick, port, passwort):
        self.server = server
        self.channel = channel
        self.nick = nick
        self.port = port
        self.passwort = passwort
        self.admin = "janus!Janus@bnc.animux.de"

        self.connection = None
        self.buffer = ""
        self.last_ping = 0
        self.start_time = 0
        self.ping_pending = False

        self.queue = []
        self.lock = threading.Lock()
        self.quit_loop = False

        self.DEBUG = False
        self.trigger = "{}, ".format(self.nick)
        self.time_format = "%d.%m.%Y %H:%M:%S"
        self.use_ping = False
        self.nickserv_replay = False

        self.hostname = None
        self.command = None
        self.target = None
        self.content = None
        self.user = None
        self.host = None

    def connect_server(self):
        print(colorize("Connecting to {}:{}".format(self.server, self.port), 'brown'))

        while not self.connection:
            try:
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.connection = ssl.wrap_socket(self.connection)
                self.connection.connect((self.server, self.port))
            except socket.gaierror:
                print(colorize("Couldn't resolve server, check your internet connection." \
                       " Re-attempting in 60 seconds.", 'red'))
                self.connection = None
                time.sleep(RETRY_INTERVAL)

        self.last_ping = time.time()
        self.start_time = time.time()
        self.process_input()

        self.post_string('PASS {}:{}\n'.format(self.nick, self.passwort))
        self.post_string('NICK {}\n'.format(self.nick))
        self.post_string('USER {} {} {} :python BOT\n'.format(self.nick, self.nick, self.nick))
        self.post_string('JOIN {}\n'.format(self.channel))
        self.post_string('MODE {} +iw\n'.format(self.nick))
        self.send_notice(irccolors.colorize('IRC bot initialized successfully', 'green'))

    def reconnect(self):
        self.connection.shutdown(2)
        self.connection.close()
        self.connection = None
        self.connect_server()

    def try_ping(self):
        if self.DEBUG:
            print('try_ping: {}'.format(time.time()))
        if self.use_ping:
            self.post_string('PING {}\n'.format(self.server))
            self.ping_pending = True
        else:
            self.last_ping = time.time()
            self.ping_pending = False

    def schedule_message(self, message):
        self.lock.acquire()
        try:
            self.queue.append(message)
        finally:
            self.lock.release()

    def replace_first_pattern(self, pattern, sub, content):
        if self.DEBUG:
            print("replace_first_pattern: pattern: {} sub: {} content: {}".format(pattern, sub, content))
        return re.sub('^{}'.format(pattern), sub, content)

    def split_content(self, line):
        if self.DEBUG:
            print("split_content_1: {}".format(line))
        #line = line.split()
        #if self.DEBUG:
        #    print("split_content_2: {}".format(line))
        if line.startswith(':'):
            source, line = line[1:].split(' ', 1)
        else:
            source = None

        search = re.compile(r'([^!]*)!?([^@]*)@?(.*)')
        match = search.match(source or '')
        self.hostname = source
        self.name, self.user, self.host = match.groups()

        if ' :' in line:
            arguments, text = line.split(' :', 1)
        else:
            arguments, text = line, ''

        arguments = arguments.split()
        print("#" * 120)
        print("split_content_2: arg: {}-{}; text: {}".format(len(arguments), arguments, text))
        if len(arguments) == 1:
            self.command = arguments[0]
            self.target = None
        elif len(arguments) == 2:
            self.command = arguments[0]
            self.target = arguments[1]
        else:
            self.command = arguments[0]
            self.target = ' '.join(str(i) for i in arguments[1:])
        self.content = text
        """
        if len(line) == 0:
            content = '', '', '', ''
        elif len(line) == 1:
            content = line[0], '', '', ''
        elif len(line) == 2:
            content = line[0], line[1], '', ''
        elif len(line) == 3:
            content = line[0], line[1], line[2], ''
        else:
            content = line[0], line[1], line[2], ' '.join(str(i) for i in line[3:])
        self.hostname, self.command, self.target, self.content = content
        """

    def format_content(self, line):
        if self.DEBUG:
            print("format_content_1: {}".format(line))
        self.split_content(line)
        #self.hostname = self.replace_first_pattern(':', '', self.hostname)
        #self.command = self.replace_first_pattern(':', '', self.command)
        #self.content = self.replace_first_pattern(':', '', self.content)
        #try:
        #    user, host = self.hostname.split('!')
        #    self.user = user
        #    self.host = host
        #except:
        #    self.user = ""
        #    self.host = ""
        if self.DEBUG:
            print("format_content_2: \nhostname: {} \nname: {} \nuser: {} \nhost: {}\ncommand: {}\ntarget {}\ncontent {}\n".format(self.hostname \
                            , self.name \
                            , self.user \
                            , self.host \
                            , self.command \
                            , self.target \
                            , self.content ))

    def trigger_ctcp(self):
        if self.content.find('\x01VERSION\x01') == 0:
            self.send_notice('\x01VERSION Ein Bot in Version 0.1.1\x01', self.user)

        if self.content.find('\x01TIME\x01') == 0:
            self.send_notice('\x01TIME {}\x01'.format(time.strftime("%A, %d. %B %Y %H:%M:%S %Z")), self.user)

        if self.content.find('\x01USERINFO\x01') == 0:
            self.send_notice('\x01USERINFO Ein Bot von janus\x01', self.user)

        if self.content.find('\x01CLIENTINFO\x01') == 0:
            self.send_notice('\x01CLIENTINFP CLIENTINFO PING TIME USERINFO VERSION\x01', self.user)

        if self.content.find('\x01PING') == 0:
            if len(self.content.split()) > 1:
                self.send_notice('\x01PING {}'.format(' '.join(str(i) for i in self.content.split()[1:])), self.user)

    def trigger_privmsg(self):
        if self.hostname == self.admin:
            if re.search('^nickserv', self.content, re.IGNORECASE):
                print('trigger_nickserv')
                self.trigger_nickserv()
            if re.search('^config', self.content, re.IGNORECASE):
                print('trigger_config')
                self.trigger_config()

        if self.content.find('{}hello'.format(self.trigger)) == 0 \
                or self.content.find('{}hallo'.format(self.trigger)) == 0 \
                or re.search('^hello', self.content, re.IGNORECASE) \
                or re.search('^hallo', self.content, re.IGNORECASE):
            self.send_message('Hallo {}'.format(self.user))

        if self.content.find('{}ping'.format(self.trigger)) == 0 \
                or re.search('^ping {}'.format(self.nick), self.content, re.IGNORECASE):
            self.send_message('pong {}'.format(self.user))

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

    def process_line(self, line):
        if len(line) > 0:
            line = line.replace('\n', '')
            line = line.replace('\r', '')
            self.format_content(line)
            if self.command == 'PING':
                self.post_string('PONG {}\n'.format(self.content))

            if self.command == 'PONG':
                self.last_ping = time.time()
                self.ping_pending = False

            if self.hostname == 'NickServ!NickServ@services.' and self.command == 'NOTICE' and self.target == self.nick:
                if self.nickserv_replay:
                    self.nickserv_replay = False
                    self.send_message('NICKSERV: {}'.format(self.content))

            if re.search('^\x01', self.content) and re.search('\x01$', self.content):
                print("CTCP")
                self.trigger_ctcp()

            if self.command == 'PRIVMSG' and not re.search('\x01$', self.content):
                self.trigger_privmsg()

            if self.start_time + 2 < time.time():
                if self.command != "PONG":
                    if self.hostname:
                        print("Hostname: {}\nCommand: {}\nTarget: {}\nMessage: {}".format(self.hostname, self.command, self.target, self.content))

                if self.DEBUG:
                    self.send_message(line)

            print('{}: {}'.format(colorize("{} {}".format(time.strftime(self.time_format), self.server), 'green'), line))


    # Receive bytes from input, and process each new line which was received
    def process_input(self):
        data = self.connection.recv(4096)
        if not data or data == b'':
            return

        self.buffer += data.decode('utf-8')

        last_line_complete = (self.buffer[-1] == '\n')
        lines = self.buffer.split('\n')
        if last_line_complete: # The next buffer should be empty
            lines += ['']

        # Process all complete lines
        for line in lines[:-1]:
            self.process_line(line)

        # Next time append to the last line which is still incomplete
        self.buffer = self.buffer[-1]

    def post_string(self, message):
        print(colorize('{} {}> {}'.format(time.strftime(self.time_format), self.nick, message[:-1]), 'blue'))
        self.connection.send(bytes(message, 'utf-8'))

    def send_notice(self, message, target=None):
        if target:
            self.post_string('NOTICE ' + target + ' :' + message + '\n')
        else:
            self.post_string('NOTICE ' + self.channel + ' :' + message + '\n')

    def send_message(self, message, target=None):
        if target:
            self.post_string('PRIVMSG ' + target + ' :' + message + '\n')
        else:
            self.post_string('PRIVMSG ' + self.channel + ' :' + message + '\n')

    def stop_loop(self):
        self.quit_loop = True

    def loop(self):
        self.connect_server() # Initial connection attempt
        k = 0
        while not self.quit_loop:
            try:
                to_read, _, _ = select.select([self.connection], [], [], 1)
            except select.error:
                self.reconnect()
                continue

            # make sure connection doesn't get dropped
            if self.last_ping + PING_INTERVAL < time.time() and not self.ping_pending:
                self.try_ping()

            # it was too much time since last ping, assume a broken connection
            if self.last_ping + PING_TIMEOUT < time.time():
                self.reconnect()
                continue

            if to_read:
                r = self.process_input()

            self.lock.acquire()
            try:
                while len(self.queue) > 0:
                    print('loop_try_while: {}'.format(self.queue))
                    self.send_notice(self.queue[0])
                    self.queue = self.queue[1:]
            finally:
                self.lock.release()

    def __del__(self):
        self.connection.close()
