# -*- coding: utf-8 -*-

import argparse
import os
import datetime
import re
import signal

try:
    import yaml
    from cloudflare import Cloudflare, NOT_GIVEN
    from cloudflare.types.zones import Zone
    from cloudflare.types.dns import RecordResponse
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("Please install cloudflare>=4.0, rich and PyYAML")
    exit(1)

__version__ = "1.0.0"

CONFIGFILE_SAMPLE = """defaults:
    token: __SPECIFY_TOKEN__
    domain: __SPECIFY_DOMAIN__"""
DEFAULT_TYPE = "A"
DEFAULT_TTL = 3600
TYPE_CHOICES = ["A", "AAAA", "CAA", "CERT", "CNAME", "DNSKEY", "DS", "HTTPS", "LOC", "MX", "NAPTR",
                "NS", "OPENPGPKEY", "PTR", "SMIMEA", "SRV", "SSHFP", "SVCB", "TLSA", "TXT", "URI"]

class CFAction:
    def __init__(self, namespace: argparse.Namespace, parser: argparse.ArgumentParser):
        self.namespace = namespace
        self.cf = Cloudflare(api_token=self._get_token())
        self.parser = parser
        self.domain = self.get_domain()
    def _get_token(self) -> str:
        if os.path.exists((path := os.path.expanduser("~/.cfcli.yml"))):
            with open(path, "r") as f:
                values = yaml.safe_load(f)
                return values[self.namespace.context]["token"]
        else:
            print("Configfile ~/.cfcli.yml not exists, please create it, sample follows")
            print(CONFIGFILE_SAMPLE)
            exit(1)
    def get_domain(self) -> str:
        with open(os.path.expanduser("~/.cfcli.yml"), "r") as f:
            values = yaml.safe_load(f)
            read_domain = values["defaults"].get("domain", None)
        if self.namespace.domain:
            return self.namespace.domain
        if read_domain is not None:
            return read_domain
        print("Domain not given as Parameter or in Configfile")
        self.parser.print_help()
        exit(1)


class RemoveCFAction(CFAction):
    def __call__(self):
        if len((zones := self.cf.zones.list(name=self.domain)).result) > 0:
            zone = next(iter(zones))
            if self.namespace.debug:
                print(f"Zone found: {zone}")
        else:
            print(f"Zone {self.domain} not found or not accessible")
            exit(1)
        if self.namespace.id:
            result = self.cf.dns.records.delete(zone_id=zone.id, dns_record_id=self.namespace.record)
            if self.namespace.debug:
                print(f"Deleted record: {result}")
            if result.id:
                print(f"Successfully deleted DNS record {self.namespace.record}")
                exit()
        if len((records := self.cf.dns.records.list(zone_id=zone.id, type=self.namespace.type, name=self.namespace.record)).result) > 0:
            record = next(iter(records))
            result = self.cf.dns.records.delete(zone_id=zone.id, dns_record_id=record.id)
            if self.namespace.debug:
                print(f"Deleted record: {record}")
            if result.id:
                print(f"Successfully deleted DNS record {self.namespace.record}")
                exit()
        else:
            print(f"No records found for {self.namespace.record} in {self.domain}")
            exit(1)


class ListCFAction(CFAction):
    def __call__(self):
        if len((zones := self.cf.zones.list(name=self.domain)).result) > 0:
            zone = next(iter(zones))
            if self.namespace.debug:
                print(f"Zone found: {zone}")
        else:
            print(f"Zone {self.domain} not found or not accessible")
            exit(1)
        records_req = self.cf.dns.records.list(zone_id=zone.id, type=self.namespace.type if self.namespace.type != "ALL" else NOT_GIVEN)
        if records_req:
            records = []
            for page in records_req.iter_pages():
                records.extend(page.result)
            if self.namespace.debug:
                print(f"Found {len(records)} DNS records in {self.domain}")
            if self.namespace.search:
                if self.namespace.regex:
                    try:
                        regex = re.compile(self.namespace.search)
                        self.print([rec for rec in records if regex.search(rec.name)], self.domain)
                    except re.error:
                        print("Invalid regular expression")
                        exit(1)
                else:
                    self.print([rec for rec in records if self.namespace.search in rec.name], self.domain)
            else:
                if len(records) >= 1000:
                    print("\033[1mOutput truncated to 1000 records, use search filter instead\033[0m")
                self.print(records[:1000], self.domain)
        else:
            print(f"No records found in {self.domain}")
    def print(self, records: list[RecordResponse], domain: str):
        table = Table(title=f"DNS Records of Domain {domain}")
        columns = ("Type", "Name", "Value", "TTL", "Proxied", "ID")
        for column in columns:
            table.add_column(column, min_width=5, no_wrap=False if column in ("ID", "Value") and not self.namespace.nowrap else True)
        for record in records:
            table.add_row(record.type, record.name, record.content,
                          str(round(record.ttl)) if record.ttl != 1.0 else "Automatic",
                          "Yes" if record.proxied else "No", record.id)
        console = Console()
        try:
            console.print(table)
        except BrokenPipeError:
            pass


class AddCFAction(CFAction):
    def __call__(self):
        if len((zones := self.cf.zones.list(name=self.domain)).result) > 0:
            zone = next(iter(zones))
            if self.namespace.debug:
                print(f"Zone found: {zone}")
        else:
            print(f"Zone {self.domain} not found or not accessible")
            exit(1)
        record = self.cf.dns.records.create(zone_id=zone.id,
                                       type=self.namespace.type,
                                       name=self.namespace.record,
                                       ttl=self.namespace.ttl,
                                       content=self.namespace.value,
                                       tags=self.namespace.tag if self.namespace.tag else NOT_GIVEN,
                                       comment=self.namespace.comment if self.namespace.comment else NOT_GIVEN,
                                       priority=self.namespace.priority if self.namespace.priority else NOT_GIVEN)
        if self.namespace.debug:
            print(f"Create called: {record}")
        if record.id:
            print(f"Successfully created DNS record {self.namespace.record}")


class ModifyCFAction(CFAction):
    def __call__(self):
        if len((zones := self.cf.zones.list(name=self.domain)).result) > 0:
            zone = next(iter(zones))
            if self.namespace.debug:
                print(f"Zone found: {zone}")
        else:
            print(f"Zone {self.domain} not found or not accessible")
            exit(1)
        if self.namespace.id:
            self.edit_record(self.cf.dns.records.get(dns_record_id=self.namespace.record, zone_id=zone.id), zone)
        else:
            records = self.cf.dns.records.list(zone_id=zone.id, type=self.namespace.type, name={"contains": self.namespace.record}).result
            if len(records) < 1:
                print("no records found")
                exit(0)
            if len(records) > 1:
                input(f"You modify {len(records)} entries, do you really want to proceed?\nPress Enter to confirm or Ctrl+C for cancel")
            for record in records:
                if self.namespace.debug:
                    print(f"Record found: {record}")
                self.edit_record(record, zone)
    def edit_record(self, record, zone):
        response = self.cf.dns.records.edit(record.id,
                                   zone_id=zone.id,
                                   type=self.namespace.type,
                                   ttl=self.namespace.ttl,
                                   name=NOT_GIVEN,
                                   content=self.namespace.value if self.namespace.value else NOT_GIVEN,
                                   tags=self.namespace.tag if self.namespace.tag else NOT_GIVEN,
                                   comment=self.namespace.comment if self.namespace.comment else NOT_GIVEN,
                                   priority=self.namespace.priority if self.namespace.priority else NOT_GIVEN)
        if (datetime.datetime.now(tz=datetime.UTC) - response.modified_on).seconds < 2:
            print(f"Successfully modified DNS record {record.name}")
        if self.namespace.debug:
            print(f"Record modify called: {response}")


class ZonesCFAction(CFAction):
    def __call__(self):
        zones = self.cf.zones.list()
        if self.namespace.debug:
            print(zones)
        self.print(zones)
    def print(self, zones: list[Zone]):
        table = Table(title="DNS Zones")
        table.add_column("Name", no_wrap=True)
        table.add_column("Plan", no_wrap=True)
        table.add_column("Active", no_wrap=True)
        table.add_column("ID")
        for zone in zones:
            table.add_row(zone.name, zone.plan.legacy_id, zone.status, zone.id)
        console = Console()
        try:
            console.print(table)
        except BrokenPipeError:
            pass


def call_sigint_handler(signum, frame):
    print()
    exit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, call_sigint_handler)
    parser = argparse.ArgumentParser("Cloudflare DNS CLI")
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument("-c", "--context", help="use specific context in config file", default="defaults")
    parser.add_argument("-d", "--domain", help="Domain name")
    parser.add_argument("-D", "--debug", help="Enable debug mode", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True, title="Commands")
    add = sub.add_parser("add", help="Add a DNS record")
    add.add_argument("-t", "--type", help="DNS Type", default=DEFAULT_TYPE, choices=TYPE_CHOICES)
    add.add_argument("-l", "--ttl", help="TTL", default=DEFAULT_TTL, type=int)
    add.add_argument("-p", "--priority", help="Priority")
    add.add_argument("--proxied", help="Record in proxy mode", action="store_true", default=False)
    add.add_argument("-m", "--comment", help="Comment")
    add.add_argument("-T", "--tag", help="Tag, can be used multiple times", action="append")
    add.add_argument("record", help="DNS Record Name")
    add.add_argument("value", help="DNS Value")
    rm = sub.add_parser("rm", help="Remove a DNS record")
    rm.add_argument("record", help="DNS Record Name")
    rm.add_argument("-t", "--type", help="DNS Type", default=DEFAULT_TYPE, choices=TYPE_CHOICES)
    rm.add_argument("--id", help="Cloudflare ID", action="store_true", default=False)
    ls = sub.add_parser("ls", help="List DNS records")
    ls.add_argument("search", help="Search Term, substrings or RegEx (only valid with regex option)", default="", nargs="?")
    ls.add_argument("--regex", help="Enable RegEx mode for search", action="store_true", default=False)
    ls.add_argument("-t", "--type", help="DNS Type, special Type ALL to match all Types", default="ALL", choices=TYPE_CHOICES + ["ALL"])
    ls.add_argument("--nowrap", help="Do not wrap result", action="store_true", default=False)
    edit = sub.add_parser("edit", help="Edit a DNS record")
    edit.add_argument("-t", "--type", help="DNS Type", default=DEFAULT_TYPE, choices=TYPE_CHOICES)
    edit.add_argument("-l", "--ttl", help="TTL", default=NOT_GIVEN, type=int)
    edit.add_argument("-p", "--priority", help="Priority")
    edit.add_argument("--id", help="Cloudflare ID", action="store_true", default=False)
    edit.add_argument("--proxied", help="Record in proxy mode", action="store_true", default=False)
    edit.add_argument("-m", "--comment", help="Comment")
    edit.add_argument("-T", "--tag", help="Tag, can be used multiple times", action="append")
    edit.add_argument("record", help="DNS Record Name")
    edit.add_argument("value", help="DNS Value", default="", nargs="?")
    zones = sub.add_parser("zones", help="List DNS zones")

    args = parser.parse_args()
    if args.command == "rm":
        RemoveCFAction(args, parser)()
    elif args.command == "ls":
        ListCFAction(args, parser)()
    elif args.command == "add":
        AddCFAction(args, parser)()
    elif args.command == "edit":
        ModifyCFAction(args, parser)()
    elif args.command == "zones":
        ZonesCFAction(args, parser)()
