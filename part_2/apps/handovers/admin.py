from django.contrib import admin

from .models import Employee, Handover, Subtask, Task, Upload

# Show each table on Django's admin page (/admin/) so we can view and edit the data
admin.site.register(Employee)
admin.site.register(Handover)
admin.site.register(Upload)
admin.site.register(Task)
admin.site.register(Subtask)