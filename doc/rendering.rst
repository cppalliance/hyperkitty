===========================
Hyperkitty's Markdown Guide
===========================

Hyperkitty supports rich text rending of Emails. Due to the fact the most
people writing emails aren't *always* aware that they are writing markdown, a
prime philosophy of renderer is to prevent common plain-text to be mangled by
rendering them as markdown. Only **some** of the Markdown rules actually work.


Headers
-------

Markdown headers using ``##`` syntax or using ``==`` or ``--`` are not
supported in Hyperkitty. This is because these characters are very often used
in different context and results in untentional ``<h1>`` and ``<h2>`` tags in
the rendered output.


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


Images
------

Remote image support for Hyperkitty is optional and disabled by default due to
the fact that they can often be used to track users. Hyperkitty also doesn't
have support to upload attachments when replying from web interface, which
makes it hard to support inline images.

It is however possible to allow rendering of inline images, and might be
considered in future.

To enable the support for images, administrators can add
``HYPERKITTY_RENDER_INLINE_IMAGE = True`` to Hyperkitty's ``settings.py``.

::

   ![Image's alt text](http://image.com/file.png "Image Title")
