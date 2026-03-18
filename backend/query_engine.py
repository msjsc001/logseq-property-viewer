from dataclasses import dataclass
from typing import Dict, List


class QuerySyntaxError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


@dataclass(frozen=True)
class QueryNode:
    kind: str
    value: str | None = None
    key: str | None = None
    left: "QueryNode | None" = None
    right: "QueryNode | None" = None


def _normalize(text: str, *, case_sensitive: bool = False) -> str:
    normalized = str(text or "").strip()
    return normalized if case_sensitive else normalized.casefold()


def tokenize(query: str) -> List[Token]:
    tokens: List[Token] = []
    index = 0
    length = len(query)

    while index < length:
        char = query[index]
        if char.isspace():
            index += 1
            continue
        if char in {":", "~"}:
            tokens.append(Token(char, char))
            index += 1
            continue
        if char == '"':
            index += 1
            start = index
            value_chars: List[str] = []
            escaped = False
            while index < length:
                current = query[index]
                if escaped:
                    value_chars.append(current)
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    break
                else:
                    value_chars.append(current)
                index += 1
            if index >= length or query[index] != '"':
                raise QuerySyntaxError("INVALID_QUERY_SYNTAX", "未闭合的引号")
            tokens.append(Token("WORD", "".join(value_chars)))
            index += 1
            continue

        start = index
        while index < length and not query[index].isspace() and query[index] not in {":", "~"}:
            index += 1
        value = query[start:index]
        upper_value = value.upper()
        if upper_value == "AND":
            tokens.append(Token("AND", value))
        elif upper_value == "OR":
            tokens.append(Token("OR", value))
        else:
            tokens.append(Token("WORD", value))

    return tokens


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.index = 0

    def current(self) -> Token | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index]

    def consume(self, expected: str | None = None) -> Token:
        token = self.current()
        if token is None:
            raise QuerySyntaxError("INVALID_QUERY_SYNTAX", "查询语句不完整")
        if expected and token.kind != expected:
            raise QuerySyntaxError("INVALID_QUERY_SYNTAX", f"缺少 {expected}")
        self.index += 1
        return token

    def parse(self) -> QueryNode:
        if not self.tokens:
            raise QuerySyntaxError("EMPTY_QUERY", "请输入查询语句")
        expression = self.parse_or()
        if self.current() is not None:
            raise QuerySyntaxError("INVALID_QUERY_SYNTAX", "存在无法识别的查询片段")
        return expression

    def parse_or(self) -> QueryNode:
        node = self.parse_and()
        while self.current() and self.current().kind == "OR":
            self.consume("OR")
            node = QueryNode("or", left=node, right=self.parse_and())
        return node

    def parse_and(self) -> QueryNode:
        node = self.parse_term()
        while self.current() and self.current().kind == "AND":
            self.consume("AND")
            node = QueryNode("and", left=node, right=self.parse_term())
        return node

    def parse_term(self) -> QueryNode:
        token = self.consume("WORD")
        next_token = self.current()
        if next_token and next_token.kind == ":":
            self.consume(":")
            if token.value.casefold() == "has":
                key = self.consume("WORD").value.strip()
                if not key:
                    raise QuerySyntaxError("INVALID_QUERY_SYNTAX", "has 查询必须提供属性名")
                return QueryNode("has", key=key)
            value_token = self.consume("WORD")
            key = token.value.strip()
            value = value_token.value.strip()
            if not key or not value:
                raise QuerySyntaxError("INVALID_QUERY_SYNTAX", "精确匹配必须提供属性名和值")
            return QueryNode("exact", key=key, value=value)
        if next_token and next_token.kind == "~":
            self.consume("~")
            value_token = self.consume("WORD")
            key = token.value.strip()
            value = value_token.value.strip()
            if not key or not value:
                raise QuerySyntaxError("INVALID_QUERY_SYNTAX", "模糊匹配必须提供属性名和值")
            return QueryNode("fuzzy", key=key, value=value)
        return QueryNode("text", value=token.value.strip())


def parse_query(query: str) -> QueryNode:
    return Parser(tokenize(query)).parse()


def _values_match(left: str, right: str, *, case_sensitive: bool = False) -> bool:
    return _normalize(left, case_sensitive=case_sensitive) == _normalize(
        right,
        case_sensitive=case_sensitive,
    )


def _contains_text(haystack: str, needle: str, *, case_sensitive: bool = False) -> bool:
    return _normalize(needle, case_sensitive=case_sensitive) in _normalize(
        haystack,
        case_sensitive=case_sensitive,
    )


def _iter_properties(block: Dict) -> List[tuple[str, str]]:
    return [
        (str(key).strip(), str(value or ""))
        for key, value in block.get("properties", {}).items()
    ]


def _match_text(block: Dict, text: str, *, case_sensitive: bool = False) -> bool:
    properties = block.get("properties", {})
    haystacks = [
        block.get("page", ""),
        block.get("block_content", ""),
    ]
    haystacks.extend(properties.keys())
    haystacks.extend(str(value) for value in properties.values())
    return any(_contains_text(str(item), text, case_sensitive=case_sensitive) for item in haystacks)


def evaluate_query(node: QueryNode, block: Dict, *, case_sensitive: bool = False) -> bool:
    properties = _iter_properties(block)

    if node.kind == "and":
        return bool(node.left and evaluate_query(node.left, block, case_sensitive=case_sensitive)) and bool(
            node.right and evaluate_query(node.right, block, case_sensitive=case_sensitive)
        )
    if node.kind == "or":
        return bool(node.left and evaluate_query(node.left, block, case_sensitive=case_sensitive)) or bool(
            node.right and evaluate_query(node.right, block, case_sensitive=case_sensitive)
        )
    if node.kind == "has":
        return any(_values_match(key, node.key or "", case_sensitive=case_sensitive) for key, _ in properties)
    if node.kind == "exact":
        return any(
            _values_match(key, node.key or "", case_sensitive=case_sensitive)
            and _values_match(value, node.value or "", case_sensitive=case_sensitive)
            for key, value in properties
        )
    if node.kind == "fuzzy":
        return any(
            _values_match(key, node.key or "", case_sensitive=case_sensitive)
            and _contains_text(value, node.value or "", case_sensitive=case_sensitive)
            for key, value in properties
        )
    if node.kind == "text":
        return _match_text(block, node.value or "", case_sensitive=case_sensitive)
    return False


def search_blocks(all_blocks: List[Dict], query: str, *, case_sensitive: bool = False) -> List[Dict]:
    node = parse_query(query.strip())
    return [block for block in all_blocks if evaluate_query(node, block, case_sensitive=case_sensitive)]
