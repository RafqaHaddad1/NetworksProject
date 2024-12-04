
BLACKLIST = {'example.com'}
WHITELIST = set()

def is_blacklisted(hostname):
    """Check if the hostname is blacklisted."""
    return hostname in BLACKLIST


def is_whitelisted(hostname):
    """Check if the hostname is whitelisted."""
    return not WHITELIST or hostname in WHITELIST

