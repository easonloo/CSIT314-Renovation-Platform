"""Guard the application BCE dependency direction independently of feature tests.

Django's ModelForm/authentication/session internals remain framework code.  These
checks target application-owned controller and HTTP boundary code, rather than
claiming that Django itself never performs database access from framework hooks.
"""

import ast
import importlib
import inspect
import json
from pathlib import Path
import textwrap

from django.conf import settings
from django.test import SimpleTestCase


APPLICATIONS = (
    "accounts", "companies", "projects", "favourites", "categories", "reports", "reviews",
)
# These methods perform persistence, build database queries or execute SQL.  Do
# not include general Python/dict methods such as get(), count(), values() or
# update(); for example, a form legitimately iterates self.fields.values().
DATABASE_METHODS = {
    "save", "delete", "filter", "exclude", "annotate", "aggregate", "order_by",
    "select_related", "prefetch_related", "select_for_update", "values_list",
    "get_or_create", "update_or_create", "bulk_create", "bulk_update", "create_user",
    "create_superuser", "raw", "cursor",
}


def resolve_symbol(path):
    """Resolve both module symbols and methods nested inside a class."""
    parts = path.split(".")
    for end in range(len(parts), 0, -1):
        try:
            value = importlib.import_module(".".join(parts[:end]))
        except ModuleNotFoundError as error:
            attempted = ".".join(parts[:end])
            if error.name != attempted and not attempted.startswith(f"{error.name}."):
                raise
            continue
        for part in parts[end:]:
            value = getattr(value, part)
        return value
    raise ImportError(path)


class BoundaryControlEntityArchitectureTests(SimpleTestCase):
    def test_application_boundaries_and_controls_delegate_database_work_to_entities(self):
        violations = []
        for application in APPLICATIONS:
            for filename in ("controllers.py", "views.py", "forms.py"):
                path = Path(settings.BASE_DIR) / application / filename
                if not path.exists():
                    continue
                tree = ast.parse(path.read_text(), filename=str(path))
                for node in ast.walk(tree):
                    reason = None
                    if isinstance(node, ast.Attribute) and node.attr == "objects":
                        reason = "direct access to an ORM manager"
                    elif (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in DATABASE_METHODS
                    ):
                        reason = f"direct database operation {node.func.attr}()"
                    elif isinstance(node, ast.ImportFrom) and (
                        node.module == "django.db" or (node.module or "").startswith("django.db.")
                    ):
                        reason = "database machinery imported outside the entity layer"
                    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        if node.func.id in {"get_object_or_404", "get_list_or_404"}:
                            reason = "boundary performs an ORM lookup"
                    if reason:
                        relative = path.relative_to(settings.BASE_DIR)
                        violations.append(f"{relative}:{node.lineno}: {reason}")
        self.assertEqual(violations, [], "\n".join(violations))

    def test_story_mapping_covers_48_resolvable_controls_and_entity_operations(self):
        mapping_path = Path(settings.BASE_DIR) / "docs" / "bce-user-stories.json"
        mapping = json.loads(mapping_path.read_text())
        stories = mapping["stories"]
        self.assertEqual([story["id"] for story in stories], list(range(1, 49)))
        self.assertEqual(len({story["control"] for story in stories}), 48)
        for story in [*stories, *mapping.get("additional_features", [])]:
            with self.subTest(story=story["id"]):
                control = resolve_symbol(story["control"])
                self.assertTrue(inspect.isclass(control))
                self.assertTrue(callable(getattr(control, story["method"])))
                self.assertTrue(callable(resolve_symbol(story["boundary"])))
                for entity_operation in story["entity_operations"]:
                    self.assertTrue(callable(resolve_symbol(entity_operation)))

    def test_mapped_controls_are_referenced_by_their_boundary_or_dispatcher(self):
        mapping_path = Path(settings.BASE_DIR) / "docs" / "bce-user-stories.json"
        mapping = json.loads(mapping_path.read_text())
        stories = [*mapping["stories"], *mapping.get("additional_features", [])]
        for story in stories:
            with self.subTest(story=story["id"]):
                controller_name = story["control"].rsplit(".", 1)[1]
                symbols = set()
                # The explicit dispatcher list records shared login, period and
                # current/past routes.  An import alone is not a wiring reference.
                for path in [story["boundary"], *story.get("dispatchers", [])]:
                    value = inspect.unwrap(resolve_symbol(path))
                    source = textwrap.dedent(inspect.getsource(value))
                    for node in ast.walk(ast.parse(source)):
                        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                            symbols.add(node.id)
                        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                            symbols.add(node.attr)
                self.assertIn(controller_name, symbols)
