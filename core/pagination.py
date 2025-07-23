from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
import math

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
        total_count = self.page.paginator.count
        total_pages = math.ceil(total_count / self.page_size)
        current_page = self.page.number

        return Response({
            'status': True,
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': total_count,
            'total_pages': total_pages,
            'current_page': current_page,
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
