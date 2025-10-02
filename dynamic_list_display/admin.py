from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.core.exceptions import FieldDoesNotExist

class DynamicFieldsModelAdmin(admin.ModelAdmin):
    default_fields = [
        # Model default fields
    ]
    wrapper_change_list_template = "dynamic_list_display/change_list_dynamic_fields.html"

    @property
    def dynamic_fields_session_name(self):
        return f"{self.opts.app_label}.{self.__class__.__name__}"

    def _model_field_exists(self, field: str) -> bool:
        complex_field_parts = field.split("__")
        if len(complex_field_parts) == 1:
            try:
                self.model._meta.get_field(field)
                return True
            except FieldDoesNotExist:
                return False
        else:
            related_model = None
            for index, field_part in enumerate(complex_field_parts):
                if index < len(complex_field_parts)-1:
                    # related model
                    try:
                        if related_model is None:
                            related_model = self.model._meta.get_field(field_part).related_model
                        else:
                            related_model = related_model._meta.get_field(field_part).related_model
                    except FieldDoesNotExist:
                        return False
                else:
                    # last part is normal field
                    try:
                        related_model._meta.get_field(field_part)
                        return True
                    except FieldDoesNotExist:
                        return False

    def get_list_display(self, request):
        if request.GET.getlist('fields'):
            request.session[self.dynamic_fields_session_name] = request.GET.getlist('fields')

        if request.session.get(self.dynamic_fields_session_name):
            selected_fields = request.session.get(self.dynamic_fields_session_name)
            return [field for field in selected_fields if self._model_field_exists(field)]

        return self.default_fields

    def changelist_view(self, request, extra_context=None):
        if request.method != "GET":  # if action used, not just regular page load
            return super().changelist_view(request, extra_context)
        
        extra_context = extra_context or {}

        all_fields = []
        for f in self.model._meta.fields:
            if isinstance(f, models.OneToOneField) or isinstance(f, models.ForeignKey) or isinstance(f, models.ManyToManyField):
                for related_field in f.related_model._meta.fields:
                    all_fields.append(f"{f.name}__{related_field.name}")
            else:
                all_fields.append(f.name)

        selected_fields = request.session.get(self.dynamic_fields_session_name) or self.default_fields

        checkbox_html = ''.join([
            f'<label style="margin-right:10px;"><input type="checkbox" name="fields" value="{f}"'
            f' {"checked" if f in selected_fields else ""}> {f}</label>'
            for f in all_fields
        ])

        extra_context["original_template"] = self.change_list_template or "admin/change_list.html"
        extra_context['custom_field_selector'] = format_html(f"""
            <form method="get" style="margin: 0 0 60px 0;">
                {checkbox_html}
                <button type="submit" class="button cancel-link">Apply</button>
            </form>
        """)
        resulted_template = super().changelist_view(request, extra_context=extra_context)
        resulted_template.template_name = self.wrapper_change_list_template
        return resulted_template
