from django.http import HttpResponse
from django.utils.text import slugify
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test, login_required
from django.views.decorators.cache import never_cache, cache_page
from django import forms
from django.db import models

import csv
import json
from crispy_forms.helper import FormHelper

class BasicContextMixin(object):
    """
    This mixin allows you to define a context dictionary in any view and the contents will
    be available to your template.
    """
    extra_context = {}
    def get_context_data(self, **kwargs):
        context = super(BasicContextMixin, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

class SuperUserAuthenticationMixin(object):
    """
    Requires user to be superuser before being able to access the post/get methods.
    """
    @method_decorator(user_passes_test(lambda x: x.is_superuser))
    def dispatch(self, request,  *args, **kwargs):
        return super(SuperUserAuthenticationMixin, self).dispatch(request, *args, **kwargs)

class StaffAuthenticationMixin(object):
    """
    Requires user to be staff before being able to access to post/get methods.
    """
    @method_decorator(user_passes_test(lambda x: x.is_staff))
    def dispatch(self, request, *args, **kwargs):
        return super(StaffAuthenticationMixin, self).dispatch(request, *args, **kwargs)

class UserAuthenticationMixin(object):
    """
    Requires user to be logged in user before being able to access the post/get methods.
    """
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserAuthenticationMixin, self).dispatch(request, *args, **kwargs)

class FormHorizontalForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        super(FormHorizontalForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'

class FormHorizontalModelForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(FormHorizontalModelForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'

class NeverCacheMixin(object):
    """
    Never cache a view
    """
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super(NeverCacheMixin, self).dispatch(request, *args, **kwargs)

class CSVModelExportResponseMixin(object):
    """
    Mixin that constructs a CSV response file from a Django model based on the requested
    list of objects.
    """
    def render_to_response(self, context, **response_kwargs):
        if 'csv' in self.request.GET.get('export', '') and self.model:
            # If `?export=csv` is in the GET variables.
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=%s.csv' % (self.model.__name__)
            writer = csv.writer(response)
            headers = [field.name for field in self.model._meta.fields]
            writer.writerow(headers)
            # Double list comprehension, I'm a jerk, I know.
            # The inner comprehension loops over the fields in headers and the outer 
            # comprehension loops over the objects in the queryset for the view.
            [writer.writerow([getattr(obj, field) for field in headers]) for obj in self.get_queryset()]
            return response
        else:
            return super(CSVModelExportResponseMixin, self).render_to_response(context, **response_kwargs)

class AjaxFormResponseMixin(object):
    def render_to_json_response(self, context, **response_kwargs):
        data = json.dumps(context)
        response_kwargs['content_type'] = 'application/json'
        reutrn HttpResponse(data, **response_kwargs)

    def form_invalid(self, form):
        response = super(AjaxFormResponseMixin, self).form_invalid(form)
        if self.request.is_ajax():
            return self.render_to_json_response(form.errors, status = 400)
        else:
            return response

    def form_valid(self, form):
        response = super(AjaxFormResponseMixin, self).form_valid(form)
        if self.request.is_ajax():
            data = { self.object.pk }
            return render_to_json_response(data)
        else:
            return response
        
class DefaultFilterListMixin(object):
    default_filter = {}
    filter_fields = []

    def get_queryset(self):
        queryset = super(DefaultFilterListMixin, self).get_queryset()
        # Intersect self.filter_fields with model fields to ensure we don't get any wacky lookups
        if self.request.GET:
            default_copy = self.default_filter
            for filter, filter_value in self.request.GET.iteritems():
                # We loop over the submitted fields in .GET and make sure they are in the filter_fields. 
                if filter.split('__')[0] in self.safe_filters(): 
                    queryset = queryset.filter(**{filter: filter_value})
                    default_copy.pop(filter, None)
                # For filters that are not passed along in .GET that are not default, we make sure we keep them.
                # Check to make sure `all` wasn't passed along
                if not self.request.GET.get('all'):
                    for filter, filter_value in default_copy.iteritems():
                        queryset = queryset.filter(**{filter: filter_value})
        else:
            # We want the default filter. Filter on it!
            for filter, filter_value in self.default_filter.iteritems():
                queryset = queryset.filter(**{filter: filter_value})
        return queryset

    def get_context_data(self, **kwargs):
        context = super(DefaultFilterListMixin, self).get_context_data(**kwargs)
        context['available_filters'] = self.get_available_filter_dict()
        context['active_filters'] = self.get_active_filter_dict()
        return context

    def safe_filters(self):
        safe_filters = []
        if self.filter_fields and self.model:
            """
            # Strip __ to ensure the lookup works. We should ensure that further lookups are safe.
            filters = [filter[0].split('__')[0] for filter in self.filter_fields.iteritems()]
            safe_filters = list(set(set(filters) & set(self.model._meta.get_all_field_names())))
            """
            # Strip __ to ensure the lookup works. We should ensure that further lookups are safe.
            split_dict = {}
            filters = []
            for filter in self.filter_fields:
                filter_split = filter.split('__')[0]
                split_dict[filter_split] = filter
                filters.append(filter_split)
            safe_split_filters = list(set(filters) & set(self.model._meta.get_all_field_names()))
            for split_filter, filter in split_dict.iteritems():
                if split_filter in safe_split_filters:
                    safe_filters.append(filter)
        return safe_filters

    def get_active_filter_dict(self):
        active_filters = {}
        if self.request.GET and self.safe_filters():
            safe_filters = self.safe_filters()
            for filter in self.request.GET:
                if filter.split('__')[0] in safe_filters:
                    active_filters[filter] = self.request.GET.get(filter)
        return active_filters

    def is_fk_model(self, fieldname):
        """
        http://stackoverflow.com/questions/2608067/how-to-find-out-whether-a-models-column-is-a-foreign-key
        Returns None if the fieldname is not a foreignkey on 
        the model, otherwise returns the model.
        """
        field_object, model, direct, m2m = self.model._meta.get_field_by_name(fieldname)
        if not m2m and direct and isinstance(field_object, models.ForeignKey):
            return field_object.rel.to
        return None

    def is_datetime_field(self, fieldname):
        field_object, model, direct, m2m = self.model._meta.get_field_by_name(fieldname)
        if isinstance(field_object, models.DateTimeField) or isinstance(field_object, models.DateField) or isinstance(field_object, models.TimeField):
            return field_object
        return False

    def get_available_filter_dict(self):
        base_qs = self.model._base_manager.all()
        qs_values = base_qs.values()
        safe_filters = self.safe_filters()
        basic_filters = {}
        fk_filters = {}
        lookup_filters = {}
        for filter in safe_filters:
            split_filter = filter.split('__')
            # IF FOREIGN KEY
            # Use __unicode__ or the lookup
            if self.is_fk_model(split_filter[0]):
                fk_filters[filter] = {}
                fk_filters[filter]['select_name'] = filter
                fk_filters[filter]['values'] = {}
                fk = self.is_fk_model(split_filter[0])
                fk_qs = fk._base_manager.all()
                try:
                    lookup_name = fk._meta.get_field_by_name(split_filter[1])[0].name
                except FieldDoesNotExist:
                    [fk_filters[filter]['values'].update({obj.pk: str(obj)}) for obj in fk_qs]
                    fk_filters[filter]['display_name'] = split_filter[0]
                except:
                    fk_filters[filter]['values'] = 'Error'
                else:
                    [fk_filters[filter]['values'].update({obj.pk: getattr(obj, lookup_name)}) for obj in fk_qs]
                    fk_filters[filter]['display_name'] = lookup_name
            """
            # IF DATETIME, DATE, TIME
            # Lookup using getattr()
            elif self.is_datetime_field(split_filter[0]):
                type = self.is_datetime_field(split_filter[0]).verbose_name
                lookup_filters[filter] = {}
                available_lookups = []
                if type == 'datetime':
                    available_lookups = ['year', 'month', 'day', 'minute', 'hour', 'seconds']
                elif type == 'date':
                    available_lookups = ['year', 'month', 'day']
                elif type == 'time':
                    available_lookups = ['hour', 'minute', 'seconds']
                lookup_filters[filter]['display_name'] = split_filter[1]
                if split_filter[1] in available_lookups:
                    lookup_filters[filter]['values'] = {}
                    [lookup_filters[filter]['values'].update({getattr(getattr(obj, type), split_filter[1]): getattr(getattr(obj, type), split_filter[1])}) for obj in qs_values]
            """
            # ELSE ???? DONT KNOW.
            # Do normal expectation on values. (use getattr)
            else:
                basic_filters[filter] = {}
                basic_filters[filter]['select_name'] = filter
                basic_filters[filter]['display_name'] = filter.capitalize()
                basic_filters[filter]['values'] = {}
                [lookup_filters[filter]['values'].update({getattr(obj, filter): getattr(obj, filter)}) for obj in base_qs if getattr(obj, filter) is not None]
        actual_filters = {}
        actual_filters.update(fk_filters)
        actual_filters.update(basic_filters)
        actual_filters.update(lookup_filters)
        return actual_filters
