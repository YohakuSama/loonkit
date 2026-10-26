"""Typed, ordered source model for the public Loon configuration."""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path
import re

from loon_resources import ROOT, pinned_uri

MODEL = "build/profile.json"
NAME = re.compile(r"[^,=\s\[\]#;]+\Z")
HOST = re.compile(r"(?=.{1,253}\Z)[a-z0-9-]+(?:\.[a-z0-9-]+)+\Z")
BUILTINS = {"DIRECT", "REJECT", "REJECT-DROP", "REJECT-IMG", "REJECT-DICT", "REJECT-ARRAY"}
OPTIONS = {"select": (), "url-test": ("url", "interval", "tolerance"),
           "fallback": ("url", "interval", "max-timeout")}
FIELDS = {"schema_version", "general", "filters", "groups", "remote_rules", "hosts", "rules", "plugins", "service_roots"}


def object_fields(value, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("invalid " + label + " fields")


def scalar(value, label: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("invalid " + label)


def named(value, label: str) -> None:
    scalar(value, label)
    if not NAME.fullmatch(value):
        raise ValueError("invalid " + label)


def load(root: Path = ROOT) -> dict:
    return json.loads((root / MODEL).read_text(encoding="utf-8"))


def validate(model: dict) -> None:
    object_fields(model, FIELDS, "profile")
    if model["schema_version"] != 1:
        raise ValueError("unsupported profile model schema")
    for key in ("filters", "groups", "remote_rules", "rules", "plugins"):
        if not isinstance(model[key], list):
            raise ValueError("profile " + key + " must be ordered")
    for label in ("general", "hosts", "service_roots"):
        if not isinstance(model[label], dict):
            raise ValueError("invalid profile " + label)
    for key, value in model["general"].items():
        if not re.fullmatch(r"[a-z][a-z0-9-]*", key):
            raise ValueError("invalid general setting")
        scalar(value, "general setting")
    for host, address in model["hosts"].items():
        if not HOST.fullmatch(host):
            raise ValueError("invalid host override")
        ipaddress.ip_address(address)
    filters = set()
    for row in model["filters"]:
        object_fields(row, {"name", "pattern"}, "filter")
        named(row["name"], "filter name")
        scalar(row["pattern"], "filter pattern")
        if '"' in row["pattern"]:
            raise ValueError("filter pattern contains a quote")
        re.compile(row["pattern"])
        if row["name"] in filters or row["name"] in BUILTINS:
            raise ValueError("duplicate or reserved filter")
        filters.add(row["name"])
    groups = {}
    for row in model["groups"]:
        object_fields(row, {"name", "type", "members", "options", "icon"}, "group")
        named(row["name"], "group name")
        if row["name"] in groups or row["name"] in filters | BUILTINS:
            raise ValueError("duplicate or reserved group")
        if row["type"] not in OPTIONS:
            raise ValueError("unsupported group type")
        if not isinstance(row["members"], list) or not row["members"]:
            raise ValueError("group has no members")
        for member in row["members"]:
            named(member, "group member")
        if len(set(row["members"])) != len(row["members"]):
            raise ValueError("duplicate group member")
        if not isinstance(row["options"], dict) or set(row["options"]) != set(OPTIONS[row["type"]]):
            raise ValueError("invalid group options")
        for key, value in row["options"].items():
            if key == "url":
                scalar(value, "probe URL")
                if not re.fullmatch(r"https?://[^\s,]+", value):
                    raise ValueError("invalid probe URL")
            elif type(value) is not int or value < (0 if key == "tolerance" else 1):
                raise ValueError("invalid numeric group option")
        pinned_uri(row["icon"])
        groups[row["name"]] = row
    if not groups:
        raise ValueError("profile has no groups")
    policies = set(groups) | BUILTINS
    for row in groups.values():
        if set(row["members"]) - policies - filters:
            raise ValueError("undefined group member in " + row["name"])
    visiting, visited = set(), set()

    def visit(name):
        if name in visiting:
            raise ValueError("cyclic policy group reference: " + name)
        if name in visited:
            return
        visiting.add(name)
        for member in groups[name]["members"]:
            if member in groups:
                visit(member)
        visiting.remove(name)
        visited.add(name)

    for name in groups:
        visit(name)
    tags, uris = set(), set()
    for row in model["remote_rules"]:
        object_fields(row, {"uri", "policy", "tag", "source_group"}, "remote rule")
        resource = pinned_uri(row["uri"])
        if not resource["path"].startswith("rules/releases/") or not resource["path"].endswith(".lsr"):
            raise ValueError("formal rules require released LSR resources")
        named(row["tag"], "remote tag")
        named(row["source_group"], "source group")
        if row["policy"] not in policies:
            raise ValueError("undefined remote rule policy")
        if row["tag"] in tags or row["uri"] in uris:
            raise ValueError("duplicate remote resource or tag")
        tags.add(row["tag"])
        uris.add(row["uri"])
    for at, row in enumerate(model["remote_rules"]):
        if row["source_group"] == "AdBlock" and at != 0:
            raise ValueError("advertising rules must precede service rules")
        if row["source_group"] == "ChinaDirect" and at != len(model["remote_rules"]) - 1:
            raise ValueError("broad domestic rules must follow service rules")
    final = []
    for at, row in enumerate(model["rules"]):
        object_fields(row, {"type", "value", "policy", "flags"}, "local rule")
        if row["policy"] not in policies:
            raise ValueError("undefined local rule policy")
        kind, value, flags = row["type"], row["value"], row["flags"]
        if not isinstance(value, str) or not isinstance(flags, list) or flags not in ([], ["no-resolve"]):
            raise ValueError("invalid local rule value or flags")
        if kind == "FINAL":
            if value or flags:
                raise ValueError("invalid FINAL rule")
            final.append(at)
        elif kind in {"DOMAIN", "DOMAIN-SUFFIX"}:
            if not HOST.fullmatch(value) or flags:
                raise ValueError("invalid local domain rule")
        elif kind == "GEOIP":
            if not re.fullmatch(r"[A-Z]{2}", value):
                raise ValueError("invalid GEOIP country")
        elif kind in {"IP-CIDR", "IP-CIDR6"}:
            network = ipaddress.ip_network(value, strict=True)
            if (network.version == 6) != (kind == "IP-CIDR6"):
                raise ValueError("local rule IP family differs")
        elif kind == "IP-ASN":
            if not value.isdigit() or not 0 < int(value) < 2**32:
                raise ValueError("invalid local ASN")
        else:
            raise ValueError("unsupported local rule type")
    if final != [len(model["rules"]) - 1]:
        raise ValueError("FINAL must appear exactly once and last")
    fallback = {"type": "GEOIP", "value": "CN", "policy": "DIRECT", "flags": ["no-resolve"]}
    if (len(model["rules"]) < 2 or model["rules"][-2] != fallback
            or model["rules"][-1]["policy"] != "Final"
            or sum(row == fallback for row in model["rules"]) != 1):
        raise ValueError("native GEOIP fallback must immediately precede FINAL,Final")
    if len(model["plugins"]) != 1:
        raise ValueError("public profile requires one explicit diagnostic plugin")
    pinned_uri(model["plugins"][0])
    for group, hosts in model["service_roots"].items():
        if group not in groups or not isinstance(hosts, list) or not hosts or len(set(hosts)) != len(hosts):
            raise ValueError("invalid service registry")
        if any(not isinstance(host, str) or not HOST.fullmatch(host) for host in hosts):
            raise ValueError("invalid service hostname")


def render(model: dict, version: str) -> bytes:
    validate(model)
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("invalid profile version")
    sections = []

    def add(name, lines):
        sections.append("[" + name + "]\n" + "\n".join(lines))

    add("General", [key + " = " + value for key, value in model["general"].items()])
    add("Proxy", [])
    add("Remote Proxy", [])
    add("Remote Filter", [r["name"] + ' = NameRegex, FilterKey = "' + r["pattern"] + '"' for r in model["filters"]])
    groups = []
    for row in model["groups"]:
        values = [row["type"], *row["members"]]
        values.extend(key + " = " + str(row["options"][key]) for key in OPTIONS[row["type"]])
        values.append("img-url = " + row["icon"])
        groups.append(row["name"] + " = " + ",".join(values))
    add("Proxy Group", groups)
    add("Remote Rule", [r["uri"] + ", policy=" + r["policy"] + ", tag=" + r["tag"] + ", enabled=true" for r in model["remote_rules"]])
    add("Host", [host + " = " + address for host, address in model["hosts"].items()])
    rules = []
    for row in model["rules"]:
        values = [row["type"]] + ([row["value"]] if row["type"] != "FINAL" else [])
        rules.append(",".join([*values, row["policy"], *row["flags"]]))
    add("Rule", rules)
    add("Plugin", [uri + ", enabled=true" for uri in model["plugins"]])
    return ("# LoonKit " + version + "\n\n" + "\n\n".join(sections) + "\n").encode("utf-8")
