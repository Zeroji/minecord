"""A Discord-based tool to manage a Minecraft server."""
import asyncio
import json
import os
import subprocess
import re
import time
import discord
import emoji


class Client(discord.Client):
    """Wrapper around discord.Client."""

    def __init__(self, config):
        super(Client, self).__init__()
        self.channel: discord.Channel = None
        self.proc: subprocess.Popen = None
        self.cfg: dict = config
        self.triggers: dict = {}
        self.me: discord.Member = None

    # discord.py events

    async def on_message(self, message):
        if message.channel != self.channel:
            return  # Only one channel
        if not message.content.startswith(self.user.mention):
            return  # Must start with a mention
        if message.author == self.me:
            return  # Can't reply to self
        text = message.content.split(None, 1)[1]
        if len(text) == 0:
            return  # No empty messages
        if text.startswith('bye'):
            await self.kill_server()
            await self.logout()
        elif text.startswith('start'):
            await self.start_server()
        else:  # Send command to server
            if self.proc is not None and self.proc.poll() is None:
                self.console(text)

    async def on_reaction_add(self, reaction: discord.Reaction, user):
        if user == self.me:  # No reacting to self
            return
        tag = None
        for t, msg in self.triggers.items():
            if reaction.message.id == msg:
                tag = t
        if tag is None:  # Message must be a trigger
            return
        for r in reaction.message.reactions:  # Reaction must have been added by the client
            if r.emoji == reaction.emoji and not r.me:
                return
        if tag == 'eula':  # Accept EULA
            eula = os.path.join(self.cfg['mc-directory'], 'eula.txt')
            content = open(eula).read().replace('eula=false', 'eula=true')
            open(eula, 'w').write(content)
            await self.set_trigger('eula', None)
            await self.send_tag('start', emoji.START_SRV, 'EULA accepted. You can now start the server.')
        elif tag == 'start':
            await self.start_server()
        elif tag == 'control':
            if reaction.emoji == emoji.STOP_SRV:
                await self.stop_server()
            elif reaction.emoji == emoji.KILL_SRV:
                await self.kill_server()
            elif reaction.emoji == emoji.RESTART_SRV:
                await self.restart_server()
        else:
            await self.send('Reaction received: ' + reaction.emoji)

    async def on_ready(self):
        self.channel = self.get_channel(self.cfg['channel'])
        self.me = self.channel.server.me
        await self.send_tag('start', emoji.START_SRV, "Hi everyone!")

    # discord-related functions

    async def send(self, *args, **kwargs):
        """Shortcut for send_message."""
        return await self.send_message(self.channel, *args, **kwargs)

    async def send_react(self, reactions, *args, **kwargs):
        """Send a message and add reactions to it."""
        message = await self.send(*args, **kwargs)
        if isinstance(reactions, str):  # Handle two-character emojis
            reactions = (reactions,)
        for reaction in reactions:
            await self.add_reaction(message, reaction)
        return message

    async def send_tag(self, tag, reactions, *args, **kwargs):
        """Send a message with reactions and add it as a trigger."""
        message = await self.send_react(reactions, *args, **kwargs)
        await self.set_trigger(tag, message)

    async def set_trigger(self, tag, message):
        """Set/change a trigger message.

        Triggers are messages with reactions added by the client,
        which can be clicked by the user to do certain actions."""
        if tag in self.triggers:
            try:
                msg = await self.get_message(self.channel, self.triggers[tag])
            except discord.NotFound:
                pass
            else:
                # Remove reactions on the previous trigger (from this tag)
                for reaction in msg.reactions:
                    if reaction.me and reaction.emoji in emoji.TRIGGERS[tag]:
                        await self.remove_reaction(msg, reaction.emoji, self.me)
        if message is None:
            self.triggers.pop(tag)
        else:
            self.triggers[tag] = message.id

    # server-related events

    async def read_console(self):
        """Loop through the console output"""
        while self.proc is not None and self.proc.poll() is None:
            line = await self.loop.run_in_executor(None, self.proc.stdout.readline)  # Async readline
            # Parse the command output and get the time in epoch format
            match = re.match(r'\[([0-9]{2}):([0-9]{2}):([0-9]{2})\] \[([^][]*)\]: (.*)$', line.decode())
            if match is None:
                return
            h, m, s, log, text = match.groups()
            local = time.localtime()
            if h == 23 and local.tm_hour == 0:  # In case a line from 23:59 gets parsed at 00:00
                local = time.localtime(time.time()-3600)
            log_t = list(local)
            log_t[3:6] = map(int, (h, m, s))
            log_time = time.mktime(tuple(log_t))
            self.loop.create_task(self.on_line(log_time, log, text))

    async def on_line(self, timestamp, logger, line: str):
        """Process one line of output."""
        if line.startswith('You need to agree to the EULA in order to run the server.'):
            message = "You need to agree to Mojang's End-User License Agreement in order to run the server.\n" \
                "For more information, please visit <https://account.mojang.com/documents/minecraft_eula>.\n" \
                "By clicking the button below you are indicating your agreement to Mojang's EULA."
            await self.send_tag('eula', emoji.ACCEPT_EULA, message)
        else:
            await self.send(line)

    # server-related functions

    def console(self, message):
        """Send a command to the server."""
        message = message.split('\n')[0] + '\n'
        self.proc.stdin.write(message.encode())
        self.proc.stdin.flush()

    def _start(self):
        self.proc = subprocess.Popen(self.cfg['mc-command'].split(), cwd=self.cfg['mc-directory'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.loop.create_task(self.read_console())

    async def _stop(self):
        self.console('stop')
        try:
            await self.loop.run_in_executor(None, self.proc.wait, 10)
        except subprocess.TimeoutExpired:
            await self.kill()
            return False
        else:
            return True

    async def _kill(self):
        self.console('say Killing server!')
        await asyncio.sleep(0.5)
        self.proc.kill()

    async def start_server(self):
        self._start()
        await self.set_trigger('start', None)
        await self.send_tag('control', emoji.TRIGGERS['control'], 'Server started!')

    async def stop_server(self):
        """Stop the server, kill it after a timeout."""
        t = time.time()
        success = await self._stop()
        t = time.time() - t
        if success:
            await self.send('Server stopped in {time:.3f}'.format(time=t))
        else:
            await self.send('Server timed out and was killed')

    async def kill_server(self):
        await self._kill()
        await self.send('Server killed')

    async def restart_server(self):
        await self.stop_server()
        self._start()
        await self.send_tag('control', emoji.TRIGGERS['control'], 'Server restarted!')


def main():
    config = json.load(open('config.json'))
    token = open(config['auth-token']).read().strip()
    client = Client(config)
    client.run(token)

if __name__ == '__main__':
    main()
