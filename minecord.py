"""A Discord-based tool to manage a Minecraft server."""
import json
import subprocess
import discord


class Client(discord.Client):
    """Wrapper around discord.Client."""

    def __init__(self, config):
        super(Client, self).__init__()
        self.channel = None
        self.proc = None
        self.cfg = config

    async def on_message(self, message):
        if message.channel != self.channel:
            return  # Only one channel
        if not message.content.startswith(self.user.mention):
            return  # Must start with a mention
        if message.author == self.user:
            return  # Can't reply to self
        text = message.content.split(None, 1)[1]
        if len(text) == 0:
            return  # No empty messages
        if text.startswith('bye'):  # Kill server, logout
            if self.proc is not None:
                self.proc.kill()
            await self.logout()
        elif text.startswith('start'):  # Start server
            self.proc = subprocess.Popen(self.cfg['mc-command'].split(), cwd=self.cfg['mc-directory'], stdin=subprocess.PIPE)
        else:  # Send command to server
            self.proc.stdin.write(text.encode()+b'\n')
            self.proc.stdin.flush()

    async def on_ready(self):
        self.channel = self.get_channel(self.cfg['channel'])
        await self.send_message(self.channel, "Hi everyone!")


def main():
    config = json.load(open('config.json'))
    token = open(config['auth-token']).read().strip()
    client = Client(config)
    client.run(token)

if __name__ == '__main__':
    main()
