MapleSoft plug-in
=====================

The `LabManager <http://github.com/gateway4labs/labmanager/>`_ provides an API for
supporting more Remote Laboratory Management Systems (RLMS). This project is the
implementation for the `MapleSoft
<http://www.maplesoft.com/products/mobiusproject/studentapps/>`_ virtual apps.

Usage
-----

First install the module::

  $ pip install git+https://github.com/gateway4labs/rlms_maplesoft.git

Then add it in the LabManager's ``config.py``::

  RLMS = ['maplesoft', ... ]

Profit!
