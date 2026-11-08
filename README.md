# CSIT314 Renovation Platform

Django group project for matching renovation customers with interior designers.

Implemented so far: authentication and User Admin account/profile management;
Interior Designer company information and project portfolio management; and
customer project search, favourites, and reviews. Platform Management can manage
categories and generate daily, weekly, and monthly reports, including PDF downloads.
Interior Designers can create, view,
update, delete, and search their current and past Interior Design Projects (IDPs).

## Set up your own development environment

Install Git and the latest Python 3.12 patch release. Use Python 3.12 for this
project, even if another version is also installed. The shared dependencies in
`requirements.txt` pin Django 5.2 LTS and Pillow 13.0.0.

Clone the repository:

```bash
git clone https://github.com/easonloo/CSIT314-Renovation-Platform.git
cd CSIT314-Renovation-Platform
```

On macOS or Linux:

```bash
python3.12 -m venv .venv312
source .venv312/bin/activate
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv312
.venv312\Scripts\Activate.ps1
```

Install dependencies and create your local database:

```bash
python --version
python -m pip install --upgrade pip
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

The `setup_profiles` command creates the initial user profiles and demo
Interior Designer, Customer, and Platform Management accounts below. It is
safe to run again; existing demo accounts and profiles are not duplicated.

The setup command also creates six demo Interior Designer accounts, company
records, and three sample projects for each designer, with a mix of current and
past projects. The projects use the sample images in `media/sample_idp/` so the
portfolio screens are populated for local testing. Their default username and
password combinations are:

- `designer_aurora` / `Designer@123`
- `designer_bloom` / `Designer@456`
- `designer_cove` / `Designer@789`
- `designer_ember` / `Designer@101`
- `designer_harbor` / `Designer@202`
- `designer_luna` / `Designer@303`

The setup command also creates demo Customer accounts with sample reviews.
Customers can leave one 1–5 star rating and optional comment per IDP, whether
current or past, then update or delete their own review:

- `customer_demo` / `Customer@123`
- `customer_jordan` / `Customer@456`

The setup command also creates two demo Platform Management accounts for
testing category management and platform reports:

- `platform_manager_1` / `Platform@123`
- `platform_manager_2` / `Platform@456`

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

## Generate the assignment demonstration dataset

After activating `.venv312` and applying migrations, run:

```bash
python manage.py generate_demo_data
```

This adds the following synthetic dataset to your configured local database:

| Record type | New dataset size |
| --- | ---: |
| Users and their linked user accounts | 202 each |
| Interior Designer companies | 100 |
| Project categories | 100 |
| Current projects | 100 |
| Past projects | 100 |
| Favourites | 300 |
| Project view events | 1,000 |
| Customer reviews | 200 |

The 202 accounts comprise 100 designers, 100 customers, one User Admin and one
Platform Management user. The four required role profiles are created if missing
and reused otherwise. Existing custom profiles remain in place. Your database
totals also include any records you already had.

Use these application logins at <http://127.0.0.1:8000/login/>:

| Role | Username |
| --- | --- |
| User Admin | `demo314_admin` |
| Interior Designer | `demo314_designer_001` |
| Customer | `demo314_customer_001` |
| Platform Management | `demo314_pm` |

The initial password for all newly generated accounts is `Demo314!Pass2026`.
These are application roles; the command creates ordinary Django users. Every
tenth generated designer/customer starts suspended so account status management
can be demonstrated. The four logins above start active when newly created.
Existing profile/account suspension states and passwords are preserved.

Names and review text use seeded random data. Contact details use synthetic
addresses and reserved `.test` domains. Projects use category-matched virtual
room renders from `media/demo_idp_catalog/` when available. Creation and activity dates span today, the current week/month,
and older periods; activity follows the related user/project creation dates.
Project view and shortlist counters are calculated from their actual related
records, including later manual activity on the generated projects.

Running the command again with the same options reuses generated records.
Usernames, category names and project titles within each company identify the
dataset: keep these identifiers unchanged for exact repeat runs. Other edits,
passwords and suspension statuses remain intact. Changing the count or seed can
add more records; it does not shrink the existing dataset. A conflicting username
stops generation and rolls back the run instead of reassigning the existing user.

For a smaller, separate dataset or a different seed:

```bash
python manage.py generate_demo_data --count 10 --prefix small_demo --seed 7
```

`--count` accepts 1–1,000 and controls the number of designers, customers,
companies and categories. Project and activity counts scale with it. You can set
an initial password for new accounts with `--password`. Use
`python manage.py help generate_demo_data` for the available options. Teammates
can generate their own local data with the same command.

`DemoDataController` in `accounts/demo_data.py` is an administrative seed-data
utility. It creates records and controls transactions directly, separately from
the 48 application user-story controllers described below. Generator regression
tests run with `python manage.py test accounts.test_demo_data`.

## Category-matched project images

The demo image catalog contains 20 AI-generated interior renders, covering the
20 room types used by the data generator. Kitchen projects use a kitchen render,
bathrooms use a bathroom render, and bedrooms, balconies, offices and other
spaces have their own corresponding images. These files are shared project
assets in `media/demo_idp_catalog/`. The prompts and generation method are
recorded in `media/demo_idp_catalog/generation_manifest.json`.

New projects created by `generate_demo_data` select images from their category.
For existing demo projects, preview and then apply the matching images with:

```bash
python manage.py assign_demo_images --dry-run
python manage.py assign_demo_images
```

The assignment command replaces missing images, the five original numbered
sample placeholders, and older catalog selections that no longer match a
project's category. Uploaded photos are preserved. It updates the image reference
without changing project details, dates, interest counts or related records.
Repeated assignment leaves correctly matched images in place.

The app labels catalog images **Virtual demo render** on project cards and
details so their source is clear. Generic categories such as Residential use the
project title to identify a room, or a living room render for a whole-home
project. If the corresponding catalog file is missing, the command reports it
and retains the current image.

## Run tests

```bash
python -m pip check
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Automated checks (CI)

The **Django CI** GitHub Actions workflow runs on pushes and pull requests into
`main`. It installs `requirements.txt`, checks Django configuration, checks for
missing migrations, and runs the complete test suite on Python 3.12.

See the results in the repository's **Actions** tab or in a pull request's checks.
You can also run it manually from **Actions → Django CI → Run workflow** once the
workflow is on `main`. Django creates a temporary test database; your local
database and administrator credentials are not used.

This workflow checks the code. Deployment can be added separately when the group
is ready for CD.

## Upgrade an existing development environment

Stop the development server and back up your local database before applying
migrations. Install Python 3.12, pull the updated project code, and create the new
`.venv312` environment using the commands above. If an older environment is active,
run `deactivate` first. Creating `.venv312` preserves your old `.venv` environment.

After activating `.venv312`, confirm `python --version` reports 3.12, install
`requirements.txt`, run the checks above, and run `python manage.py migrate`.
Reuse your existing database and administrator account.

In VS Code, use **Python: Select Interpreter** to select the Python executable in
`.venv312` (`bin/python` on macOS/Linux or `Scripts/python.exe` on Windows). Open a
new terminal and confirm its Python version before starting the server.

After this upgrade is merged into `main`, bring the updated `main` into existing
feature branches so their dependencies and CI use the same versions. Preserve
any additional dependencies needed by your feature, then run the full test suite.

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
| `reviews/` | Customer project ratings and reviews |
| `templates/` | Django HTML templates |
| `static/` | Shared CSS and other static assets |
| `config/` | Django settings and root routes |

Platform Management accounts can manage categories and view daily, weekly, and
monthly reports, and download each report as a PDF with its date range and
generation timestamp. Report periods use Singapore local dates; the weekly report
covers Monday through Sunday. New users and projects are counted by creation
date, while views and favourite saves are recorded with timestamps so reports
show activity within the selected period. Active users are distinct active
accounts that viewed or saved an IDP during that period.

## Boundary–Control–Entity (BCE) structure

The application separates its responsibilities into three layers:

| Layer | Files | Responsibility |
| --- | --- | --- |
| Boundary | `urls.py`, `views.py`, `forms.py`, and `templates/` | Receive requests, validate input, display pages and form errors, handle sessions, and return redirects or downloads |
| Control | Each app's `controllers.py` | Coordinate one user-story operation and apply access and ownership rules by calling entity operations |
| Entity | Each app's `models.py`, including custom model managers | Own persistent data, domain behaviour, database queries, saves, transactions, and constraints |

The user-story controls are separate classes. For example,
`SuspendUserAccountController` has a `suspend_account()` method. Its boundary is
the confirmation page and `account_suspend()` view:

```text
User Admin confirms the suspension
  -> account_suspend()                         Boundary
  -> SuspendUserAccountController.suspend_account()
                                               Control
  -> account.suspend()                        Entity
  -> Django ORM -> Database
```

The controller asks the entity to perform the operation. `UserAccount.suspend()`
updates the linked Django user's `is_active` field and saves it. Suspending a
profile similarly calls `UserProfile.suspend()` and saves the profile's own
status. Entity instance methods handle individual records; custom model managers
and entity class methods handle creation, searching, counts and other collection
operations. Controllers do not construct ORM queries or call `save()` directly.

Shared login, current/past project routes and report-period routes dispatch to
the appropriate named user-story control. The existing broad controller names
remain as compatibility facades for older callers. The application boundaries
use the individual controls. Access decorators use `AccountAccessController` to
keep active-account/profile rules shared. Forms retain Django's field and model
validation. Django's authentication/session machinery, HTTP redirects, messages
and PDF formatting remain boundary or framework responsibilities.

The four role-specific logout controls inherit the same redirect policy. The
shared logout boundary dispatches to the relevant role control and lets Django
invalidate the session. These role controls reuse the same infrastructure
behaviour; they do not need different database updates for each role.

The [48-story mapping](docs/bce-user-stories.json) lists each story's boundary,
control class, public method and entity operation. It describes the implemented
structure for review; the tutor's marking criteria and UML expectations should
also be checked against the final submission. Reviews and reactivation have
their own controls in addition to the 48 required stories.

User Admins can also delete another user account or an unused profile from its
detail page or list menu. `DeleteUserAccountController` and
`DeleteUserProfileController` call the corresponding entity's `delete_account()`
or `delete_profile()` method. Both operations require an active User Admin;
opening a confirmation page does not delete anything, and confirmation requires
a CSRF-protected POST. An administrator cannot delete their own account.
Profiles with assigned accounts must have those accounts reassigned or deleted
first. Account deletion removes its linked login and cascades to its company,
projects, favourites, reviews and view records. Shortlist counts on surviving
projects are adjusted in the same transaction; cumulative project view counts
remain unchanged. Account, profile and review deletion are listed separately
from the 48 required stories under `additional_features` in the mapping.

Company, current/past IDP, category and review Delete links also open a
confirmation page with the selected record and a Cancel link. GET only displays
the confirmation; a CSRF-protected POST calls the existing deletion control and
entity. Ownership and role restrictions apply to both requests. Deleting a
category keeps its projects and clears their category; company and project
confirmation pages explain their cascading deletions.

Run `python manage.py test accounts.test_bce_architecture` to check the mapping
and prevent application-owned ORM operations returning to the HTTP boundaries
or `controllers.py` files. Run the full `python manage.py test` suite to verify
the user flows. These architecture checks cover the application endpoints;
administrative seed scripts, demo-image assignment tools, migrations and Django
admin are separate infrastructure. Record user stories, tests, sprint work and
review evidence for the group report.
