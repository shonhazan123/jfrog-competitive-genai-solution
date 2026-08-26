from selectolax.parser import HTMLParser
from app.services.normalization.elements import Element, ElementKind

DROP = {"script", "style", "nav", "footer", "noscript", "svg", "form", "aside"}
TAG_KINDS = {"p": ElementKind.paragraph, "li": ElementKind.list_item,
             "blockquote": ElementKind.quote, "pre": ElementKind.code_block,
             "figcaption": ElementKind.caption}

def parse_html(html: str) -> list[Element]:
    tree = HTMLParser(html)
    for tag in DROP:
        for node in tree.css(tag):
            node.decompose()

    elements: list[Element] = []
    path: list[str] = []
    order = 0

    for node in tree.css("h1, h2, h3, h4, h5, h6, p, li, blockquote, pre, figcaption, tr"):
        text = " ".join(node.text(separator=" ").split())
        if not text:
            continue

        if node.tag.startswith("h") and len(node.tag) == 2 and node.tag[1].isdigit():
            level = int(node.tag[1])
            del path[level - 1:]
            path.append(text)
            elements.append(Element(ElementKind.heading, text, order, level=level,
                                    path=tuple(path[:-1])))
        elif node.tag == "tr":
            cells = [" ".join(c.text(separator=" ").split())
                     for c in node.css("td, th")]
            elements.append(Element(ElementKind.table_row, " │ ".join(cells), order,
                                    path=tuple(path), attrs={"cells": cells}))
        else:
            elements.append(Element(TAG_KINDS[node.tag], text, order, path=tuple(path)))
        order += 1

    return elements
