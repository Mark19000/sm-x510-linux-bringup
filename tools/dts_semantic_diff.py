#!/usr/bin/env python3
"""Conservative, path-oriented comparison for decompiled DTS files.

The files in this project are a mixture of DTS produced by different ``dtc``
versions.  A textual diff therefore reports harmless differences such as
``&foo`` versus a numeric phandle, labels, and NUL-separated strings.  This
module deliberately implements a small parser instead of depending on ``dtc``
or a third-party DTS library.  It normalises only what can be proven from the
two input trees:

* node identity is its full path (labels are not identity);
* strings are compared as a NUL-separated string list;
* numeric phandle references are mapped to a path when the referenced phandle
  is defined locally, or when the peer property supplies an explicit label at
  that position;
* ``phandle``/``linux,phandle`` numbers are reported as renumbering, not as a
  property change.

Unresolved labels, unresolved numeric references, duplicate paths/labels,
unsupported directives, and parser recovery are surfaced in the result.  A
comparison is marked equivalent only if none of those caveats remain.  The
tool is intended for triage and review, not for proving that two DTBs can be
combined or flashed.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import sys
from collections import defaultdict
from typing import Sequence


_NUMBER_RE = re.compile(r"^[+-]?(?:0[xX][0-9a-fA-F]+|[0-9]+)$")
_HEX_BYTE_RE = re.compile(r"^(?:0[xX])?[0-9a-fA-F]{1,2}$")


@dataclasses.dataclass(frozen=True)
class Token:
    value: str
    kind: str = "word"
    line: int = 1


@dataclasses.dataclass(frozen=True)
class Atom:
    """One scalar from a cells/bytes/raw value."""

    kind: str
    value: object

    def as_text(self) -> str:
        if self.kind == "number":
            return f"0x{int(self.value):x}"
        if self.kind == "ref":
            return f"&{self.value}"
        if self.kind == "ref-name":
            return f"&{self.value}"
        if self.kind == "unresolved-ref":
            return f"?{self.value}"
        if self.kind == "null-ref":
            return "<null-ref>"
        return str(self.value)


@dataclasses.dataclass(frozen=True)
class ValuePart:
    """A typed portion of a property value.

    ``cells`` is flattened for comparison, because dtc may emit
    ``<&foo>, <0x01>`` or ``<0x10 0x01>`` for the same cell stream.
    """

    kind: str
    values: tuple[object, ...]


@dataclasses.dataclass
class Property:
    name: str
    parts: tuple[ValuePart, ...] = ()
    boolean: bool = False
    line: int = 1

    def raw_text(self) -> str:
        if self.boolean:
            return "(boolean)"
        pieces: list[str] = []
        for part in self.parts:
            if part.kind == "strings":
                strings = [json.dumps(str(item), ensure_ascii=False) for item in part.values]
                pieces.append(", ".join(strings))
            elif part.kind == "cells":
                cells = " ".join(
                    item.as_text() if isinstance(item, Atom) else str(item)
                    for item in part.values
                )
                pieces.append(f"<{cells}>")
            elif part.kind == "bytes":
                pieces.append("[" + " ".join(str(item) for item in part.values) + "]")
            else:
                pieces.append(" ".join(str(item) for item in part.values))
        return " ".join(pieces)


@dataclasses.dataclass
class Node:
    path: str
    name: str
    labels: tuple[str, ...] = ()
    properties: dict[str, Property] = dataclasses.field(default_factory=dict)
    children: tuple[str, ...] = ()
    line: int = 1


@dataclasses.dataclass
class DtsTree:
    source: pathlib.Path | str
    nodes: dict[str, Node]
    phandles: dict[int, str]
    labels: dict[str, str]
    issues: list[str]
    unresolved: list[str]
    unsupported: list[str]
    duplicate_paths: list[str]
    duplicate_labels: list[str]

    @property
    def source_name(self) -> str:
        return str(self.source)


class DtsParseError(ValueError):
    """Raised for an unrecoverable DTS syntax error."""


def _decode_dts_string(raw: str) -> str:
    """Decode the small escape subset emitted by ``dtc -O dts``.

    Unknown escapes are retained as the escaped character.  This is less
    surprising for a review tool than Python's broad ``unicode_escape`` codec,
    which can turn malformed input into a different Unicode string.
    """

    out: list[str] = []
    index = 0
    while index < len(raw):
        char = raw[index]
        if char != "\\" or index + 1 >= len(raw):
            out.append(char)
            index += 1
            continue
        index += 1
        escaped = raw[index]
        simple = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v"}
        if escaped in simple:
            out.append(simple[escaped])
            index += 1
        elif escaped in {"0", "a"}:
            out.append("\0" if escaped == "0" else "\a")
            index += 1
        elif escaped == "x" and index + 2 < len(raw):
            digits = raw[index + 1:index + 3]
            if all(item in "0123456789abcdefABCDEF" for item in digits):
                out.append(chr(int(digits, 16)))
                index += 3
            else:
                out.append("x")
                index += 1
        else:
            # DTS uses backslash to quote punctuation as well.
            out.append(escaped)
            index += 1
    return "".join(out)


def _split_dts_string(value: str) -> tuple[str, ...]:
    """Return a canonical DT string-list representation."""

    return tuple(value.split("\0"))


def _parse_int(value: str) -> int | None:
    if not _NUMBER_RE.match(value):
        return None
    try:
        return int(value, 0)
    except ValueError:
        try:
            return int(value, 10)
        except ValueError:
            return None


def _scan(text: str) -> list[Token]:
    """Tokenise enough of DTS to preserve typed property values."""

    tokens: list[Token] = []
    index = 0
    line = 1
    length = len(text)
    punctuation = frozenset("{};=<>[],:&")
    while index < length:
        char = text[index]
        if char.isspace():
            if char == "\n":
                line += 1
            index += 1
            continue
        if text.startswith("//", index):
            end = text.find("\n", index + 2)
            if end < 0:
                break
            line += 1
            index = end + 1
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                raise DtsParseError(f"unterminated comment at line {line}")
            line += text[index:end + 2].count("\n")
            index = end + 2
            continue
        if char == '"':
            start_line = line
            index += 1
            raw: list[str] = []
            while index < length:
                char = text[index]
                if char == '"':
                    break
                if char == "\\" and index + 1 < length:
                    raw.append(char)
                    raw.append(text[index + 1])
                    index += 2
                    continue
                raw.append(char)
                if char == "\n":
                    line += 1
                index += 1
            if index >= length or text[index] != '"':
                raise DtsParseError(f"unterminated string at line {start_line}")
            index += 1
            tokens.append(Token(_decode_dts_string("".join(raw)), "string", start_line))
            continue
        if char in punctuation:
            tokens.append(Token(char, "punct", line))
            index += 1
            continue
        # '/' is both part of the root/directive syntax and a useful token on
        # its own.  Keep it separate so ``/plugin/`` is easy to recognise.
        if char == "/":
            tokens.append(Token(char, "punct", line))
            index += 1
            continue
        start = index
        while index < length:
            current = text[index]
            if current.isspace() or current in punctuation or current in {'"', '/'}:
                break
            index += 1
        if index == start:
            # Backslash outside a string or another unusual character.  Keep
            # it as a one-character raw token and let the parser report it.
            tokens.append(Token(text[index], "raw", line))
            index += 1
        else:
            tokens.append(Token(text[start:index], "word", line))
    return tokens


class _Parser:
    def __init__(self, text: str, source: pathlib.Path | str):
        self.tokens = _scan(text)
        self.index = 0
        self.source = source
        self.issues: list[str] = []
        self.unsupported: list[str] = []
        self.nodes: dict[str, Node] = {}
        self.duplicate_paths: list[str] = []
        self._children: defaultdict[str, list[str]] = defaultdict(list)

    def _peek(self, offset: int = 0) -> Token | None:
        position = self.index + offset
        return self.tokens[position] if position < len(self.tokens) else None

    def _take(self) -> Token:
        token = self._peek()
        if token is None:
            raise DtsParseError(f"unexpected end of file in {self.source}")
        self.index += 1
        return token

    def _skip_until(self, terminators: set[str]) -> None:
        depth = 0
        while self._peek() is not None:
            token = self._take()
            if token.value in "<[{":
                depth += 1
            elif token.value in ">]}" and depth:
                depth -= 1
            elif token.value in terminators and depth == 0:
                return

    def parse(self) -> DtsTree:
        while self._peek() is not None:
            if self._peek().value == ";":
                self._take()
                continue
            if self._is_directive_start():
                self._consume_directive(top_level=True)
                continue
            self._parse_node("/")
            # A valid DTS has one root node.  Continue parsing to report extra
            # fragments rather than silently dropping them.
            if self._peek() is not None:
                self.issues.append(f"extra top-level statement at line {self._peek().line}")

        labels: dict[str, str] = {}
        duplicate_labels: list[str] = []
        for path in sorted(self.nodes):
            node = self.nodes[path]
            for label in node.labels:
                if label in labels and labels[label] != path:
                    duplicate_labels.append(label)
                    self.issues.append(f"duplicate label {label!r}: {labels[label]} and {path}")
                else:
                    labels[label] = path

        phandles: dict[int, str] = {}
        for path in sorted(self.nodes):
            node = self.nodes[path]
            for name in ("phandle", "linux,phandle"):
                prop = node.properties.get(name)
                if prop is None or prop.boolean:
                    continue
                numbers = _direct_numbers(prop)
                if len(numbers) != 1:
                    self.issues.append(f"non-scalar {name} at {path}")
                    continue
                value = numbers[0]
                if value in phandles and phandles[value] != path:
                    self.issues.append(
                        f"duplicate phandle 0x{value:x}: {phandles[value]} and {path}"
                    )
                else:
                    phandles[value] = path

        for parent, children in self._children.items():
            self.nodes[parent].children = tuple(sorted(children))
        self.issues.sort()
        self.unsupported.sort()
        self.duplicate_paths.sort()
        duplicate_labels.sort()
        return DtsTree(
            source=self.source,
            nodes=self.nodes,
            phandles=phandles,
            labels=labels,
            issues=self.issues,
            unresolved=[],
            unsupported=self.unsupported,
            duplicate_paths=self.duplicate_paths,
            duplicate_labels=duplicate_labels,
        )

    def _is_directive_start(self) -> bool:
        # The root node itself is written ``/ {``; only a slash followed by a
        # directive name is a directive statement.
        return (
            self._peek() is not None
            and self._peek().value == "/"
            and self._peek(1) is not None
            and self._peek(1).value != "{"
        )

    def _consume_directive(self, top_level: bool = False) -> None:
        start = self._take()
        name_parts: list[str] = []
        if self._peek() is not None and self._peek().value not in {";", "{"}:
            name_parts.append(self._take().value)
        if self._peek() is not None and self._peek().value == "/":
            name_parts.append(self._take().value)
        name = "".join(name_parts)
        if name in {"dts-v1/", "plugin/", "memreserve/"}:
            self._skip_until({";"})
            return
        # /bits/ is part of a value; callers only reach here for a statement.
        self.unsupported.append(f"unsupported directive /{name} at line {start.line}")
        self._skip_until({";", "{"})
        if self._peek() is not None and self._peek().value == "{":
            self._skip_balanced("{", "}")

    def _skip_balanced(self, opening: str, closing: str) -> None:
        if self._peek() is None or self._peek().value != opening:
            return
        depth = 0
        while self._peek() is not None:
            token = self._take()
            if token.value == opening:
                depth += 1
            elif token.value == closing:
                depth -= 1
                if depth == 0:
                    return

    def _parse_node(self, parent_path: str) -> None:
        labels: list[str] = []
        prefix: list[str] = []
        first = self._peek()
        if first is None:
            return
        while self._peek() is not None:
            token = self._peek()
            if token.value == ":":
                label = prefix.pop() if prefix else ""
                self._take()
                if label:
                    labels.append(label)
                continue
            if token.value == "{":
                self._take()
                name = prefix[-1] if prefix else "/"
                if name == "/":
                    path = "/"
                    parent = None
                else:
                    path = _join_path(parent_path, name)
                    parent = parent_path
                if path in self.nodes:
                    self.duplicate_paths.append(path)
                    self.issues.append(f"duplicate node path {path} at line {token.line}")
                node = Node(path=path, name=name, labels=tuple(labels), line=first.line)
                self.nodes.setdefault(path, node)
                if parent is not None and path not in self._children[parent]:
                    self._children[parent].append(path)
                self._parse_block(path)
                return
            if token.value in {"=", ";"}:
                # A property was encountered where a node was expected.  This
                # can happen after a directive recovery; consume it safely.
                self.issues.append(f"expected node at line {first.line}")
                self._skip_until({";"})
                return
            prefix.append(self._take().value)
        self.issues.append(f"unterminated node at line {first.line}")

    def _parse_block(self, node_path: str) -> None:
        while self._peek() is not None:
            token = self._peek()
            if token.value == "}":
                self._take()
                if self._peek() is not None and self._peek().value == ";":
                    self._take()
                return
            if token.value == ";":
                self._take()
                continue
            if self._is_directive_start():
                self._consume_directive()
                continue
            self._parse_member(node_path)
        self.issues.append(f"unterminated node {node_path}")

    def _parse_member(self, node_path: str) -> None:
        node = self.nodes[node_path]
        prefix: list[str] = []
        labels: list[str] = []
        first = self._peek()
        if first is None:
            return
        while self._peek() is not None:
            token = self._peek()
            if token.value == ":":
                label = prefix.pop() if prefix else ""
                self._take()
                if label:
                    labels.append(label)
                continue
            if token.value == "{":
                self._take()
                name = prefix[-1] if prefix else ""
                if not name:
                    self.issues.append(f"unnamed node at line {first.line}")
                    self._skip_balanced("{", "}")
                    return
                child_path = _join_path(node_path, name)
                if child_path in self.nodes:
                    self.duplicate_paths.append(child_path)
                    self.issues.append(f"duplicate node path {child_path} at line {token.line}")
                child = Node(child_path, name, tuple(labels), line=first.line)
                self.nodes.setdefault(child_path, child)
                if child_path not in self._children[node_path]:
                    self._children[node_path].append(child_path)
                self._parse_block(child_path)
                return
            if token.value == "=":
                self._take()
                name = prefix[-1] if prefix else ""
                if not name:
                    self.issues.append(f"unnamed property at line {first.line}")
                    self._skip_until({";"})
                    return
                value_tokens = self._take_value_tokens()
                node.properties[name] = _parse_property_value(name, value_tokens, first.line)
                return
            if token.value == ";":
                self._take()
                name = prefix[-1] if prefix else ""
                if name:
                    node.properties[name] = Property(name=name, boolean=True, line=first.line)
                else:
                    self.issues.append(f"unnamed property at line {first.line}")
                return
            prefix.append(self._take().value)
        self.issues.append(f"unterminated member at {node_path}:{first.line}")

    def _take_value_tokens(self) -> list[Token]:
        values: list[Token] = []
        depths = {"<": 0, "[": 0, "{": 0}
        closing = {">": "<", "]": "[", "}": "{"}
        while self._peek() is not None:
            token = self._take()
            if token.value == ";" and not any(depths.values()):
                return values
            if token.value in depths:
                depths[token.value] += 1
            elif token.value in closing:
                opener = closing[token.value]
                if depths[opener]:
                    depths[opener] -= 1
                else:
                    self.issues.append(f"unbalanced {token.value} at line {token.line}")
            values.append(token)
        self.issues.append("unterminated property value")
        return values


def _join_path(parent: str, name: str) -> str:
    if parent == "/":
        return "/" + name
    if name.startswith("&"):
        # Targeted overlay nodes are intentionally kept distinct.  The path is
        # not claimed to be the target's effective path.
        return parent + "/" + name
    return parent.rstrip("/") + "/" + name


def _direct_numbers(prop: Property) -> list[int]:
    numbers: list[int] = []
    for part in prop.parts:
        if part.kind != "cells":
            continue
        for atom in part.values:
            if isinstance(atom, Atom) and atom.kind == "number":
                numbers.append(int(atom.value))
            else:
                return []
    return numbers


def _parse_property_value(name: str, tokens: Sequence[Token], line: int) -> Property:
    parts: list[ValuePart] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.value == ",":
            index += 1
            continue
        if token.value == "<":
            index += 1
            atoms: list[Atom] = []
            while index < len(tokens) and tokens[index].value != ">":
                current = tokens[index]
                if current.value == ",":
                    index += 1
                    continue
                if current.value == "&":
                    index += 1
                    if index < len(tokens):
                        atoms.append(Atom("ref-name", tokens[index].value))
                        index += 1
                    else:
                        atoms.append(Atom("unresolved-ref", "missing-label"))
                    continue
                if current.value == "/":
                    # Preserve /bits/ and similar value modifiers as raw
                    # atoms.  The type is intentionally not guessed.
                    raw = current.value
                    index += 1
                    while index < len(tokens) and tokens[index].value not in {" ", ">", ","}:
                        raw += tokens[index].value
                        if tokens[index].value == "/":
                            index += 1
                            break
                        index += 1
                    atoms.append(Atom("raw", raw))
                    continue
                number = _parse_int(current.value)
                if number is not None:
                    atoms.append(Atom("number", number))
                else:
                    atoms.append(Atom("raw", current.value))
                index += 1
            if index < len(tokens) and tokens[index].value == ">":
                index += 1
            parts.append(ValuePart("cells", tuple(atoms)))
            continue
        if token.value == "[":
            index += 1
            values: list[object] = []
            while index < len(tokens) and tokens[index].value != "]":
                current = tokens[index]
                if current.value != ",":
                    if _HEX_BYTE_RE.match(current.value):
                        base = 0 if current.value.lower().startswith("0x") else 16
                        values.append(f"{int(current.value, base):02x}")
                    else:
                        values.append(current.value)
                index += 1
            if index < len(tokens) and tokens[index].value == "]":
                index += 1
            parts.append(ValuePart("bytes", tuple(values)))
            continue
        if token.kind == "string":
            strings: list[str] = []
            while index < len(tokens):
                current = tokens[index]
                if current.kind != "string":
                    break
                strings.extend(_split_dts_string(current.value))
                index += 1
                if index < len(tokens) and tokens[index].value == ",":
                    index += 1
            parts.append(ValuePart("strings", tuple(strings)))
            continue
        # A bare value (including /bits/ outside an angle list) is retained as
        # raw text.  Treat commas as separators only.
        raw: list[str] = []
        while index < len(tokens) and tokens[index].value not in {",", "<", "["}:
            raw.append(tokens[index].value)
            index += 1
        if raw:
            parts.append(ValuePart("raw", tuple(raw)))
    return Property(name=name, parts=tuple(parts), line=line)


def parse_dts(text_or_path: str | pathlib.Path, *, source: pathlib.Path | str | None = None) -> DtsTree:
    """Parse text or a path into a :class:`DtsTree`."""

    # A caller passing ``source=...`` is unambiguously supplying text, even if
    # the synthetic DTS happens to fit on one line.  Without that hint, a
    # string with no newline is treated as a filesystem path for CLI-friendly
    # convenience.
    candidate = str(text_or_path)
    looks_like_dts = any(char in candidate for char in "{};<>=\n")
    if isinstance(text_or_path, pathlib.Path) or (source is None and not looks_like_dts):
        path = pathlib.Path(text_or_path)
        text = path.read_text(encoding="utf-8", errors="replace")
        source = source or path
    else:
        text = str(text_or_path)
        source = source or "<string>"
    return _Parser(text, source).parse()


def _normalise_label(tree: DtsTree, label: str) -> tuple[str, object]:
    if label in tree.labels:
        return "ref", tree.labels[label]
    # Keep the spelling in diagnostics, but compare unresolved external
    # references as one opaque kind.  The comparison remains INCOMPLETE, so
    # this avoids a misleading wall of ``&foo`` versus ``0xffffffff`` rows
    # without claiming that the external targets are identical.
    return "unresolved-ref", "external"


_PURE_REF_PROPERTIES = {
    "target",
    "interrupt-parent",
    "memory-region",
    "nvmem-cells",
    "operating-points-v2",
    "remote-endpoint",
    "backlight",
    "panel",
    "sound-dai",
    "link",
    "links",
    "ref",
    "refs",
}
_REF_PROPERTY_RE = re.compile(
    r"(?:^pinctrl(?:-|$)|(?:^|[-,])(supply|gpio|gpios|reset-gpios|power-domain|domains?)$)"
)


def _looks_like_ref_property(name: str) -> bool:
    if name in _PURE_REF_PROPERTIES:
        return True
    if name.startswith("pinctrl-"):
        return True
    if name in {"gpios", "gpio", "clocks", "resets", "phys", "dmas", "iommus", "mboxes", "pwms", "io-channels", "power-domains"}:
        return True
    if name.endswith(("-supply", "-gpio", "-gpios", "-reset-gpios", "-power-domain")):
        return True
    return bool(_REF_PROPERTY_RE.search(name))


def _flatten_cells(prop: Property) -> list[Atom]:
    atoms: list[Atom] = []
    for part in prop.parts:
        if part.kind == "cells":
            atoms.extend(item for item in part.values if isinstance(item, Atom))
    return atoms


def _has_explicit_ref(prop: Property | None) -> bool:
    if prop is None:
        return False
    return any(atom.kind == "ref-name" for atom in _flatten_cells(prop))


def _canonical_property(
    tree: DtsTree,
    prop: Property,
    peer: Property | None,
    unresolved: list[str],
) -> tuple[object, ...]:
    if prop.boolean:
        return (("boolean", True),)
    peer_atoms = _flatten_cells(peer) if peer is not None else []
    atoms = _flatten_cells(prop)
    peer_explicit = {index for index, atom in enumerate(peer_atoms) if atom.kind == "ref-name"}
    use_ref_context = _looks_like_ref_property(prop.name) or bool(peer_explicit)
    canonical_parts: list[object] = []
    cell_index = 0
    for part in prop.parts:
        if part.kind == "cells":
            canonical_cells: list[object] = []
            for atom in part.values:
                if not isinstance(atom, Atom):
                    canonical_cells.append(("raw", str(atom)))
                    cell_index += 1
                    continue
                if atom.kind == "ref-name":
                    kind, value = _normalise_label(tree, str(atom.value))
                    if kind != "ref":
                        unresolved.append(f"{tree.source_name}: unresolved &{atom.value} in {prop.name}")
                    canonical_cells.append((kind, value))
                elif atom.kind == "number":
                    number = int(atom.value)
                    path = tree.phandles.get(number)
                    explicit_peer = cell_index in peer_explicit
                    # A numeric phandle is mapped only with evidence: a known
                    # reference property or an explicit peer reference.  This
                    # avoids turning arbitrary constants that happen to equal
                    # a phandle into references.
                    if path is not None and use_ref_context and (explicit_peer or _numeric_ref_position(prop.name, cell_index)):
                        canonical_cells.append(("ref", path))
                    elif number == 0 and use_ref_context and (explicit_peer or _numeric_ref_position(prop.name, cell_index)):
                        canonical_cells.append(("null-ref", 0))
                    elif number == 0xFFFFFFFF and use_ref_context:
                        unresolved.append(f"{tree.source_name}: external phandle sentinel in {prop.name}")
                        canonical_cells.append(("unresolved-ref", "external"))
                    elif explicit_peer and path is None:
                        unresolved.append(
                            f"{tree.source_name}: numeric reference 0x{number:x} not defined locally in {prop.name}"
                        )
                        canonical_cells.append(("unresolved-ref", f"0x{number:x}"))
                    else:
                        canonical_cells.append(("number", number))
                else:
                    canonical_cells.append((atom.kind, atom.value))
                cell_index += 1
            canonical_parts.append(("cells", tuple(canonical_cells)))
        elif part.kind == "strings":
            canonical_parts.append(("strings", tuple(str(item) for item in part.values)))
        elif part.kind == "bytes":
            canonical_parts.append(("bytes", tuple(str(item).lower() for item in part.values)))
        else:
            canonical_parts.append((part.kind, tuple(str(item) for item in part.values)))
    # Flatten cells across angle-list grouping.  dtc is free to choose a
    # different grouping around explicit phandle references.
    flattened: list[object] = []
    remainder: list[object] = []
    for item in canonical_parts:
        if item[0] == "cells":
            flattened.extend(item[1])
        else:
            remainder.append(item)
    if flattened and not remainder:
        return (("cells", tuple(flattened)),)
    return tuple(canonical_parts)


def _numeric_ref_position(name: str, index: int) -> bool:
    """Conservative fallback for numeric-only synthetic/reference fields."""

    if name in _PURE_REF_PROPERTIES or name.startswith("pinctrl-"):
        return True
    if name in {"interrupt-parent", "memory-region", "nvmem-cells", "operating-points-v2", "remote-endpoint", "backlight", "panel", "sound-dai", "link", "links", "ref", "refs"}:
        return True
    # In tuple-style bindings the provider phandle is conventionally first;
    # subsequent cells are provider arguments and remain numeric.
    return index == 0 and name in {"clocks", "resets", "gpios", "gpio", "phys", "dmas", "iommus", "mboxes", "pwms", "io-channels", "power-domains"}


@dataclasses.dataclass(frozen=True)
class Difference:
    kind: str
    path: str
    property: str | None = None
    left: object | None = None
    right: object | None = None


@dataclasses.dataclass
class Comparison:
    left: DtsTree
    right: DtsTree
    differences: list[Difference]
    phandle_renumbered: list[tuple[str, int, int]]
    unresolved: list[str]

    @property
    def material_difference_count(self) -> int:
        return len(self.differences)

    @property
    def incomplete(self) -> bool:
        return bool(
            self.unresolved
            or self.left.issues
            or self.right.issues
            or self.left.unsupported
            or self.right.unsupported
            or self.left.duplicate_paths
            or self.right.duplicate_paths
            or self.left.duplicate_labels
            or self.right.duplicate_labels
        )

    @property
    def equivalent(self) -> bool:
        return not self.differences and not self.incomplete

    @property
    def status(self) -> str:
        if self.equivalent:
            return "EQUIVALENT"
        if self.differences:
            return "DIFFERENT (INCOMPLETE)" if self.incomplete else "DIFFERENT"
        return "INCONCLUSIVE"


def compare_trees(left: DtsTree, right: DtsTree) -> Comparison:
    differences: list[Difference] = []
    unresolved: list[str] = []
    left_paths = set(left.nodes)
    right_paths = set(right.nodes)
    for path in sorted(left_paths - right_paths):
        differences.append(Difference("node-removed", path))
    for path in sorted(right_paths - left_paths):
        differences.append(Difference("node-added", path))

    phandle_renumbered: list[tuple[str, int, int]] = []
    left_phandle_paths = {path: value for value, path in left.phandles.items()}
    right_phandle_paths = {path: value for value, path in right.phandles.items()}
    for path in sorted(set(left_phandle_paths) & set(right_phandle_paths)):
        left_value = left_phandle_paths[path]
        right_value = right_phandle_paths[path]
        if left_value != right_value:
            phandle_renumbered.append((path, left_value, right_value))
    for path in sorted(set(left_phandle_paths) - set(right_phandle_paths)):
        differences.append(Difference("phandle-removed", path, "phandle", left_phandle_paths[path], None))
    for path in sorted(set(right_phandle_paths) - set(left_phandle_paths)):
        differences.append(Difference("phandle-added", path, "phandle", None, right_phandle_paths[path]))

    for path in sorted(left_paths & right_paths):
        left_node = left.nodes[path]
        right_node = right.nodes[path]
        left_names = set(left_node.properties) - {"phandle", "linux,phandle"}
        right_names = set(right_node.properties) - {"phandle", "linux,phandle"}
        for name in sorted(left_names - right_names):
            prop = left_node.properties[name]
            differences.append(Difference("property-removed", path, name, prop.raw_text(), None))
        for name in sorted(right_names - left_names):
            prop = right_node.properties[name]
            differences.append(Difference("property-added", path, name, None, prop.raw_text()))
        for name in sorted(left_names & right_names):
            left_prop = left_node.properties[name]
            right_prop = right_node.properties[name]
            left_value = _canonical_property(left, left_prop, right_prop, unresolved)
            right_value = _canonical_property(right, right_prop, left_prop, unresolved)
            if left_value != right_value:
                differences.append(Difference("property-changed", path, name, left_value, right_value))

    # Make the result stable even when parser traversal encountered malformed
    # input.  The original sequence remains useful only for diagnostics.
    differences.sort(key=lambda item: (item.path, item.property or "", item.kind))
    unresolved = sorted(set(unresolved))
    left.unresolved[:] = [item for item in unresolved if item.startswith(left.source_name + ":")]
    right.unresolved[:] = [item for item in unresolved if item.startswith(right.source_name + ":")]
    return Comparison(left, right, differences, phandle_renumbered, unresolved)


def _display_value(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _markdown_cell(value: object) -> str:
    return _display_value(value).replace("`", "\\`")


def render_markdown(comparison: Comparison, *, detail_limit: int = 0) -> str:
    """Render a deterministic review report."""

    left = comparison.left
    right = comparison.right
    lines = [
        "# DTS semantic diff",
        "",
        "This is a conservative path/property comparison. It ignores label spelling,",
        "canonicalises NUL-separated strings, and maps a phandle only when its local",
        "definition or an explicit peer reference proves the target path. An",
        "`INCONCLUSIVE`/`INCOMPLETE` result is not an equivalence claim.",
        "",
        f"- Left: `{left.source_name}`",
        f"- Right: `{right.source_name}`",
        f"- Status: **{comparison.status}**",
        f"- Nodes: {len(left.nodes)} left / {len(right.nodes)} right",
        f"- Material differences: {len(comparison.differences)}",
        f"- Phandle renumberings ignored by path: {len(comparison.phandle_renumbered)}",
        f"- Unresolved references: {len(comparison.unresolved)}",
        "",
    ]
    if comparison.phandle_renumbered:
        lines += ["## Phandle renumbering", "", "| path | left | right |", "|---|---:|---:|"]
        renumbered = comparison.phandle_renumbered
        if detail_limit > 0:
            renumbered = renumbered[:detail_limit]
        for path, left_value, right_value in renumbered:
            lines.append(f"| `{path}` | `0x{left_value:x}` | `0x{right_value:x}` |")
        if len(renumbered) < len(comparison.phandle_renumbered):
            lines.append("")
            lines.append(
                f"Only the first {len(renumbered)} renumberings are shown; total is "
                f"{len(comparison.phandle_renumbered)}."
            )
        lines.append("")
    if comparison.differences:
        lines += ["## Differences by path", "", "| kind | path | property | left | right |", "|---|---|---|---|---|"]
        rows = comparison.differences if detail_limit <= 0 else comparison.differences[:detail_limit]
        for difference in rows:
            property_name = difference.property or "-"
            lines.append(
                f"| `{difference.kind}` | `{difference.path}` | `{property_name}` | "
                f"`{_markdown_cell(difference.left)}` | "
                f"`{_markdown_cell(difference.right)}` |"
            )
        if len(rows) < len(comparison.differences):
            lines.append("")
            lines.append(f"Only the first {len(rows)} differences are shown; total is {len(comparison.differences)}.")
        lines.append("")
    if comparison.unresolved:
        lines += ["## Unresolved/incomplete evidence", "", "The following references were not resolved to a local node; therefore the result cannot be called equivalent:", ""]
        for item in comparison.unresolved if detail_limit <= 0 else comparison.unresolved[:detail_limit]:
            lines.append(f"- `{item}`")
        if detail_limit > 0 and len(comparison.unresolved) > detail_limit:
            lines.append(f"- … {len(comparison.unresolved) - detail_limit} more")
        lines.append("")
    diagnostics = sorted(set(left.issues + right.issues + left.unsupported + right.unsupported))
    if diagnostics:
        lines += ["## Parser diagnostics", ""]
        lines.extend(f"- `{item}`" for item in diagnostics)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(comparison: Comparison) -> str:
    payload = {
        "left": comparison.left.source_name,
        "right": comparison.right.source_name,
        "status": comparison.status,
        "equivalent": comparison.equivalent,
        "nodes": {"left": len(comparison.left.nodes), "right": len(comparison.right.nodes)},
        "material_difference_count": len(comparison.differences),
        "phandle_renumbered": [
            {"path": path, "left": left, "right": right}
            for path, left, right in comparison.phandle_renumbered
        ],
        "unresolved": comparison.unresolved,
        "issues": sorted(set(comparison.left.issues + comparison.right.issues)),
        "unsupported": sorted(set(comparison.left.unsupported + comparison.right.unsupported)),
        "differences": [
            {
                "kind": item.kind,
                "path": item.path,
                "property": item.property,
                "left": item.left,
                "right": item.right,
            }
            for item in comparison.differences
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def compare_paths(left_path: pathlib.Path, right_path: pathlib.Path) -> Comparison:
    return compare_trees(parse_dts(left_path), parse_dts(right_path))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=pathlib.Path, help="left DTS/DTS decompile")
    parser.add_argument("right", type=pathlib.Path, help="right DTS/DTS decompile")
    parser.add_argument("-o", "--output", type=pathlib.Path, help="write report to this path")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--detail-limit", type=int, default=0, help="limit rows/diagnostics (0 = all)")
    args = parser.parse_args(argv)
    try:
        comparison = compare_paths(args.left, args.right)
    except (OSError, DtsParseError, UnicodeError) as error:
        print(f"dts_semantic_diff: {error}", file=sys.stderr)
        return 2
    rendered = render_json(comparison) if args.format == "json" else render_markdown(comparison, detail_limit=args.detail_limit)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if comparison.equivalent else 1


if __name__ == "__main__":
    raise SystemExit(main())
