class AnsiColors:
    def __init__(self):
        self.colors = {
            'purple': '\033[95m',
            'blue': '\033[94m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'red': '\033[91m'
        }

        self.end = '\033[0m'

    def color(self, string, color):
        return "%s%s%s" % (self.colors[color], string, self.end)
