import re

from django.conf import settings

import mistune
from mistune.plugins.url import url
from mistune.util import safe_entity


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

    def emphasis(self, text, marker):
        """Emphasis with marker included."""
        return super().emphasis(marker + text + marker)

    def strong(self, text, marker):
        """Strong with marker included."""
        return super().strong(marker + text + marker)

    def text(self, text, marker=None):
        # We had to override this because for some reason, text inside emphasis
        # and strong will receive the attrs of parents too, like "marker" in
        # our case. We don't really need to do anything with it.
        return text

    def _md_style_img(self, src, title, alt):
        """Markdown syntax for images. """
        title = f'"{title}"' if title else ''
        return '![{alt}]({src} {title})'.format(
            src=src, title=title, alt=alt)

    def image(self, alt, url, title=None):
        """Render image if configured to do so.

        HYPERKITTY_RENDER_INLINE_IMAGE configuration allows for
        rendering of inline images in the markdown. This is disabled by
        default since embeded images can cause problems.
        """
        if getattr(settings, 'HYPERKITTY_RENDER_INLINE_IMAGE', False):
            return super().image(alt, url, title)
        return self._md_style_img(url, title, alt)

    def link(self, text, url, title=None):
        """URL link renderer that truncates the length of the URL.

        This only does it for the URLs that are not hyperlinks by just literal
        URLs (text=None) so text is same as URL.
        It also adds target=“_blank” so that the URLs open in a new tab.
        """
        # text can be none of same as url in case of autolink parsing. This
        # will truncate the length of the URL in both cases but preserve
        # the actual URL destination in the hyperlink.
        if text is None or text == url:
            text = url
            if len(text) > 76:
                text = url[:76] + '...'

        s = '<a target="_blank" href="' + self.safe_url(url) + '"'
        if title:
            s += ' title="' + safe_entity(title) + '"'
        return s + '>' + (text or url) + '</a>'


class InlineParser(mistune.inline_parser.InlineParser):
    """Modified parser that returns the marker along with emphasized text.
    We do this so we can apply styling without modifying the text itself, like
    removing `**` or `__`. Since both the markers have same styling effect,
    the renderer currently doesn’t get which marker was used, it just gets
    ‘emphasis’ or ‘strong’ node.
    We also null the ESCAPE string to prevent removing backslash escapes
    without unwanted side effects from removing the 'escapre' rule.
    """

    def parse_emphasis(self, m, state):
        end_pos = super().parse_emphasis(m, state)
        last_token = state.tokens[-1].copy()
        marker = m.group(0)
        last_token['attrs'] = {'marker': marker}
        state.tokens[-1] = last_token
        return end_pos

    def parse_escape(self, m, state):
        # Upstream version will use `unescape_char` on the text, which
        # removes the `\` in _some_ cases. This will remove the use of
        # unescape char since we don't want to do escaping at all.
        state.append_token({
            'type': 'text',
            'raw': m.group(0),
        })
        return m.end()


def remove_header_rules(rules):
    rules = list(rules)
    for rule in ('setex_header', 'axt_heading'):
        if rule in rules:
            rules.remove(rule)
    return rules


class BlockParser(mistune.block_parser.BlockParser):
    """A copy of Mistune's block parser with header parsing rules removed."""
    DEFAULT_RULES = remove_header_rules(
        mistune.block_parser.BlockParser.DEFAULT_RULES)


OUTLOOK_REPLY_PATTERN = (
    r'^-------- Original message --------\n'
    r'(?P<reply_text>[\s\S]+)'                    # everything after newline
)


def parse_outlook_reply(block, m, state):
    """Parser for outlook style replies."""
    text = m.group('reply_text')
    reply_token = '-------- Original message --------\n'
    state.append_token({
        'type': 'block_quote',
        'children': [{'type': 'paragraph', 'text': reply_token + text}],
        })
    return m.end() + 1


def plugin_outlook_reply(md):
    md.block.register(
        'outlook_reply', OUTLOOK_REPLY_PATTERN, parse_outlook_reply)


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
    md.block.register('signature', SIGNATURE_PATTERN, parse_signature)

    # md.block.rules.insert(0,  'signature')
    if md.renderer and md.renderer.NAME == 'html':
        md.renderer.register('signature', render_html_signature)


def plugin_disable_markdown(md):
    """This plugin disables most of the rules in mistune.

    This uses mistune to do only block_quote parsing and then some inline rules
    to render an email as simple text instead of rich text. This makes such
    that the code path is same for MailingLists that do and don't enable the
    markdown rendering.
    """
    md.block.rules = ['block_quote']
    md.block.block_quote_rules = ['block_quote', 'blank_line']
    md.block.list_rules = []
    md.inline.rules = ['inline_html', 'auto_link']


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
    md.block.register('pgp', PGP_SIGNATURE_MATCH, parse_pgp_signature)
    # md.block.rules.append('pgp')
    if md.renderer and md.renderer.NAME == 'html':
        md.renderer.register('pgp', render_pgp_signature)


renderer = MyRenderer()
markdown_renderer = mistune.Markdown(
    renderer=renderer,
    inline=InlineParser(hard_wrap=False),
    block=BlockParser(),
    plugins=[
        plugin_outlook_reply,
        plugin_pgp_signature,
        plugin_signature,
        url,
        ])


# The only difference between the markdown and this renderer is
# plugin_disable_markdown which disables all but a few markdown processing
# rules that results in a regularly formatted email.
text_renderer = mistune.Markdown(
    renderer=renderer,
    inline=InlineParser(hard_wrap=False),
    block=BlockParser(),
    plugins=[plugin_disable_markdown,
             plugin_pgp_signature,
             plugin_signature,
             url,
             ])
