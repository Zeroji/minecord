"""Handle roles and permissions."""
import json
import re


class Role:
    """Define a role, with permissions and sub-roles."""

    def __init__(self, name='', all_perms=set()):
        self.name = name
        self.all_perms = all_perms
        self.perms = []
        self.sub_roles = []

    def load(self, perm_list, permissions):
        """Load from a permission list."""
        for perm in perm_list:
            if perm.startswith('#'):
                self.sub_roles.append(permissions.get_role(perm[1:]))
            else:
                self.perms.append(perm)
        self.all_perms.update(self.perms)

    def __contains__(self, item):
        """Whether or not a permission/role is contained."""
        if item == '#' + self.name:
            return True
        contain = item in self.perms or any([item in role for role in self.sub_roles])
        if contain:
            return True
        if item == '@' or item.startswith('#'):
            return False
        if item not in self.all_perms:
            return '@' in self

    def __bool__(self):
        """Whether or not this role has any permissions."""
        return len(self.perms) > 0 or any(self.sub_roles)


class Permissions:
    """Handle permissions."""
    def __init__(self, roles_filename, users_filename, client):
        self.roles_filename = roles_filename
        self.users_filename = users_filename
        self.client = client
        self.all_perms = set()
        self.roles = {}
        self.users = {}
        self.reload()

    def __getitem__(self, item):
        """Get a user's role."""
        if item not in self.users:
            return Role()
        else:
            return self.get_role(self.users[item])

    def reload(self):
        """Reload roles and users."""
        self.all_perms.clear()
        self.roles.clear()
        data = json.load(open(self.roles_filename))
        for role in data:
            self.roles[role] = Role(role, self.all_perms)
        for name, role in self.roles.items():
            role.load(data[name], self)
        if '@' in self.all_perms:
            self.all_perms.remove('@')
        self.reload_users()

    def reload_users(self):
        """Reload users."""
        self.users.clear()
        data = json.load(open(self.users_filename))
        self.users.update(data)

    def get_role(self, name):
        return self.roles.get(name, Role())

    async def list_roles(self, args):
        """List different roles, or list the permissions of a role."""
        if not args:
            await self.client.send("The following roles exist: " + ', '.join(['#**%s**' % name for name in self.roles]))
        else:
            args = args.lstrip('#')
            if args not in self.roles:
                await self.client.send_error("Role #**{role}** doesn't exist.".format(role=args))
            else:
                role = self.roles[args]
                message = "Role #**{role}** has the following permissions: ".format(role=args) + ', '.join(role.perms)
                for sub_role in role.sub_roles:
                    message += ' + #**{sub}**'.format(sub=sub_role.name)
                await self.client.send(message)

    async def show_role(self, args):
        """Display someone's role."""
        uid = get_uid(args)
        if uid is None:
            return
        if uid not in self.users:
            await self.client.send('This user has no roles.')
        else:
            await self.client.send('This user has the #**{role}** role.'.format(role=self.users[uid]))

    async def set_role(self, args, user):
        """Set or remove someone's role."""
        if ' ' in args:
            target, new_role = args.split(None, 1)
            new_role = new_role.lstrip('#')
        else:
            target, new_role = args, None
        user_role = self.users[user.id]
        target = get_uid(target)
        old_role = self.users.get(target, None)
        if old_role is not None and (old_role == user_role or '#' + old_role not in self.get_role(user_role)):
            await self.client.send_error_perms(user.mention + ", you aren't allowed to remove this role.")
            return
        if new_role is not None and (new_role == user_role or '#' + new_role not in self.get_role(user_role)):
            await self.client.send_error_perms(user.mention + ", you aren't allowed to assign this role.")
            return
        if new_role is None and target in self.users:
            self.users.pop(target)
        else:
            self.users[target] = new_role
        json.dump(self.users, open(self.users_filename, 'w'), indent=2)
        if new_role is None:
            await self.client.send("Role successfully removed.")
        else:
            await self.client.send("Role #**{role}** successfully assigned.".format(role=new_role))


def get_uid(args):
    if not args:
        return None
    if re.match('[0-9]{18,}', args) is not None:
        return args
    match = re.match('<@!?([0-9]*)>', args)
    if match is not None:
        return match.group(1)
    return None
