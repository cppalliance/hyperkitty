============================
Hyperkitty's Email Rendering
============================

Hyperkitty supports rich text rendering of Emails. Due to the fact the most
people writing emails aren't *always* aware that they are writing markdown, a
prime philosophy of renderer is to prevent common plain-text to be mangled by
rendering them as markdown.

Hyperkitty currently recognizes some rules that are used to parse the content of
an email and render them as HTML with some CSS styling applied.


Enabling Markdown Rendering
===========================

In Postorius UI, under :guilabel:`Setttings` -> :guilabel:`Archiving` ->
:guilabel:`Archive Rendering Mode`, MailingList owners can choose between
``Plain Text`` and ``Markdown text``.

Hyperkitty will use that to choose between the simple text renderer and
markdown renderer.


Text Renderer
=============

Text renderer is the default renderer for the Emails since the default value of
``archive_rendering_mode`` setting for MailingLists is ``text``. Text renderer
supports the following rules only:


* :ref:`signature-rule`
* :ref:`pgp-signature-rule`
* :ref:`autolink-rule`
* :ref:`quote-rule`

Markdown Renderer
=================

Markdown renderer support all the rendering rules mentioned in the
:ref:`rendering-rules` section below.


.. versionadded:: 1.3.4


.. _rendering-rules:

Rendering Rules
===============

Rules are essentially markup that are given special meaning such that they
affect how the rendered text looks. Apart from well known Markdown rules
(which are documented later in this page), there are some other rules that is
supported by Hyperkitty's renderer that make sense in the context of an Email.


.. _signature-rule:

Signature Rule
--------------

Email signatures are often delimited by ``--<SPACE>\n``. That is recognized as
the boundary of the email and
:py:func:`hyperkitty.lib.renderer.plugin_signature` parses that to produce a
greyed out signature at the bottom of the email. An **empty space** after two
dashes ``--`` is important and used as a standard email signature delimiter.

For example, something like::

  --
  Thanks,
  My Name
  http://example.com


.. _pgp-signature-rule:

PGP Signature Rule
------------------

PGP signature rule recognizes inline PGP signatures that looks like this::

      ----BEGIN PGP SIGNED MESSAGE-----
      This is the text.
      -----BEGIN PGP SIGNATURE-----
      iQEXYZXYZ
      -----END PGP SIGNATURE-----

It is parsed and collapsed into a paragraph with a quote switch (``...PGP
SIGNATURE...``) to expand the collapsed signature.

.. _autolink-rule:

Autolink Rule
-------------

This recognizes the URLs in the text which may or may not be included in angle
brackets (``<http://example.com>``) and converts them to Hyperlinks. It will
also truncate the text to 76 characters with following ``...`` characters if
the length of the URL is longer than 76 characters.

This rule will also convert Email addresses into ``mailto:aperson@example.com``
URLs. It does not verify the validity of the Email address or even if the email
address is a valid email address. The parsing is naive in many ways.


.. _quote-rule:

Quote Rule
----------

Or, Blockquote rule. This rule recognizes the lines starting with one or more
``>`` and converts them to blockquotes. They are also collapsed with a switch
(``...``) for expanding and collapsing each section. Hyperkitty currently will
parse upto 6 levels of nested quotes.

A different color styling is provided for each level of blockquote to make it
easy to differentiate between a user's reply and the previous user's reply and
so on and so forth.

For example, each level is indicated with a ``>``::


  > This is level 1 quote
  > > This is Level 2 quote
  > > > This level 3 quote.

Each of them are collapsed with their own quote switch (``...``) to expand or
collapse them.

The rendering of the blockquote can often times be found to be buggy, where
text from a higher level quoting will appear under lower level quote when there
are sentence breaks. Like for example::


  > > > This line of sentence will be broken unintentionally
  > > into the lower
  > > > level because of the improper folding of the email text
  > > by
  > > > some of the email clients.

This type of text will appear with a mixed level of quoting and can often times
be very hard to read. This is caused by email client adding hard line breaks in
the sentences when replying which makes it impossible to differentiate between
the level of quote.

Hyperkitty's current parser is unable to deal with these embarrassing quote
wraps and will unfortunately present the text as mixed levels of quotes. As the
current parser evolves, it *might* be possible to provide a better rendering
experience for this with some heuristics.


Image Rule
----------

Remote image support for Hyperkitty is optional and disabled by default due to
the fact that they can often be used to track users. Hyperkitty also doesn't
have support to upload attachments when replying from web interface, which
makes it hard to support inline images.

To enable the support for images, administrators can add
``HYPERKITTY_RENDER_INLINE_IMAGE = True`` to Hyperkitty's ``settings.py``.

The default value of above setting is ``False`` and all Markdown image syntax
is just ignored. If the above setting is set to True, the images are rendered
inline with the text.

::

   ![Image's alt text](http://image.com/file.png "Image Title")


Lists
-----
::

   * List Items
   * List Item 2
     * List Item 3
     * List Item 4


   - List Item
   - List Item 2


Bold
----
::

   **Bold Text**


Italics
-------
::

   *Italics*


Horizontal Rule
---------------
::

   ---

   ***

Code
----
::

   `inline code for text`

   ```
   Multi-line code segment
   ```

       Code can also be indented by 4 spaces without any backticks.

Hyperlink
---------
::

   [Text](https://url)


   [Text][1]


   [1]: https://URL


Footnotes
---------
::

   This text has a footnote reference[^note]

   [^note]: Foonotes for testing.


Headers
-------

Markdown headers using ``##`` syntax or using ``==`` or ``--`` are not
supported in Hyperkitty. This is because these characters are very often used
in different context and results in untentional ``<h1>`` and ``<h2>`` tags in
the rendered output.


Extending Hyperkitty Renderer
=============================

Hyperkitty uses the `mistune <https://pypi.org/project/mistune/>`_ library as
the renderer but customizes the rendering rules to tailor the rendering
behavior to its liking. Many of the above mentioned rules are implemented as
mistune plugins using their standard plugin interface.

As it has been mentioned in the first paragraph of this page, the default set
of rules that are enabled in Hyperkitty is going to be limited by what can be
assumed in a unstructured plain text email.

But, new rendering rules that conform the above design can be added or
contributed to Hyperkitty. It is possible to also extend the renderer to
support optional rules that can be enabled by site administrators if they
choose to do so. These rules would have to be `mistune plugins
<https://mistune.readthedocs.io/en/latest/plugins.html>`_ and need to be either
a 3rd party package or contributed to Hyperkitty.
