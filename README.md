# CSIT314 Renovation Platform

Django group project for matching renovation customers with interior designers.

Implemented so far: authentication, User Admin profile management, and account
creation, viewing, updating, suspension, and reactivation. Profile search is also
available. Account search and the remaining designer/customer/management features
are still to be implemented.

## Set up your own development environment

Install Git and Python. The current project has been tested with Python 3.9.

Clone the repository:

```bash
git clone https://github.com/easonloo/CSIT314-Renovation-Platform.git
cd CSIT314-Renovation-Platform
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies and create your local database:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
```

Each new developer creates their own local administrator login:

```bash
python manage.py createsuperuser
```

Create the initial profiles and link that login to the application's User Admin
profile. Replace `your_username` with the username you just created:

```bash
python manage.py setup_profiles --admin-username your_username
python manage.py runserver
```

Open <http://127.0.0.1:8000/login/> and use your local administrator credentials.
The Django admin interface is at <http://127.0.0.1:8000/admin/>.

If you already have a local administrator account, reuse it. You do not need to
create another one. `setup_profiles` can be run again without duplicating profiles
or accounts, and it preserves existing suspension statuses and descriptions.

Your SQLite database, virtual environment, and passwords belong to your local
development environment. They are excluded from new commits. Share model changes
through migrations; each teammate runs `python manage.py migrate` after pulling.

The development server generates a private `.django-secret-key` file on first
run. This file is ignored by Git. You can instead supply the `DJANGO_SECRET_KEY`
environment variable. These settings are for local development.

## Run tests

```bash
python manage.py test accounts
python manage.py check
```

## Automated checks (CI)

The **Django CI** GitHub Actions workflow runs on pushes and pull requests into
`main`. It installs `requirements.txt`, checks Django configuration, checks for
missing migrations, and runs the complete test suite on Python 3.9.

See the results in the repository's **Actions** tab or in a pull request's checks.
You can also run it manually from **Actions → Django CI → Run workflow** once the
workflow is on `main`. Django creates a temporary test database; your local
database and administrator credentials are not used.

This workflow checks the code. Deployment can be added separately when the group
is ready for CD.

## Work with the group

The repository owner invites teammates through GitHub repository **Settings →
Collaborators → Add people**. Teammates need to accept the invitation before
pushing their branches.

Start each feature from the latest `main`:

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/company-management
```

Use a different descriptive branch name for each feature. After coding and testing:

```bash
git add accounts companies templates static
git commit -m "Implement company management"
git push -u origin feature/company-management
```

Stage the paths relevant to your change, including new migration files. Open a pull
request into `main` on GitHub and ask another group member to review it before
merging. Each developer uses their own database and credentials.

## Project structure

| Path | Purpose |
| --- | --- |
| `accounts/` | Authentication, user profiles, and account management |
| `companies/` | Interior designer company information |
| `projects/` | Current and past design projects |
| `favourites/` | Customer saved projects |
| `categories/` | Project categories |
| `reports/` | Platform reports |
| `templates/` | Django HTML templates |
| `static/` | Shared CSS and other static assets |
| `config/` | Django settings and root routes |

Use the assignment's Boundary–Control–Entity structure: request handling and
templates form the boundary, controller classes coordinate operations, and models
represent persistent entities. Record user stories, tests, sprint work, and review
evidence for the group report.
