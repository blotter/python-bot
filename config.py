import configparser

class config:
    def read(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.configfile)
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
        self.widelands['webhook']['port'] = self.config.getint('webhook', 'port')
        self.widelands['webhook']['start'] = self.config.getboolean('webhook', 'start')
        self.channels = self.widelands['channel']['liste'].split(', ')
        self.events = self.widelands['channel']['event'].split(', ')
        self.trigger = "{}, ".format(self.widelands['nickserv']['username'])

    def write(self):
        with open(self.configfile, 'w') as configfile:
            self.config.write(configfile)

    def update(self, section, option, value):
        if not section in self.config.sections():
            self.config.add_section(section)
        if isinstance(value, list):
            value = ', '.join(value)
        self.config.set(section, option, str(value))
        self.widelands[section][option] = value
        self.write()

    def remove(self, section, option):
        self.config.set(section, option, '')
        self.widelands[section][option] = ''
        self.write()

    def ask(self, section, option):
        return self.config.get(section, option)
