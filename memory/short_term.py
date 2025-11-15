class ShortTermMemory:
    """
    A simple rolling memory buffer that stores recent thoughts,
    actions, observations, or intermediate results.
    """

    def __init__(self, max_items=10):
        self.max_items = max_items
        self.buffer = []

    def add(self, item):
        """Add an entry to memory."""
        self.buffer.append(item)
        if len(self.buffer) > self.max_items:
            self.buffer.pop(0)

    def get(self):
        """Return all short-term memories."""
        return list(self.buffer)

    def clear(self):
        """Clear memory."""
        self.buffer = []
