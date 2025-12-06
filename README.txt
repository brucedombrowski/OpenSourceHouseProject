HOUSE WBS SYSTEM — MAC RESTORE GUIDE
==================================

This archive restores a full Django-based WBS system
including tree structure, schedule fields, costs, and dependencies.

---

REQUIREMENTS:
-------------
MacOS (Intel or Apple Silicon)
Python 3.10+
Internet connection

---

STEP 1: INSTALL PYTHON (if missing)
-----------------------------------
Check version:
    python3 --version

If not found:
    https://www.python.org/downloads/macos/

---

STEP 2: CREATE PROJECT FOLDER
------------------------------
cd ~
mkdir house_wbs_crud
cd house_wbs_crud

---

STEP 3: CREATE VIRTUAL ENVIRONMENT
---------------------------------
python3 -m venv venv
source venv/bin/activate

---

STEP 4: INSTALL DEPENDENCIES
----------------------------
pip install django django-mptt

---

STEP 5: CREATE PROJECT STRUCTURE
--------------------------------
django-admin startproject house_wbs .
python manage.py startapp wbs

---

STEP 6: COPY PROJECT FILES
--------------------------
Copy the following directories from your original project into this folder:

    house_wbs/
    wbs/

Overwrite any existing ones created by Django.

---

STEP 7: MIGRATE DATABASE
------------------------
python manage.py makemigrations
python manage.py migrate

---

STEP 8: CREATE ADMIN USER
-------------------------
python manage.py createsuperuser

---

STEP 9: RESTORE DATA
--------------------
Place files from backup folder into project root:

    wbs_items.csv
    dependencies.csv

Then:

    python manage.py import_wbs_csv wbs_items.csv --update
    python manage.py import_dependencies_csv dependencies.csv --update

---

STEP 10: RUN SERVER
-------------------
python manage.py runserver

---

ACCESS:
--------
Admin panel:
    http://127.0.0.1:8000/admin/

Gantt chart:
    http://127.0.0.1:8000/gantt/

---

DONE.
