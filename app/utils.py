class Follower:
    def __init__(self):
        self.attempts = 0
        self.telegram_id = None
        self.telegram_nick = None
        self.channel_name = None
        self.channel_url = None
        self.channel_theme = None
        self.channel_members = None
        self.channel_description = None

class Message:
    keys = ["date", "time", "text", "group", "type", "status", "row"]

    def __init__(self):
        for key in self.keys:
            setattr(self, key, None)

    def init(self, values):
        for key, value in zip(self.keys, values):
            setattr(self, key, value)