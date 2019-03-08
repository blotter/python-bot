import configparser

class config:
    def read(self):
        config = configparser.ConfigParser()
        config.read(self.configfile)
        self.widelands = config._sections
        self.widelands['server']['ssl'] = config.getboolean('server', 'ssl')
        self.widelands['server']['sasl'] = config.getboolean('server', 'sasl')
        self.widelands['server']['port'] = config.getint('server', 'port')
        self.widelands['server']['retry'] = config.getint('server', 'retry')
        self.widelands['nickserv']['replay'] = config.getboolean('nickserv', 'replay')
        self.widelands['admin']['debug'] = config.getboolean('admin', 'debug')
        self.widelands['ping']['interval'] = config.getint('ping', 'interval')
        self.widelands['ping']['timeout'] = config.getint('ping', 'timeout')
        self.widelands['ping']['pending'] = config.getboolean('ping', 'pending')
        self.widelands['ping']['use'] = config.getboolean('ping', 'use')
        if ',' in self.widelands['channel']['liste']:
            self.channels = self.widelands['channel']['liste'].split(', ')
        self.trigger = "{}, ".format(self.widelands['nickserv']['username'])
        return config

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
