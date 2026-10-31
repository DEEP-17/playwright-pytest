from functools import lru_cache

from data.factory import TestDataFactory
from data.objects import TestData


@lru_cache(maxsize=1)
def load_test_data() -> TestData:
    return TestDataFactory.create()
