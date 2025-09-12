from django.contrib import admin
from django.utils.html import format_html


class DynamicFieldsModelAdmin(admin.ModelAdmin):
    default_fields = [
        # Model default fields
    ]
    change_list_template = "dynamic_list_display/change_list_dynamic_fields.html"

    @property
    def dynamic_fields_session_name(self):
        return f"{self.opts.app_label}.{self.__class__.__name__}"

    def get_list_display(self, request):        
        if request.GET.getlist('fields'):
            request.session[self.dynamic_fields_session_name] = request.GET.getlist('fields')

        if request.session.get(self.dynamic_fields_session_name):
            selected_fields = request.session.get(self.dynamic_fields_session_name)
            valid_fields = [f.name for f in self.model._meta.fields]
            return [f for f in selected_fields if f in valid_fields]
        return self.default_fields

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        all_fields = [f.name for f in self.model._meta.fields]
        selected_fields = request.session.get(self.dynamic_fields_session_name) or self.default_fields

        checkbox_html = ''.join([
            f'<label style="margin-right:10px;"><input type="checkbox" name="fields" value="{f}"'
            f' {"checked" if f in selected_fields else ""}> {f}</label>'
            for f in all_fields
        ])

        extra_context['custom_field_selector'] = format_html(f"""
            <form method="get" style="margin: 0 0 60px 0;">
                {checkbox_html}
                <button type="submit" class="button cancel-link">Apply</button>
            </form>
        """)

        return super().changelist_view(request, extra_context=extra_context)