from django.contrib.staticfiles.finders import find
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class MyTasksTemplateTests(SimpleTestCase):
    def test_mock_calendar_template_renders_tasks_and_selected_date(self):
        page = render_to_string("handovers/my_tasks.html")

        self.assertIn("My Tasks", page)
        self.assertIn("November", page)
        self.assertIn("Wednesday, 18 Nov", page)
        self.assertIn("1.1 Gather project information", page)
        self.assertIn("1.2 Analyse information", page)
        self.assertIn("Weekly audit summary", page)

    def test_calendar_stylesheet_is_available(self):
        self.assertIsNotNone(find("css/my_tasks.css"))
