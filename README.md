gnucash-django
==============

A mobile-friendly Web frontend for GnuCash, primarily written using Django.

Features
--------

 - View transactions in a GnuCash account, along with their "opposing
   account"

 - Filter by opposing account, transaction description, or transaction post
   date

 - Change the opposing account of any transaction and create rules for future
   transactions

 - Import QIF files and automatically categorize transactions according to the
   saved rules

 - More features planned (graphs, budgeting, etc.)

Requirements
------------

 - Django 1.3 or higher

 - Python GnuCash API installed (currently this is only used in the code that
   imports QIF files)

 - A GnuCash file that uses a database backend (tested with MySQL; should work
   with Postgres or SQLite as well)

 - (Optional) The Python `psutil` module

Installation
------------

 - Download the application code into a folder:

        git clone git://github.com/nylen/gnucash-django.git
        cd gnucash-django

 - Copy `settings.example.py` to `settings.py` and fill in values for all
   places where the file contains three asterisks (`***`).  At this point
   you'll need to set up a MySQL database and username, if you haven't done so
   already.  Currently this must be done manually.

 - Create the database structure: `./manage.py syncdb`

 - In the previous step, you should have been prompted to create a Django
   superuser.  If not, or you didn't create one, do that now by running
   `./manage.py createsuperuser`.  This will be your login to the site.

 - There are two options for starting the application:

   1. Django development server: `./manage.py runserver`

   2. Configure Apache to host the application with mod\_wsgi.  Here is an
      example:

            WSGIDaemonProcess site.com processes=2 threads=15
            WSGIProcessGroup site.com

            WSGIScriptAlias /gnucash-django /path/to/gnucash-django/apache/money.wsgi
            <Location /gnucash-django>
              # This setup will allow everyone access to the application.
              # Even though visitors will have to log in, this is probably
              # still not a good idea and you should use Apache auth here.
              Order deny,allow
              Allow from all
            </Location>

      More information about configuring mod\_wsgi is on the mod\_wsgi website:
      http://code.google.com/p/modwsgi/

 - Browse to the site and log in as the superuser you created earlier.  Example
   URLs:
    - Django development server: `http://localhost:8000/`
    - Apache and mod\_wsgi: `http://localhost/gnucash-django/`

 - **NOTE**: Even though all views are set up to require authentication, this
   application has **NOT** been written with security in mind.  Therefore, it
   is advisable to secure it using HTTPS and Apache authentication, or to
   disallow public access to the application.

