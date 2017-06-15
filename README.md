Minecord
========

*A Discord-based tool to manage a Minecraft server.*

---

#### Installation

Minecord requires Python 3.5+ to be installed.  
Install the requirements:

```
pip install -U -r requirements
```

Create a folder (this will be your server's root) and place the Minecraft
server file inside:

```
mkdir mc
mv ~/minecraft-server*.jar mc
```

Finally, get your Discord authentication token and store it:

```
touch token
chmod 600 token
echo your_auth_token > token
```

#### Configuration

You need to edit `config.json` to specify a couple options:

`mc-command`: the command line used to run the server  
`mc-directory`: the path to the directory you created  
`token`: the path to your authentication token  
`channel`: the ID of the Discord channel to work in  

#### Usage

Navigate to the `minecord` folder then simply execute it:

```
python3 minecord.py
```

From Discord, you can use `@minecord start` to start the server, `@minecord
bye` to shutdown Minecord, or `@minecord <command>` to send a command to the
server.

Occasionally, the client will add reactions to its own messages. You can then
click on them to trigger certain actions, for example accepting the EULA
or restarting the server.

#### Shells

Through certain buttons or commands, you can activate a "shell". Once it's
activated, everything you type will be sent directly to it, instead of the
main message processing. To exit a shell, simply type `exit`.

As of now, the only shell available is the chat shell, which forwards all of
your messages in the channel to the linked Minecraft server.
