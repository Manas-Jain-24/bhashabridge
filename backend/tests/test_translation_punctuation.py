import pytest
from app.services.translation.punctuation import finish_native_sentence


@pytest.mark.parametrize('source,expected',[
    ('তিনি বললেন, "হ্যাঁ।"','তিনি বললেন, "হ্যাঁ।"'),
    ('তিনি বললেন, "হ্যাঁ।"।','তিনি বললেন, "হ্যাঁ।"'),
    ('उन्होंने कहा, “हाँ।”','उन्होंने कहा, “हाँ।”'),
    ('हे बरोबर आहे','हे बरोबर आहे।'),
    ('काय?','काय?'),('  ঠিক আছে।  ','ঠিক আছে।'),('',''),
])
def test_native_sentence_endings_respect_quotes(source,expected):
    assert finish_native_sentence(source)==expected
