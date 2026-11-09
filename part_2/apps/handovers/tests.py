from django.contrib.staticfiles.finders import find
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class MyTasksTemplateTests(SimpleTestCase):
    def test_calendar_template_has_interactive_controls(self):
        page = render_to_string("handovers/my_tasks.html")

        self.assertIn("My Tasks", page)
        self.assertIn("November", page)
        self.assertIn('id="calendar-days"', page)
        self.assertIn('id="task-list"', page)
        self.assertIn('id="prev-period"', page)
        self.assertIn('id="next-period"', page)
        self.assertIn('id="today-button"', page)

    def test_calendar_stylesheet_is_available(self):
        self.assertIsNotNone(find("css/my_tasks.css"))