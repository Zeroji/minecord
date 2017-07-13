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
`mc-kill-timeout`: the time (in seconds) to wait before killing the server when stopping  
`mc-autostart`: `true` to automatically start Minecraft with minecord  
`auth-token`: the path to your authentication token  
`channel`: the ID of the Discord channel to work in  
`prefixes`: a list of command prefixes in addition to `@minecord`  
`role-config`: path to the role configuration JSON file  
`role-users`: path to the role/user assignations JSON file  
`short-name`: a short name displayed before all messages (useful with multiple servers)  

#### Usage

Navigate to the `minecord` folder then simply execute it:

```
python3 minecord.py
```

From Discord, you can use `@minecord <command>` to control minecord. You can
replace `@minecord` with other prefixes if specified in your config file.
Commands like `start`, `stop` or `quit` will control minecord, while any
other commands will be forwarded to the Minecraft server.

Occasionally, the client will add reactions to its own messages. You can then
click on them to trigger certain actions, for example accepting the EULA
or restarting the server.

#### Shells

Through certain buttons or via the `shell` command, you can activate a "shell".
Once it's activated, everything you type will be sent directly to it, unless
you use a prefix like `@minecord`. To exit a shell, simply type `exit`.

As of now, the only shell available is the chat shell, which forwards all of
your messages in the channel to the linked Minecraft server.

#### Permissions

Permissions are handled through two config files: one to define the roles,
which is only read by minecord, and another to assign roles to users. This
one can be edited manually, or via commands.

##### roles.json

This contains a dictionary of roles, each being a name associated to a list
of commands that role can use. Other roles can be referenced using '#role'.

```json
{
  "op": ["@", "#admin"],
  "admin": ["#mod", "stop", "ban", "quit"],
  "mod": ["kick", "tellraw"]
}
```

The special command `@` can be used to allow a role to use any command that
is not present in the file. This is useful when you want someone to have full
access to the Minecraft commands, but restrict the minecord side.

Shells also have permissions, to enable someone to use the shell `chat`, just
add `"$chat"` in the file. Users with the `@` permission will not have access
to any shell, you have to manually add them.

##### users.json

This file contains a dictionary of user ids, each mapped to the name of their
role. In future versions, it will be possible to change a user's role through
commands, rather than having to edit manually.
