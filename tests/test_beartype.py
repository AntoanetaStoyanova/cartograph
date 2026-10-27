import pytest
from beartype.roar import BeartypeCallHintParamViolation

from cartograph.log import setup_logging


def test_wrong_argument_type_raises() -> None:
    with pytest.raises(BeartypeCallHintParamViolation):
        setup_logging(123)  # type: ignore[arg-type]
