class FakeStructuredLLM:
    """Returns (or raises) the queued outputs in order, recording each call's messages."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


class FakeLLM:
    def __init__(self, outputs):
        self.structured = FakeStructuredLLM(outputs)

    def with_structured_output(self, schema):
        return self.structured
