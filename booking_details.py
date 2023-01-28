# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


class BookingDetails:
    def __init__(
        self,
        dst_city: str = None,
        or_city: str = None,
        str_date: str = None,
        end_date: str = None,
        budget: str = None,
        n_adults: int = None,
        n_children: int = None,
        unsupported_airports=None,
    ):
        if unsupported_airports is None:
            unsupported_airports = []
        self.dst_city = dst_city
        self.or_city = or_city
        self.str_date = str_date
        self.end_date = end_date
        self.budget = budget
        self.n_adults = n_adults
        self.n_children = n_children
        self.unsupported_airports = unsupported_airports
