from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    """
    Custom pagination class that extends the `PageNumberPagination` class.
    
    This class defines how paginated responses should be structured. 
    It allows for pagination with a fixed page size and formats the paginated response
    with additional metadata, such as the total count of items and links to navigate 
    between pages.
    """
    page_size = 10
    def get_paginated_response(self, data):
        """
        Returns a paginated response in a custom format.
        
        This method takes the paginated data and formats it in a structured response,
        including metadata such as the status, total item count and pagination links.
        """
        return Response({
            'status': True, 
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'data': data
        })
    
class PaginationMixin:
    """
    Mixin to add pagination functionality to views.

    This mixin provides methods for paginating querysets and formatting the paginated response using
    a custom pagination class.
    """
    pagination_class = CustomPagination

    def paginate_queryset(self, queryset, request):
        self.paginator = self.pagination_class()
        return self.paginator.paginate_queryset(queryset, request)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)
