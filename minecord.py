"""A Discord-based tool to manage a Minecraft server."""
import asyncio
import inspect
import json
import os
import subprocess
import re
import time
import discord
import emoji
import permissions


class Client(discord.Client):
    """Wrapper around discord.Client."""

    def __init__(self, config):
        super(Client, self).__init__()
        self.channel: discord.Channel = None
        self.proc: subprocess.Popen = None
        self.cfg: dict = config
        self.triggers: dict = {}
        self.me: discord.Member = None
        self.chat: bool = False
        self.shells: dict = {}
        self.chat_message: discord.Message = None
        self.prefixes: list = []
        self.perms: permissions.Permissions = None

    # discord.py events

    async def on_message(self, message):
        if message.channel != self.channel:
            return  # Only one channel
        if message.author == self.me:
            return  # Can't reply to self
        try:
            prefix, text = message.content.split(None, 1)
        except ValueError:
            prefix, text = '', message.content
        if prefix not in self.prefixes:  # Must start with prefix, or be a shell
            if message.author.id in self.shells:  # Active shell
                await self.shell_wrapper(message.author, message.clean_content)
            return
        if len(text) == 0:
            return  # No empty messages
        if ' ' not in text:
            cmd, args = text, ''
        else:
            cmd, args = text.split(None, 1)
        await self.call(message.author, cmd, args)

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
        async def rcall(command, args=''):
            await self.call(user, command, args, reaction=True)
        if tag == 'eula':  # Accept EULA
            await rcall('eula')
        elif tag == 'start':
            await rcall('start')
        elif tag == 'control':
            if reaction.emoji == emoji.STOP_SRV:
                await rcall('stop')
            elif reaction.emoji == emoji.KILL_SRV:
                await rcall('kill')
            elif reaction.emoji == emoji.RESTART_SRV:
                await rcall('restart')
        elif tag == 'chat_init':
            await rcall('chat', 'true')
        elif tag == 'chat':
            if reaction.emoji == emoji.CHAT_STOP:
                await rcall('chat', 'false')
            elif reaction.emoji == emoji.CHAT_SHELL:
                await self.shell_activate(user, self.shell_chat)
        else:
            await self.send('Reaction received: ' + reaction.emoji)

    async def on_ready(self):
        self.channel = self.get_channel(self.cfg['channel'])
        self.me = self.channel.server.me
        self.prefixes.append(self.user.mention)
        self.prefixes.extend(self.cfg['prefixes'])
        self.perms = permissions.Permissions(self.cfg['role-config'], self.cfg['role-users'], self)
        await self.send_tag('start', emoji.START_SRV, "Hi everyone!")

    async def quit(self):
        """Terminate server and stop minecord."""
        await self.kill_server()
        await self.logout()

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
        return message

    async def send_delete(self, timeout, message, *args, **kwargs):
        """Send a message, and delete it after a certain amount of time."""
        msg = await self.send(message, *args, **kwargs)
        await self.delay(timeout, self.delete_message, msg)

    async def send_error(self, message, *args, **kwargs):
        if isinstance(message, str):
            message = emoji.ERROR_MAIN + ' ' + message
        await self.send(message, *args, **kwargs)

    async def send_error_perms(self, message, *args, **kwargs):
        if isinstance(message, str):
            message = emoji.ERROR_PERM + ' ' + message
        await self.send_delete(10, message, *args, **kwargs)

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
            self.triggers.pop(tag)
        if message is not None:
            self.triggers[tag] = message.id

    async def delay(self, sleep_time, func, *args, **kwargs):
        self.loop.create_task(self._delay(sleep_time, func, *args, **kwargs))

    @staticmethod
    async def _delay(sleep_time, func, *args, **kwargs):
        await asyncio.sleep(sleep_time)
        await func(*args, **kwargs)

    # shells

    async def shell_activate(self, user: discord.Member, shell):
        if user.id in self.shells:
            if self.shells[user.id] != shell:
                await self.send('Another shell is already activated for ' + user.mention + ' (quit with `exit`)')
            return
        self.shells[user.id] = shell
        await self.send('Shell initiated for ' + user.mention)

    async def shell_terminate(self, user: discord.Member):
        if user.id not in self.shells:
            return
        await self.send('Shell terminated for ' + user.mention)
        self.shells.pop(user.id)

    async def shell_terminate_all(self, shell):
        uids = [uid for (uid, sh) in self.shells.items() if sh == shell]
        for uid in uids:
            self.shells.pop(uid)
        await self.send('All `' + shell.__name__[6:] + '` shells terminated.')

    async def shell_wrapper(self, user: discord.Member, message: str):
        if user.id not in self.shells:
            return
        if message.lower() == 'exit':
            await self.shell_terminate(user)
            return
        shell = self.shells[user.id]
        await shell(user, message)

    async def shell_chat(self, user: discord.Member, message: str):
        """Forward user messages to Minecraft."""
        author = user.nick or user.name
        message = message.replace('\n', '').replace('/', '').replace('§', '')
        self.console(f'say <{author}> {message}')

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
        if line.startswith('You need to agree to the EULA in order to run the server.'):  # EULA error
            message = "You need to agree to Mojang's End-User License Agreement in order to run the server.\n" \
                "For more information, please visit <https://account.mojang.com/documents/minecraft_eula>.\n" \
                "By clicking the button below you are indicating your agreement to Mojang's EULA."
            await self.send_tag('eula', emoji.ACCEPT_EULA, message)
        if line.startswith('[Server] ') or re.match(r'<[^\s<>]*> ', line) is not None:  # Chat messages
            if not self.chat:
                return
            if line.startswith('[Server] '):
                message = line[9:]
                author = 'SERVER'
                if message.startswith('<'):  # Message sent by the bridge
                    return
            else:
                match = re.match(r'<([^\s<>]*)> (.*)', line)
                author, message = match.groups()
            await self.send_tag('chat', emoji.TRIGGERS['chat'], f'**{author}**: {message}')

    # server-related functions

    async def call(self, user: discord.Member, command, args='', reaction=False):
        """Call a command, checking your privilege."""
        commands = {'quit': self.quit,
                    'start': self.start_server, 'stop': self.stop_server, 'restart': self.restart_server,
                    'kill': self.kill_server, 'eula': self.accept_eula, 'chat': self.set_chat,
                    'rlist': self.perms.list_roles, 'rget': self.perms.show_role, 'rset': self.perms.set_role,
                    'reload_perms': self.reload_perms}
        user_perms = self.perms[user.id]
        if command not in user_perms:
            if user_perms:  # Don't display the message if the user has no permissions at all
                await self.send_error_perms("{user}, you are not allowed to use the command `{command}`".format(
                    user=user.mention, command=command))
            return
        if command in commands:
            func = commands[command]
            sig = inspect.signature(func)
            kw = {}
            if 'args' in sig.parameters:
                kw['args'] = args
            if 'user' in sig.parameters:
                kw['user'] = user
            await func(**kw)
        else:
            self.console(' '.join((command, args)))

    async def accept_eula(self):
        eula = os.path.join(self.cfg['mc-directory'], 'eula.txt')
        content = open(eula).read().replace('eula=false', 'eula=true')
        open(eula, 'w').write(content)
        await self.set_trigger('eula', None)
        await self.send_tag('start', emoji.START_SRV, 'EULA accepted. You can now start the server.')

    def console(self, message):
        """Send a command to the server."""
        if self.proc is None or self.proc.poll() is not None:
            return
        message = message.split('\n')[0] + '\n'
        self.proc.stdin.write(message.encode())
        self.proc.stdin.flush()

    def _start(self):
        self.proc = subprocess.Popen(self.cfg['mc-command'].split(), cwd=self.cfg['mc-directory'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.loop.create_task(self.read_console())

    async def _stop(self):
        if self.proc is None or self.proc.poll() is not None:
            return
        self.console('stop')
        try:
            await self.loop.run_in_executor(None, self.proc.wait, self.cfg['mc-kill-timeout'])
        except subprocess.TimeoutExpired:
            await self.kill()
            return False
        else:
            return True

    async def _kill(self):
        if self.proc is None or self.proc.poll() is not None:
            return False
        self.console('say Killing server!')
        await asyncio.sleep(0.5)
        self.proc.kill()
        return True

    async def start_server(self):
        self._start()
        await self.set_trigger('start', None)
        m = await self.send_tag('control', emoji.TRIGGERS['control'], 'Server started!')
        await self.add_reaction(m, emoji.CHAT_START)
        await self.set_trigger('chat_init', m)

    async def stop_server(self):
        """Stop the server, kill it after a timeout."""
        t = time.time()
        success = await self._stop()
        t = time.time() - t
        if success:
            await self.send('Server stopped in {time:.3f}s'.format(time=t))
        else:
            await self.send('Server timed out and was killed')
        await self.set_trigger('control', None)
        await self.set_trigger('chat', None)
        await self.set_trigger('chat_init', None)

    async def kill_server(self):
        """Kill the server."""
        if await self._kill():
            await self.send('Server killed')

    async def restart_server(self):
        await self.stop_server()
        self._start()
        await self.send_tag('control', emoji.TRIGGERS['control'], 'Server restarted!')

    async def set_chat(self, args):
        value = args if isinstance(args, bool) else args.lower() in ('yes', 'true', '1')
        if self.chat == value:
            return
        self.chat = value
        if self.chat_message is not None:
            await self.delete_message(self.chat_message)
        await self.set_trigger('chat_init', None)
        await self.set_trigger('chat', None)
        tag = 'chat' if self.chat else 'chat_init'
        self.chat_message = await self.send_tag(tag, emoji.TRIGGERS[tag], 'Chat enabled' if self.chat else 'Chat muted')
        if not self.chat:
            await self.shell_terminate_all(self.shell_chat)

    async def reload_perms(self):
        """Reload all permission settings from disk."""
        self.perms.reload()
        await self.send('Successfully reloaded permission settings.')


def main():
    config = json.load(open('config.json'))
    token = open(config['auth-token']).read().strip()
    client = Client(config)
    client.run(token)

if __name__ == '__main__':
    main()
