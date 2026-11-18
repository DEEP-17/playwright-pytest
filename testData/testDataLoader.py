from functools import lru_cache
from testData.testDataFactory import TestDataFactory
from testData.testDataObjects import TestData

@lru_cache(maxsize=1)
def load_test_data() -> TestData:
    return TestDataFactory.create()
