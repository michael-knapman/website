#!/usr/bin/env python3
"""Tests for static_site_generator.py. Standard library only.

Run from the repo root:

    python3 -m unittest discover -s tests -v
"""

import html.parser
import os
import pathlib
import re
import sys
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import static_site_generator as ssg

PUBLIC = ROOT / "public"
CONTENT = ROOT / "content"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class UlParentChecker(html.parser.HTMLParser):
    """Records the parent tag of every <ul> element."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []
        self.ul_parents = []

    def handle_starttag(self, tag, attrs):
        if tag == "ul":
            self.ul_parents.append(self.stack[-1] if self.stack else None)
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self.stack.remove(tag)


class LinkCollector(html.parser.HTMLParser):
    """Collects href/src/srcset values from a page."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.links = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if not value:
                continue
            if name in ("href", "src"):
                self.links.append(value)
            elif name in ("srcset", "imagesrcset"):
                for entry in value.split(","):
                    parts = entry.strip().split()
                    if parts:
                        self.links.append(parts[0])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def style_asset_urls(html):
    """url(...) references from <style> blocks, with CSS comments stripped."""
    urls = []
    for block in re.findall(r"<style[^>]*>(.*?)</style>", html, re.DOTALL):
        block = re.sub(r"/\*.*?\*/", "", block, flags=re.DOTALL)
        urls.extend(re.findall(r"url\(\s*['\"]?([^'\"\)\s]+)", block))
    return urls


EXTERNAL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


def resolve_link(page_path, link):
    """Map a page-local link to a repo path, or None if it needs no file."""
    clean = link.split("#", 1)[0].split("?", 1)[0].strip()
    if not clean or EXTERNAL_RE.match(clean) or clean.startswith("//"):
        return None
    if clean.startswith("/"):
        return PUBLIC / clean.lstrip("/")
    return pathlib.Path(os.path.normpath(page_path.parent / clean))


def sample_tree():
    """A small sitemap tree: a section landing page with two children."""
    kids = [
        ssg.PageNode("housekeeping/ai-use.html", "AI Use"),
        ssg.PageNode("housekeeping/inspiration.html", "Inspiration"),
    ]
    landing = ssg.PageNode("housekeeping.html", "Housekeeping", children=kids)
    return [ssg.PageNode("index.html", "Home"), landing]


# ---------------------------------------------------------------------------
# Escaping / markdown conversion
# ---------------------------------------------------------------------------

class TestEscape(unittest.TestCase):
    def test_ampersands_and_brackets_escaped(self):
        self.assertEqual(ssg.escape_html("Fish & <Chips>"),
                         "Fish &amp; &lt;Chips&gt;")

    def test_quotes_escaped(self):
        out = ssg.escape_html('say "hi" & bye')
        self.assertNotIn('"', out)
        self.assertIn("&quot;", out)

    def test_autolink_quote_cannot_break_out_of_href(self):
        out = ssg.inline_html('<https://e.com/"onmouseover="x>')
        self.assertIn("<a href=", out)
        self.assertNotIn('"onmouseover', out)


class TestParagraph(unittest.TestCase):
    def test_hard_break_is_real_br_tag(self):
        out = ssg.render_paragraph(["Background art:  ", "Tamagotchi"])
        self.assertIn("<br>", out)
        self.assertNotIn("&lt;br", out)

    def test_last_line_break_dropped(self):
        out = ssg.render_paragraph(["only line  "])
        self.assertNotIn("<br>", out)

    def test_text_escaped_but_br_not(self):
        out = ssg.render_paragraph(["Fish & Chips  ", "yum"])
        self.assertIn("Fish &amp; Chips<br>", out)

    def test_autolink_still_linked(self):
        out = ssg.render_paragraph(["see <https://e.com> now"])
        self.assertIn('<a href="https://e.com">https://e.com</a>', out)


class TestMarkdown(unittest.TestCase):
    def test_heading(self):
        title, body = ssg.convert_markdown_to_html("# Hello\n")
        self.assertEqual(title, "Hello")
        self.assertIn("<h1>Hello</h1>", body)

    def test_paragraph_block_not_double_escaped(self):
        title, body = ssg.convert_markdown_to_html("a & b  \nc\n")
        self.assertIn("a &amp; b<br>", body)
        self.assertNotIn("&amp;amp;", body)

    def test_bullet_list(self):
        _, body = ssg.convert_markdown_to_html("* one\n* two\n")
        self.assertIn("<ul>", body)
        self.assertIn("<li>two</li>", body)

    def test_table(self):
        md = "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
        _, body = ssg.convert_markdown_to_html(md)
        self.assertIn("<th>a</th>", body)
        self.assertIn("<td>2</td>", body)


class TestPaths(unittest.TestCase):
    def test_rel_href(self):
        self.assertEqual(ssg.rel_href("", "a.html"), "a.html")
        self.assertEqual(ssg.rel_href("sec", "a.html"), "../a.html")
        self.assertEqual(ssg.rel_href("a/b", "c.html"), "../../c.html")

    def test_extract_title(self):
        self.assertEqual(
            ssg.extract_title("<html><title>Hi</title></html>", "f.html"), "Hi")
        self.assertEqual(ssg.extract_title("<html></html>", "blah.html"),
                         "blah")
        # Entities in <title> come back unescaped: callers escape exactly
        # once for their own context (no Raison D&amp;#x27;Etre).
        self.assertEqual(
            ssg.extract_title("<title>Raison D&#x27;Etre</title>", "f.html"),
            "Raison D'Etre")


# ---------------------------------------------------------------------------
# Sidebar sitemap rendering
# ---------------------------------------------------------------------------

class TestNav(unittest.TestCase):
    def check_valid_nesting(self, lines):
        checker = UlParentChecker()
        checker.feed("<ul>\n" + "\n".join(lines) + "\n</ul>")
        for parent in checker.ul_parents:
            self.assertNotEqual(parent, "ul",
                                "a <ul> must nest inside an <li>, not a <ul>")

    def test_expanded_branch_nests_validly(self):
        lines = ssg.render_nav(sample_tree(), "housekeeping",
                               "housekeeping/ai-use.html")
        text = "\n".join(lines)
        self.assertIn("housekeeping/ai-use.html", text)
        self.check_valid_nesting(lines)

    def test_collapsed_branch_hides_children(self):
        lines = ssg.render_nav(sample_tree(), "", "index.html")
        text = "\n".join(lines)
        self.assertNotIn("housekeeping/ai-use.html", text)
        self.check_valid_nesting(lines)

    def test_group_node_nests_validly(self):
        group = ssg.GroupNode("docs", children=[
            ssg.PageNode("docs/a.html", "A"),
        ])
        lines = ssg.render_nav([group], "docs", "docs/a.html")
        self.assertIn("docs/a.html", "\n".join(lines))
        self.check_valid_nesting(lines)


# ---------------------------------------------------------------------------
# Idempotency: running the build twice must not change or nest output
# ---------------------------------------------------------------------------

class TestIdempotency(unittest.TestCase):
    def inject(self, html_text, rel="index.html"):
        fake_sitemap = SimpleNamespace(root=[])
        return ssg.inject_into_page(html_text, rel, fake_sitemap)

    def skeleton(self, body="<p>Hello</p>"):
        return ("<!DOCTYPE html>\n<html><head>\n<title>T</title>\n</head>\n"
                f"<body>\n{body}\n</body>\n</html>")

    def test_double_inject_identical(self):
        # Injection converges: re-running over built output changes nothing.
        once = self.inject(self.skeleton())
        twice = self.inject(once)
        thrice = self.inject(twice)
        self.assertEqual(twice, thrice)

    def test_single_content_box(self):
        out = self.inject(self.skeleton())
        self.assertEqual(out.count('<main class="content-box">'), 1)

    def test_nocontentbox_opts_out(self):
        html_text = self.skeleton("<!-- nocontentbox -->\n<p>Raw</p>")
        out = self.inject(html_text)
        self.assertNotIn('<main class="content-box">', out)


# ---------------------------------------------------------------------------
# Whole-repo checks against public/ and content/
# ---------------------------------------------------------------------------

class TestRepo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = sorted(PUBLIC.rglob("*.html"))

    def test_no_escaped_br_leftover(self):
        bad = [p.relative_to(ROOT).as_posix() for p in self.pages
               if "&lt;br" in p.read_text(encoding="utf-8")]
        self.assertEqual(bad, [])

    def test_no_double_escaping(self):
        bad = [p.relative_to(ROOT).as_posix() for p in self.pages
               if re.search(r"&amp;(amp|lt|gt|quot);",
                            p.read_text(encoding="utf-8"))]
        self.assertEqual(bad, [])

    def test_generated_markers_recognized(self):
        """Every 'Generated by' marker must match GENERATED_RE, or the
        build would mistreat the page as hand-written (or prune it)."""
        bad = []
        for path in self.pages:
            text = path.read_text(encoding="utf-8")
            for comment in re.findall(r"<!--.*?-->", text, re.DOTALL):
                if "Generated by" in comment \
                        and not ssg.GENERATED_RE.search(comment):
                    bad.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(bad, [])

    def test_markdown_sources_have_pages(self):
        missing = []
        for md in sorted(CONTENT.rglob("*.md")):
            rel = md.relative_to(CONTENT).as_posix()
            html_rel = rel[: -len(".md")] + ".html"
            if not (PUBLIC / html_rel).exists():
                missing.append(html_rel)
        self.assertEqual(missing, [])

    def test_internal_links_resolve(self):
        missing = []
        for path in self.pages:
            text = path.read_text(encoding="utf-8")
            collector = LinkCollector()
            collector.feed(text)
            links = collector.links + style_asset_urls(text)
            for link in links:
                target = resolve_link(path, link)
                if target is not None and not target.exists():
                    missing.append(
                        f"{path.relative_to(ROOT).as_posix()} -> {link}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
