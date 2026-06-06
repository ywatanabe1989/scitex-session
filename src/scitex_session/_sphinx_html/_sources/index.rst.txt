scitex-session
==============

``@stx.session`` decorator + lifecycle management. Parse CLI args from a
function signature, configure logging + matplotlib, run the function,
write outputs to ``script_out/<status>/<session_id>/`` (or a single
``.tar.gz`` when ``archive_format`` is set), and clean up on exit.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api
