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
