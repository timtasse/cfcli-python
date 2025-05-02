# cfcli-python

In Python rewritten alternative to https://github.com/danielpigott/cloudflare-cli, but only for the Cloudflare DNS part and only for modifying existing zones.

The Script uses the same Configfile as the original (~/.cfcli.yml), so it can be used as drop-in replacement.

The Syntax is mostly the same, but not for all Parameters.

## Configfile Example

```yaml
defaults:
    token: <cloudflare-token>
    domain: <default-cloudflare-domain>
```

## Usage

General Usage for all subcommands
```
usage: Cloudflare DNS CLI [-h] [-d DOMAIN] [-D] {add,rm,ls,edit,zones} ...

options:
  -h, --help            show this help message and exit
  -d DOMAIN, --domain DOMAIN
                        Domain name
  -D, --debug           Enable debug mode

Commands:
  {add,rm,ls,edit,zones}
    add                 Add a DNS record
    rm                  Remove a DNS record
    ls                  List DNS records
    edit                Edit a DNS record
    zones               List DNS zones
```
the 'add' subcommand to create a new record
```
usage: Cloudflare DNS CLI add [-h] [-t TYPE] [-l TTL] [-p PRIORITY] [--proxied] [-m COMMENT] [-T TAG] record value

positional arguments:
  record                DNS Record Name
  value                 DNS Value

options:
  -h, --help            show this help message and exit
  -t TYPE, --type TYPE  DNS Type
  -l TTL, --ttl TTL     TTL
  -p PRIORITY, --priority PRIORITY
                        Priority
  --proxied             Record in proxy mode
  -m COMMENT, --comment COMMENT
                        Comment
  -T TAG, --tag TAG     Tag, can be used multiple times
```
the 'rm' subcommand to delete a record
```
usage: Cloudflare DNS CLI rm [-h] [-t TYPE] record

positional arguments:
  record                DNS Record Name

options:
  -h, --help            show this help message and exit
  -t TYPE, --type TYPE  DNS Type
```
the 'ls' subcommand to print records, supports literal match and RegEx via parameter
```
usage: Cloudflare DNS CLI ls [-h] [--regex] [search]

positional arguments:
  search      Search Term, substrings or RegEx (only valid with regex option)

options:
  -h, --help  show this help message and exit
  --regex     Enable RegEx mode for search
```
the 'edit' subcommand to modify an existing record
```
usage: Cloudflare DNS CLI edit [-h] [-t TYPE] [-l TTL] [-p PRIORITY] [--proxied] [-m COMMENT] [-T TAG] record [value]

positional arguments:
  record                DNS Record Name
  value                 DNS Value

options:
  -h, --help            show this help message and exit
  -t TYPE, --type TYPE  DNS Type
  -l TTL, --ttl TTL     TTL
  -p PRIORITY, --priority PRIORITY
                        Priority
  --proxied             Record in proxy mode
  -m COMMENT, --comment COMMENT
                        Comment
  -T TAG, --tag TAG     Tag, can be used multiple times
```

## Example

an example of the list command
```
cfcli ls --regex 'server\d'

                                    DNS Records of Domain demo.org
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Type ┃ Name                           ┃ Value        ┃ TTL ┃ Proxied ┃ ID                               ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ A    │ server1.mk.demo.org            │ 194.97.61.90 │ 120 │ No      │ aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa │
│ A    │ server1.vm.demo.org            │ 194.97.14.42 │ 60  │ No      │ bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb │
│ A    │ server2.mk.demo.org            │ 194.97.61.91 │ 120 │ No      │ cccccccccccccccccccccccccccccccc │
│ A    │ sevrer2.vm.demo.org            │ 194.97.14.43 │ 60  │ No      │ dddddddddddddddddddddddddddddddd │
└──────┴────────────────────────────────┴──────────────┴─────┴─────────┴──────────────────────────────────┘
```
