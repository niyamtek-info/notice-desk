from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString, Tag


SECTION_HEADER_SELECTOR = ".docx-header, header"
SECTION_CONTENT_SELECTOR = ".docx-content"
SECTION_FOOTER_SELECTOR = ".docx-footer, footer"


def _ensure_html_shell(soup: BeautifulSoup) -> tuple[Tag, Tag]:
    html_tag = soup.html
    if html_tag is None:
        html_tag = soup.new_tag("html", attrs={"lang": "en"})
        existing = list(soup.contents)
        for node in existing:
            html_tag.append(node.extract())
        soup.append(html_tag)

    head = html_tag.find("head", recursive=False)
    if head is None:
        head = soup.new_tag("head")
        html_tag.insert(0, head)

    body = html_tag.find("body", recursive=False)
    if body is None:
        body = soup.new_tag("body")
        remaining = [node.extract() for node in list(html_tag.contents) if node is not head]
        html_tag.append(body)
        for node in remaining:
            body.append(node)

    return head, body


def _new_section(soup: BeautifulSoup, class_name: str, tag_name: str = "div") -> Tag:
    return soup.new_tag(tag_name, attrs={"class": class_name})


def _append_nonempty(target: Tag, node) -> None:
    if isinstance(node, NavigableString):
        if str(node).strip():
            wrapper = target.builder.soup.new_tag("p") if getattr(target, "builder", None) else None
            if wrapper is not None:
                wrapper.string = str(node).strip()
                target.append(wrapper)
        return
    if isinstance(node, Tag):
        target.append(node)


def _normalize_wrapper_structure(soup: BeautifulSoup, body: Tag) -> None:
    root = body.find(class_="docx-root", recursive=False)
    if root is None:
        root = soup.new_tag("div", attrs={"class": "docx-root"})
        existing = [node.extract() for node in list(body.contents)]
        body.append(root)
        for node in existing:
            root.append(node)

    header = root.select_one(":scope > .docx-header")
    content = root.select_one(":scope > .docx-content")
    footer = root.select_one(":scope > .docx-footer")

    if header is None:
        source = root.select_one(SECTION_HEADER_SELECTOR)
        if source is not None and source.parent is root:
            source.name = "header"
            source["class"] = ["docx-header"]
            header = source
        else:
            header = _new_section(soup, "docx-header", "header")
            root.insert(0, header)

    if footer is None:
        source = root.select_one(SECTION_FOOTER_SELECTOR)
        if source is not None and source.parent is root:
            source.name = "footer"
            source["class"] = ["docx-footer"]
            footer = source
        else:
            footer = _new_section(soup, "docx-footer", "footer")
            root.append(footer)

    if content is None:
        content = _new_section(soup, "docx-content")
        insertion_index = 1 if header in root.contents else len(root.contents)
        root.insert(insertion_index, content)

    loose_nodes = []
    for child in list(root.contents):
        if child is header or child is content or child is footer:
            continue
        loose_nodes.append(child.extract())

    for child in loose_nodes:
        if isinstance(child, NavigableString) and not str(child).strip():
            continue
        content.append(child)

    for section, tag_name, class_name in (
        (header, "header", "docx-header"),
        (content, "div", "docx-content"),
        (footer, "footer", "docx-footer"),
    ):
        section.name = tag_name
        section["class"] = [class_name]

    for section in (header, content, footer):
        empty_strings = [node for node in section.contents if isinstance(node, NavigableString) and not str(node).strip()]
        for node in empty_strings:
            node.extract()


def _normalize_elements(soup: BeautifulSoup) -> None:
    content = soup.select_one(".docx-root > .docx-content")
    if content is None:
        return

    for table in content.find_all("table"):
        classes = set(table.get("class", []) or [])
        if "docx-table" not in classes:
            classes.add("docx-table")
        table["class"] = list(classes)
        style = table.get("style", "")
        if "width:" not in style:
            style = f"{style}; width:100%" if style else "width:100%"
        if "border-collapse:" not in style:
            style = f"{style}; border-collapse:collapse" if style else "border-collapse:collapse"
        if "table-layout:" not in style:
            style = f"{style}; table-layout:fixed" if style else "table-layout:fixed"
        table["style"] = style.strip("; ")

    for paragraph in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
        style = paragraph.get("style", "")
        if "margin:" not in style and "margin-bottom:" not in style:
            style = f"{style}; margin:0" if style else "margin:0"
        if "white-space:" not in style:
            style = f"{style}; white-space:pre-wrap" if style else "white-space:pre-wrap"
        paragraph["style"] = style.strip("; ")


def normalize_docx_html(html_text: str) -> str:
    soup = BeautifulSoup(html_text or "", "html.parser")
    _ensure_html_shell(soup)
    _, body = _ensure_html_shell(soup)
    _normalize_wrapper_structure(soup, body)
    _normalize_elements(soup)
    return str(soup)
