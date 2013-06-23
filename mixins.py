from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test, login_required

class BasicContextMixin(object):
    """
    This mixin allows you to define a context dictionary in any view and the contents will
    be available to your template.
    """
    context = {}
    
    def get_context_data(self, **kwargs):
        context = super(ContextMixin, self).get_context_data(**kwargs)
        context.update(self.context)
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
