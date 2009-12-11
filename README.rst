====
loaf
====


Installation
------------

The easiest way to get loaf is if you have setuptools_ installed::

	easy_install loaf

Without setuptools, it's still pretty easy. Download the loaf.tgz file from 
`loaf's Cheeseshop page`_, untar it and run::

	python setup.py install

.. _loaf's Cheeseshop page: http://pypi.python.org/pypi/loaf/
.. _setuptools: http://peak.telecommunity.com/DevCenter/EasyInstall


Help and development
====================

If you'd like to help out, you can fork the project
at http://github.com/whitmo/loaf and report any bugs 
at http://github.com/loaf/loaf/issues.


PostGIS
=======

Start postgres::

   $ bin/postgres -D /Users/whit/dev/loaf/var/pgdata

or::

   $ bin/pg_ctl -D /Users/whit/dev/loaf/var/pgdata -l logfile start