import yaml  # pyyaml
from tldextract import extract

prefixs = ["DOMAIN-KEYWORD", "DOMAIN-SUFFIX", "DOMAIN"]


def listin(l1, l2):
    pos = len(l2) - len(l1)
    if pos >= 0:
        return l2[pos:] == l1


class Host:
    def __init__(self, rule):
        pattern, host = rule.split(",")
        pattern = pattern.strip()
        host = host.strip()
        self._host = host
        self.host = extract(host)
        self.suffix = self.host.suffix
        self.domain = self.host.domain
        self.subdomain = self.host.subdomain.split(".")
        self.pattern = pattern.upper()

    def __hash__(self):
        return hash(self.host)

    def __contains__(self, item):
        return self.is_superdomain(item)

    def is_superdomain(self, other):
        if self.pattern == "DOMAIN-KEYWORD":
            return self._host in other._host
        if self.pattern == "DOMAIN":
            return self.__eq__(other)
        if self.pattern == "DOMAIN-SUFFIX":
            if self.subdomain == [""]:
                return self.host.registered_domain == other.host.registered_domain
            return self.host.registered_domain == other.host.registered_domain and listin(
                self.subdomain, other.subdomain
            )

    def is_subdomain(self, other):
        if other.pattern == "DOMAIN-KEYWORD":
            return other._host in self._host
        if other.pattern == "DOMAIN-SUFFIX":
            return self.host.registered_domain == other.host.registered_domain and listin(
                other.subdomain, self.subdomain
            )

    def __eq__(self, other):
        return self._host == other._host and self.pattern == other.pattern

    def __repr__(self):
        return f"{self.pattern}, {self._host}"


with open(
    r"C:\Users\sharp\AppData\Local\Programs\clash_win\rules\proxy.yaml", encoding="utf8"
) as f:
    rules = yaml.safe_load(f)["payload"]
rules = [Host(x) for x in rules if x.startswith("DOMAIN")]


def check_one(rule):
    for x in rules:
        if (status := rule in x) and rule != x:
            print(rule, "in", x)
            return status


list(filter(lambda x: check_one(x), rules))
