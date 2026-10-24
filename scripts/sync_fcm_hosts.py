"""Mirror upstream FCM hosts and update only their block in the Clash base."""

import ipaddress
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen


SOURCE = (
    "https://raw.githubusercontent.com/"
    "cagedbird043/fcm-hosts-next/main/fcm_dual.hosts"
)
ROOT = Path(__file__).resolve().parents[1]
BEGIN = "  # BEGIN AUTO FCM HOSTS"
END = "  # END AUTO FCM HOSTS"
FCM_DOMAIN = re.compile(
    r"(?:mtalk|mtalk4|mtalk-staging|mtalk-dev|alt[1-8]-mtalk)\.google\.com"
)


def parse_hosts(content):
    hosts = {}
    for number, line in enumerate(content.splitlines(), 1):
        fields = line.partition("#")[0].split()
        if not fields:
            continue
        if len(fields) < 2:
            raise ValueError(f"Invalid hosts entry on line {number}")
        address = ipaddress.ip_address(fields[0])
        if not address.is_global or "%" in fields[0]:
            raise ValueError(f"Non-public IP on line {number}")
        for domain in fields[1:]:
            domain = domain.lower()
            if not FCM_DOMAIN.fullmatch(domain):
                raise ValueError(f"Unexpected FCM domain on line {number}")
            addresses = hosts.setdefault(domain, [])
            if str(address) not in addresses:
                addresses.append(str(address))
    if "mtalk.google.com" not in hosts:
        raise ValueError("Upstream hosts is empty or missing mtalk.google.com")
    return hosts


def update_base(content, hosts):
    if content.count(BEGIN) != 1 or content.count(END) != 1:
        raise ValueError("Clash base must contain exactly one FCM block")
    start = content.index(BEGIN) + len(BEGIN)
    end = content.index(END)
    if end < start:
        raise ValueError("FCM block markers are out of order")
    newline = "\r\n" if "\r\n" in content else "\n"
    entries = newline.join(
        f"  {json.dumps(domain)}: {json.dumps(addresses)}"
        for domain, addresses in hosts.items()
    )
    return content[:start] + newline + entries + newline + content[end:]


def write_if_changed(path, content):
    if path.exists() and path.read_bytes() == content:
        return False
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def main():
    request = Request(SOURCE, headers={"User-Agent": "clashconfig-fcm-sync"})
    with urlopen(request, timeout=30) as response:
        upstream = response.read(64 * 1024 + 1)
    if len(upstream) > 64 * 1024:
        raise ValueError("Upstream hosts exceeds the size limit")
    hosts = parse_hosts(upstream.decode("utf-8-sig"))
    base_path = ROOT / "clash-base.yml"
    base = base_path.read_bytes().decode("utf-8")
    updated = update_base(base, hosts).encode("utf-8")
    # Validate and render everything before replacing either tracked file.
    mirrored = write_if_changed(ROOT / "fcm_dual.hosts", upstream)
    changed = write_if_changed(base_path, updated)
    print(
        f"FCM: {len(hosts)} domains, "
        f"{sum(map(len, hosts.values()))} addresses; "
        f"mirror changed={mirrored}, base changed={changed}"
    )


if __name__ == "__main__":
    main()
