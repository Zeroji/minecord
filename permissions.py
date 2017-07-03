"""Handle roles and permissions."""
import json


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
    def __init__(self, roles_filename, users_filename):
        self.roles_filename = roles_filename
        self.users_filename = users_filename
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
