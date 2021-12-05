import re

from django.conf import settings

import mistune
from mistune.plugins.extra import plugin_url
from mistune.util import escape_html, escape_url


class MyRenderer(mistune.HTMLRenderer):
    """Modified HTML renderer.

    This renderer changes a couple of things in the default renderer:
    - Add a quoted-switch to toggle blockquotes.
    - Add the marker along with the emphasis and strong.
    - Optionally render Image tags depending on RENDER_INLINE_IMAGE setting,
      which is off by default to prevent remote images being rendered inline
      as they are used for tracking and can be privacy violating.

    """

    def block_quote(self, text):
        """Returns a rendered blockquote with quote-text class and a
        quote-switched classed hyperlink that can collapse the next quote-text
        using JS.
        """
        return (
            f'<div class="quoted-switch"><a href="#">...</a></div>'
            f'<blockquote class="blockquote quoted-text">{text}</blockquote>')

    def emphasis(self, marker, text):
        """Emphasis with marker included."""
        return super().emphasis(marker + text + marker)

    def strong(self, marker, text):
        """Strong with marker included."""
        return super().strong(marker + text + marker)

    def _md_style_img(self, src, title, alt):
        """Markdown syntax for images. """
        title = f'"{title}"' if title else ''
        return '![{alt}]({src} {title})'.format(
            src=src, title=title, alt=alt)

    def image(self, src, alt_text, title):
        """Render image if configured to do so.

        HYPERKITTY_RENDER_INLINE_IMAGE configuration allows for
        rendering of inline images in the markdown. This is disabled by
        default since embeded images can cause problems.
        """
        if getattr(settings, 'HYPERKITTY_RENDER_INLINE_IMAGE', False):
            return super().image(src, alt_text, title, )
        return self._md_style_img(src, title, alt_text)

    def link(self, link, text=None, title=None):
        """URL link renderer that truncates the length of the URL.

        This only does it for the URLs that are not hyperlinks by just literal
        URLs (text=None) so text is same as URL.
        It also adds target=“_blank” so that the URLs open in a new tab.
        """
        if text is None:
            text = link
            if len(text) > 76:
                text = link[:76] + '...'

        s = '<a target="_blank" href="' + self._safe_url(link) + '"'
        if title:
            s += ' title="' + escape_html(title) + '"'
        return s + '>' + (text or link) + '</a>'


class InlineParser(mistune.inline_parser.InlineParser):
    """Modified parser that returns the marker along with emphasized text.
    We do this so we can apply styling without modifying the text itself, like
    removing `**` or `__`. Since both the markers have same styling effect,
    the renderer currently doesn’t get which marker was used, it just gets
    ‘emphasis’ or ‘strong’ node.
    """

    def tokenize_emphasis(self, m, state):
        marker = m.group(1)
        text = m.group(2)
        if len(marker) == 1:
            return 'emphasis', marker, self.render(text, state)
        return 'strong', marker, self.render(text, state)

    # This is an override for a fix that should be in mistune.
    # https://github.com/lepture/mistune/pull/276
    def parse_auto_link(self, m, state):
        if state.get('_in_link'):
            return 'text', m.group(0)

        text = m.group(1)
        if ('@' in text and
            not text.lower().startswith('mailto:') and
                not text.lower().startswith('http')):
            link = 'mailto:' + text
        else:
            link = text
        return 'link', escape_url(link), text


def remove_header_rules(rules):
    rules = list(rules)
    for rule in ('setex_header', 'axt_heading'):
        if rule in rules:
            rules.remove(rule)
    return rules


class BlockParser(mistune.block_parser.BlockParser):
    """A copy of Mistune's block parser with header parsing rules removed."""
    RULE_NAMES = remove_header_rules(
        mistune.block_parser.BlockParser.RULE_NAMES)


# Signature Plugin looks for signature pattern in email content and converts it
# into a muted text.
SIGNATURE_PATTERN = re.compile(
    r'^-- \n'        # --<empty space><newline>
    r'([\s\S]+)',     # Everything after newline.,
    re.M
)


def parse_signature(block, m, state):
    """Parser for signature type returns an AST node."""
    return {'type': 'signature', 'text': m.group(0), }


def render_html_signature(signature_text):
    """Render a signature as HTML."""
    return f'<div class="text-muted">{signature_text}</div>'


def plugin_signature(md):
    """Signature Plugin looks for signature pattern in email content and
    converts it into a muted text.

    It only provides an HTML renderer because that is the only one needed.
    """
    md.block.register_rule('signature', SIGNATURE_PATTERN, parse_signature)

    md.block.rules.insert(0,  'signature')
    if md.renderer.NAME == 'html':
        md.renderer.register('signature', render_html_signature)


def plugin_disable_markdown(md):
    """This plugin disables most of the rules in mistune.

    This uses mistune to do only block_quote parsing and then some inline rules
    to render an email as simple text instead of rich text. This makes such
    that the code path is same for MailingLists that do and don't enable the
    markdown rendering.
    """
    md.block.rules = ['block_quote']
    md.inline.rules = ['escape', 'inline_html', 'auto_link']


# PGP Signature plugin parses inline pgp signatures from Emails and converts
# them into quoted text so that they can be collapsed.
PGP_SIGNATURE_MATCH = re.compile(
    r"^.*(BEGIN PGP SIGNATURE).*$"
    r"([\s\S]+)"
    r"^.*(END PGP SIGNATURE).*$",
    re.M)


def parse_pgp_signature(block, m, state):
    """Return a parsed pgp node."""
    return {'type': 'pgp', 'text': m.group(0)}


def render_pgp_signature(text):
    """Render pgp signature with a quote-switch and quoted-text.

    This allows collapsing pgp signatures.
    """
    return (f'<div class="quoted-switch"><a href="#">...PGP SIGNATURE...</a>'
            f'</div><div class="pgp quoted-text">{text}</div>')


def plugin_pgp_signature(md):
    """PGP signature plugin adds support to collapse pgp signature in emails

    It parses BEGIN PGP SIGNATURE and END PGP SIGNATURE and collapses content
    in between them.
    """
    md.block.register_rule('pgp', PGP_SIGNATURE_MATCH, parse_pgp_signature)
    md.block.rules.append('pgp')
    if md.renderer.NAME == 'html':
        md.renderer.register('pgp', render_pgp_signature)


renderer = MyRenderer(escape=True)
markdown_renderer = mistune.Markdown(
    renderer=renderer,
    inline=InlineParser(renderer, hard_wrap=False),
    block=BlockParser(),
    plugins=[plugin_pgp_signature, plugin_signature, plugin_url])


# The only difference between the markdown and this renderer is
# plugin_disable_markdown which disables all but a few markdown processing
# rules that results in a regularly formatted email.
text_renderer = mistune.Markdown(
    renderer=renderer,
    inline=InlineParser(renderer, hard_wrap=False),
    block=BlockParser(),
    plugins=[plugin_disable_markdown,
             plugin_pgp_signature,
             plugin_signature,
             plugin_url,
             ])
