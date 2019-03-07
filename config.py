import configparser

class config:
    def read(self):
        config = configparser.ConfigParser()
        config.read(self.configfile)
        print(config)
        return config

    def write(self):
        with open(self.configfile, 'w') as configfile:
            self.config.write(configfile)

    def update(self, section, option, value):
        if not section in self.config.sections():
            self.config.add_section(section)
        self.config.set(section, option, str(value))
        self.widelands[section][option] = value
        self.write()

    def remove(self, section, option):
        self.config.set(section, option, '')
        self.widelands[section][option] = ''
        self.write()

    def ask(self, section, option):
        return self.config.get(section, option)
