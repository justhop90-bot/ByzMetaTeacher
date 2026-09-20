from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\AoE2DE"
    r"\resources\_common\ai\ByzTeacher\ByzMetaTeacher.per"
)


@dataclass
class Token:
    kind: str
    text: str
    start: int
    end: int


@dataclass
class Node:
    open_pos: int
    close_pos: int
    items: list[Token | "Node"]


class ParseError(Exception):
    pass


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(source)

    while i < n:
        ch = source[i]

        if ch.isspace():
            i += 1
            continue

        # // comment
        if source.startswith("//", i):
            j = source.find("\n", i)
            i = n if j == -1 else j
            continue

        # ; comment
        if ch == ";":
            j = source.find("\n", i)
            i = n if j == -1 else j
            continue

        if ch == "(":
            tokens.append(Token("open", ch, i, i + 1))
            i += 1
            continue

        if ch == ")":
            tokens.append(Token("close", ch, i, i + 1))
            i += 1
            continue

        # Quoted string
        if ch == '"':
            start = i
            i += 1
            escaped = False

            while i < n:
                c = source[i]

                if escaped:
                    escaped = False
                    i += 1
                    continue

                if c == "\\":
                    escaped = True
                    i += 1
                    continue

                if c == '"':
                    i += 1
                    break

                i += 1

            else:
                raise ParseError(f"Unterminated string at offset {start}")

            tokens.append(Token("atom", source[start:i], start, i))
            continue

        # Bare atom
        start = i
        while i < n:
            c = source[i]
            if c.isspace() or c in "()":
                break
            if source.startswith("//", i):
                break
            if c == ";":
                break
            i += 1

        if start == i:
            raise ParseError(f"Unable to tokenize source at offset {i}")

        tokens.append(Token("atom", source[start:i], start, i))

    return tokens


def parse(tokens: list[Token]) -> list[Node]:
    roots: list[Node] = []
    stack: list[Node] = []

    for token in tokens:
        if token.kind == "open":
            node = Node(token.start, -1, [])
            if stack:
                stack[-1].items.append(node)
            else:
                roots.append(node)
            stack.append(node)

        elif token.kind == "close":
            if not stack:
                raise ParseError(
                    f"Unexpected ')' at offset {token.start}"
                )
            node = stack.pop()
            node.close_pos = token.start

        else:
            if not stack:
                raise ParseError(
                    f"Top-level atom '{token.text}' at offset {token.start}"
                )
            stack[-1].items.append(token)

    if stack:
        node = stack[-1]
        raise ParseError(
            f"Unclosed '(' starting at offset {node.open_pos}"
        )

    return roots


def first_atom(node: Node) -> str | None:
    if not node.items:
        return None

    first = node.items[0]
    if isinstance(first, Token):
        return first.text

    return None


def collect_nodes(node: Node) -> list[Node]:
    found = [node]

    for item in node.items:
        if isinstance(item, Node):
            found.extend(collect_nodes(item))

    return found


def all_nodes(roots: list[Node]) -> list[Node]:
    result: list[Node] = []

    for root in roots:
        result.extend(collect_nodes(root))

    return result


def goal_nodes(nodes: list[Node]) -> list[Node]:
    return [
        node
        for node in nodes
        if first_atom(node) == "goal"
    ]


def or_nodes(nodes: list[Node]) -> list[Node]:
    return [
        node
        for node in nodes
        if first_atom(node) == "or"
    ]


def atom_children(node: Node) -> list[Token | Node]:
    return node.items[1:]


def invalid_goal_comparisons(nodes: list[Node]) -> list[tuple[Node, str]]:
    bad: list[tuple[Node, str]] = []

    for node in goal_nodes(nodes):
        items = atom_children(node)

        # Expected valid form:
        #   (goal GOAL-ID VALUE)
        #
        # Invalid comparison form:
        #   (goal GOAL-ID != VALUE)
        #   (goal GOAL-ID == VALUE)
        # and potentially unsupported:
        #   < > <= >=
        if len(items) != 3:
            continue

        op = items[1]
        if isinstance(op, Token) and op.text in {
            "==", "!=", "<", ">", "<=", ">="
        }:
            bad.append((node, op.text))

    return bad


def multi_argument_ors(nodes: list[Node]) -> list[Node]:
    bad: list[Node] = []

    for node in or_nodes(nodes):
        child_count = len(atom_children(node))

        # Binary OR is exactly:
        #   (or A B)
        if child_count > 2:
            bad.append(node)

    return bad


def plan_goal_edit(node: Node, operator: str) -> list[tuple[int, int, str]]:
    items = atom_children(node)

    if len(items) != 3:
        raise ValueError(
            f"Goal at offset {node.open_pos} has unexpected shape."
        )

    op = items[1]
    if not isinstance(op, Token) or op.text != operator:
        raise ValueError(
            f"Goal operator mismatch at offset {node.open_pos}."
        )

    if operator == "==":
        # (goal G == V)
        # -> (goal G  V)
        #
        # Only remove the invalid operator token.
        return [
            (op.start, op.end, ""),
        ]

    if operator == "!=":
        # (goal G != V)
        # -> (not (goal G  V))
        #
        # Wrap the original goal node in (not ...).
        return [
            (node.open_pos, node.open_pos, "(not "),
            (op.start, op.end, ""),
            (node.close_pos, node.close_pos, ")"),
        ]

    raise ValueError(
        f"Unsupported goal comparison '{operator}' at offset {node.open_pos}."
    )fix_byzmetateacher_arity.py


def plan_or_flatten(node: Node) -> list[tuple[int, int, str]]:
    children = atom_children(node)

    if len(children) <= 2:
        return []

    edits: list[tuple[int, int, str]] = []

    # Example:
    #
    # (or A B C D)
    #
    # becomes:
    #
    # (or A (or B (or C D)))
    #
    # Insert nested "(or " before every child from B through C,
    # then add the matching closing parens before the outer close.
    for child in children[1:-1]:
        start = child.open_pos if isinstance(child, Node) else child.start
        edits.append((start, start, "(or "))

    edits.append(
        (
            node.close_pos,
            node.close_pos,
            ")" * (len(children) - 2),
        )
    )

    return edits


def validate_clean(source: str) -> None:
    tokens = tokenize(source)
    roots = parse(tokens)
    nodes = all_nodes(roots)

    unsupported: list[str] = []

    for node, operator in invalid_goal_comparisons(nodes):
        if operator in {"<", ">", "<=", ">="}:
            unsupported.append(
                f"unsupported goal comparison '{operator}' "
                f"at source offset {node.open_pos}"
            )

    if unsupported:
        raise ParseError(
            "Unsupported goal comparisons remain:\n"
            + "\n".join(unsupported)
        )

    remaining_or = multi_argument_ors(nodes)
    if remaining_or:
        offsets = ", ".join(str(node.open_pos) for node in remaining_or)
        raise ParseError(
            "Multi-argument OR expressions remain at offsets: "
            + offsets
        )

    # Any remaining == / != forms are now considered invalid.
    remaining_goal = invalid_goal_comparisons(nodes)
    if remaining_goal:
        details = ", ".join(
            f"{op}@{node.open_pos}"
            for node, op in remaining_goal
        )
        raise ParseError(
            "Invalid goal comparison forms remain: " + details
        )


def apply_edits(source: str, edits: list[tuple[int, int, str]]) -> str:
    # Reject overlapping edits unless they are identical insertions.
    normalized: list[tuple[int, int, str]] = sorted(
        edits,
        key=lambda e: (e[0], e[1]),
    )

    for i in range(len(normalized) - 1):
        a_start, a_end, _ = normalized[i]
        b_start, b_end, _ = normalized[i + 1]

        if a_end > b_start and not (
            a_start == a_end == b_start == b_end
        ):
            raise ValueError(
                "Overlapping edits detected."
            )

    # Apply from right to left so original offsets remain valid.
    output = source

    for start, end, replacement in sorted(
        edits,
        key=lambda e: (e[0], e[1]),
        reverse=True,
    ):
        output = output[:start] + replacement + output[end:]

    return output


def build_edits(source: str) -> tuple[list[tuple[int, int, str]], int, int]:
    tokens = tokenize(source)
    roots = parse(tokens)
    nodes = all_nodes(roots)

    edits: list[tuple[int, int, str]] = []
    goal_count = 0
    or_count = 0

    for node, operator in invalid_goal_comparisons(nodes):
        if operator in {"<", ">", "<=", ">="}:
            raise ParseError(
                f"Unsupported goal comparison '{operator}' "
                f"at source offset {node.open_pos}. "
                "The fixer will not guess the intended semantics."
            )

        edits.extend(plan_goal_edit(node, operator))
        goal_count += 1

    for node in multi_argument_ors(nodes):
        edits.extend(plan_or_flatten(node))
        or_count += 1

    return edits, goal_count, or_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Formatting-preserving fixer for ByzMetaTeacher.per. "
            "Repairs invalid goal comparisons and flattens "
            "multi-argument OR expressions into binary ORs."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=TARGET,
        help="Path to ByzMetaTeacher.per",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report required fixes without modifying the file.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a .pre_goal_or_fix.bak backup.",
    )

    args = parser.parse_args()
    path: Path = args.path

    if not path.exists():
        print(f"ERROR: File not found:\n{path}", file=sys.stderr)
        return 2

    raw = path.read_bytes()

    bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
    payload = raw[len(bom):]

    # Preserve the existing newline bytes exactly.
    if b"\r\n" in payload:
        newline = b"\r\n"
    elif b"\r" in payload:
        newline = b"\r"
    else:
        newline = b"\n"

    try:
        source = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        print(
            f"ERROR: Could not decode {path} as UTF-8: {exc}",
            file=sys.stderr,
        )
        return 2

    try:
        edits, goal_count, or_count = build_edits(source)
    except (ParseError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not edits:
        print("No invalid goal comparisons or multi-argument ORs found.")
        return 0

    print(f"Target: {path}")
    print(f"Goal comparisons to repair: {goal_count}")
    print(f"Multi-argument OR expressions to flatten: {or_count}")
    print(f"Total formatting-preserving edits: {len(edits)}")

    if args.check:
        print("\nCHECK ONLY: file was not modified.")
        return 0

    backup = path.with_name(path.name + ".pre_goal_or_fix.bak")

    if not args.no_backup:
        if backup.exists():
            print(
                f"ERROR: Backup already exists:\n{backup}\n"
                "Refusing to overwrite it.",
                file=sys.stderr,
            )
            return 2

        backup.write_bytes(raw)
        print(f"Backup created: {backup}")

    try:
        fixed = apply_edits(source, edits)

        # Preserve original newline convention if the source somehow
        # changed it during processing.
        if newline == b"\r\n":
            fixed = fixed.replace("\r\n", "\n").replace("\n", "\r\n")
        elif newline == b"\r":
            fixed = fixed.replace("\r\n", "\n").replace("\n", "\r")
        else:
            fixed = fixed.replace("\r\n", "\n")

        validate_clean(fixed)
    except (ParseError, ValueError) as exc:
        print(
            f"ERROR: Post-fix validation failed: {exc}",
            file=sys.stderr,
        )
        return 2

    output = bom + fixed.encode("utf-8")
    path.write_bytes(output)

    print("\nFIX APPLIED.")
    print("Post-fix structural validation passed.")
    print(f"Updated: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())