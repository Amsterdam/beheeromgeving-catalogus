from django.core.paginator import InvalidPage, Paginator
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.utils.urls import remove_query_param, replace_query_param


class Pagination:
    """
    Pagination Class that diverges slightly from rest framework pagination classes,
    as we do not work with querysets but rather lists of products. The django Paginator
    class is agnostic with regards to this.
    """

    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    def paginate(self, objects: list[dict], request: Request) -> list[dict]:
        self.request = request
        page_size = self.get_page_size(request)

        paginator = Paginator(objects, page_size)
        page_number = self.get_page_number(request)
        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = (
                f"Page not found: {page_number}. Page must be between 1 and "
                f"{paginator.num_pages} (inclusive)."
            )
            raise NotFound(msg) from exc

        return list(self.page)

    def get_page_number(self, request: Request) -> int:
        return int(request.query_params.get("page", 1))

    def get_page_size(self, request: Request) -> int:
        return min(
            int(request.query_params.get("pagesize", self.DEFAULT_PAGE_SIZE)), self.MAX_PAGE_SIZE
        )

    def get_paginated_response_body(self, data: list[dict]) -> dict:
        return {
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        }

    def get_paginated_response(self, data: list[dict]) -> Response:
        return Response(
            self.get_paginated_response_body(data),
        )

    def get_next_link(self):
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.next_page_number()
        return replace_query_param(url, "page", page_number)

    def get_previous_link(self):
        if not self.page.has_previous():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.previous_page_number()
        if page_number == 1:
            return remove_query_param(url, "page")
        return replace_query_param(url, "page", page_number)
