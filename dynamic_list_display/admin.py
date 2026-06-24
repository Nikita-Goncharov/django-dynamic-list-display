from typing import List
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field

class DynamicFieldsModelAdmin(admin.ModelAdmin):
    default_fields = [
        # Model default fields
    ]
    wrapper_change_list_template = "dynamic_list_display/change_list_dynamic_fields.html"
    wrapper_change_form_template = "dynamic_list_display/change_form_dynamic_fields.html"

    @property
    def dynamic_fields_session_name(self):
        return f"{self.opts.app_label}.{self.__class__.__name__}"
    
    def _get_model_field_if_exists(self, field: str) -> Field | None:
        complex_field_parts = field.split("__")
        if len(complex_field_parts) == 1:
            try:
                return self.model._meta.get_field(field)
            except FieldDoesNotExist:
                return None
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
                        return None
                else:
                    # last part is normal field
                    try:
                        return related_model._meta.get_field(field_part)
                    except FieldDoesNotExist:
                        return None

    def _is_field_editable(self, field: str) -> bool:
        """Check if a field is editable (can be included in form)."""
        field_obj = self._get_model_field_if_exists(field)
        if field_obj is None:
            return True  # Allow unknown fields (could be properties/methods)
        return field_obj.editable

    def get_list_display(self, request):
        return self._get_model_selected_fields(request)

    def get_fields(self, request, *args, **kwargs):
        selected_model_fields = self._get_model_selected_fields(request)
        try:
            # remove because id field cannot be shown in changeform
            selected_model_fields.remove("id")
        except ValueError:
            pass
        # Filter out non-editable fields (they'll be shown in readonly mode separately)
        return [f for f in selected_model_fields if "__" not in f and self._is_field_editable(f)]
    
    def _get_model_selected_fields(self, request):
        if request.GET.getlist('fields'):
            request.session[self.dynamic_fields_session_name] = request.GET.getlist('fields')

        if request.session.get(self.dynamic_fields_session_name):
            selected_fields = request.session.get(self.dynamic_fields_session_name)
            return [field for field in selected_fields if self._get_model_field_if_exists(field)]

        return list(self.default_fields)  # allow user to use list or tuple 

    def _get_model_all_fields(self) -> List[str]:
        all_fields = []
        for f in self.model._meta.fields:
            if isinstance(f, models.OneToOneField) or isinstance(f, models.ForeignKey) or isinstance(f, models.ManyToManyField):
                for related_field in f.related_model._meta.fields:
                    all_fields.append(f"{f.name}__{related_field.name}")
            else:
                all_fields.append(f.name)
        return all_fields

    def _get_checkbox_form(self, selected_fields: List[str], all_fields: List[str]):
        checkboxes = ''.join([
            f'<label style="margin-right:10px;"><input type="checkbox" name="fields" value="{f}"'
            f' {"checked" if f in selected_fields else ""}> {f}</label>'
            for f in all_fields
        ])

        return format_html(f"""
            <form method="get" style="margin: 0 0 60px 0;">
                {checkboxes}
                <button type="submit" class="button cancel-link">Apply</button>
            </form>
        """)

    @staticmethod
    def get_nested_attr(obj, attr_path):
        for attr in attr_path.split("__"):
            obj = getattr(obj, attr, None)
            if obj is None:
                return None
        return obj

    def change_view(self, request, object_id, form_url = "", extra_context = None):
        instance = self.model.objects.get(pk=object_id)
        if request.method != "GET":  # if action used, not just regular page load
            return super().change_view(request, object_id, form_url, extra_context)
        extra_context = extra_context or {}

        # trigger session update before html render to show current selected checkboxes
        selected_fields = self._get_model_selected_fields(request)
        related_fields = [f for f in selected_fields if "__" in f]
        non_editable_fields = [f for f in selected_fields if f != "id" and not self._is_field_editable(f)]

        try:
            selected_fields.remove("id")  # remove because id field cannot be shown in changeform
        except ValueError:
            pass

        all_fields = self._get_model_all_fields()

        extra_context["original_template"] = self.change_form_template or "admin/change_form.html"
        extra_context['custom_field_selector'] = self._get_checkbox_form(selected_fields, all_fields)
        # show selected foreign keys as readonly 
        extra_context["related_fields"] = {}
        for field in related_fields:
            verbose_name = self._get_model_field_if_exists(field).verbose_name
            value = self.get_nested_attr(instance, field)
            extra_context["related_fields"][verbose_name] = value

        # show non-editable fields as readonly
        extra_context["readonly_fields_data"] = {}
        for field in non_editable_fields:
            field_obj = self._get_model_field_if_exists(field)
            verbose_name = field_obj.verbose_name if field_obj else field
            value = getattr(instance, field, None)
            extra_context["readonly_fields_data"][verbose_name] = value

        resulted_template = super().change_view(request, object_id, form_url, extra_context)
        resulted_template.template_name = self.wrapper_change_form_template
        return resulted_template

    def changelist_view(self, request, extra_context=None, *args, **kwargs):
        if request.method != "GET":  # if action used, not just regular page load
            return super().changelist_view(request, extra_context)
        
        extra_context = extra_context or {}

        selected_fields = self._get_model_selected_fields(request)
        all_fields = self._get_model_all_fields()

        extra_context["original_template"] = self.change_list_template or "admin/change_list.html"
        extra_context['custom_field_selector'] = self._get_checkbox_form(selected_fields, all_fields)
        resulted_template = super().changelist_view(request, extra_context=extra_context)
        resulted_template.template_name = self.wrapper_change_list_template
        return resulted_template
